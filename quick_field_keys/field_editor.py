"""SPDX-License-Identifier: GPL-3.0-or-later

Edit only explicitly chosen fields for a fixed selection of features.
The layer form configuration is never changed. Edits require an explicit Apply.
"""
import json
from pathlib import Path

from qgis.core import QgsSettings, QgsVariantUtils
from qgis.gui import QgsGui
from qgis.PyQt.QtCore import Qt
from qgis.PyQt.QtGui import QIcon, QKeySequence
from qgis.PyQt.QtWidgets import (
    QCheckBox, QDialog, QDialogButtonBox, QFormLayout, QHBoxLayout,
    QLabel, QListWidget, QListWidgetItem, QMessageBox, QPushButton,
    QScrollArea, QStyle, QTextEdit, QToolButton, QVBoxLayout, QWidget,
)

from .plugin import locked_names, writable_indices


class FieldEditor(QDialog):
    def __init__(self, plugin, layer, embedded=False, parent=None, save_button=None):
        super().__init__(parent or plugin.iface.mainWindow())
        self.embedded = embedded
        if embedded:
            self.setWindowFlags(Qt.WindowType.Widget)
        self.plugin = plugin
        self.layer = layer
        self.ids = list(layer.selectedFeatureIds())
        self.rows = {}
        self.changed_fields = set()
        self.initial_values = {}
        self.setWindowTitle(f'Quick Field Keys - Chosen fields: {layer.name()}')
        if not embedded:
            self.resize(650, 550)
        layout = QVBoxLayout(self)
        if embedded:
            layout.setContentsMargins(0, 0, 0, 0)
            layout.setSpacing(4)
        self.scope = QLabel(f'Fixed selection: {len(self.ids)} features. Apply only modified, unlocked fields.')
        self.scope.setWordWrap(True)
        layout.addWidget(self.scope)
        if embedded:
            self.scope.hide()
        choose = QPushButton('Choose visible / editable fields...')
        choose.setToolTip('Choose visible / editable fields — Select which columns appear and can be edited in this form.\n표시·편집 필드 선택 — 이 편집창에 표시하고 편집할 컬럼을 선택합니다. 레이어별로 기억합니다.')
        choose.clicked.connect(self.choose_fields)
        if not embedded:
            layout.addWidget(choose)
        else:
            choose.deleteLater()
        self.form_widget = QWidget()
        self.form = QFormLayout(self.form_widget)
        if embedded:
            self.form.setContentsMargins(0, 0, 0, 0)
            layout.addWidget(self.form_widget)
        else:
            scroll = QScrollArea()
            scroll.setWidgetResizable(True)
            scroll.setWidget(self.form_widget)
            layout.addWidget(scroll)
        self.setting = f'quick_field_keys/visible_fields/{layer.id()}'
        try:
            names = json.loads(QgsSettings().value(self.setting, 'null'))
        except (TypeError, ValueError):
            names = None
        allowed = [layer.fields()[i].name() for i in writable_indices(layer)]
        self.visible_names = [name for name in names if name in allowed] if isinstance(names, list) else allowed
        self.load_rows()
        if embedded:
            self.save_button = save_button if save_button is not None else QToolButton(self)
            self.save_button.setObjectName('save_feature_edits')
            self.save_button.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_DialogSaveButton))
            self.save_button.setAccessibleName('Save feature edits / 피처 편집 저장')
            self.save_button.setShortcut(QKeySequence(plugin.shortcut_key('save_feature')))
            self.save_button.setToolTip('Save feature edits — Apply modified, unlocked columns to this captured selection in the edit buffer. This does not save the data file.\n피처 편집 저장 — 실제 수정한 잠금 해제 컬럼만 고정된 선택 객체의 편집 버퍼에 반영합니다. 실제 파일 저장은 별도입니다.')
            self.save_button.setEnabled(False)
            if save_button is None:
                self.save_button.clicked.connect(self.apply_form)
                row = QHBoxLayout()
                row.addStretch(1)
                row.addWidget(self.save_button)
                layout.addLayout(row)
            layer.destroyed.connect(self.layer_deleted)
            return
        self.immediate = QCheckBox('Apply Alt+1-9 immediately to layer edits')
        self.immediate.setToolTip('Immediate shortcut application — On: edit buffer. Off: stage shortcut values. File save remains manual.\n단축키 즉시 적용 — 켜면 편집 버퍼에 적용하고, 끄면 대기값으로 보관합니다. 파일 저장은 별도입니다.')
        self.immediate.setChecked(plugin.immediate)
        self.immediate.toggled.connect(plugin.set_immediate)
        layout.addWidget(self.immediate)
        self.status = QLabel()
        self.status.setWordWrap(True)
        layout.addWidget(self.status)
        self.preview = QTextEdit()
        self.preview.setReadOnly(True)
        self.preview.setMaximumHeight(120)
        layout.addWidget(self.preview)
        row = QHBoxLayout()
        for text, tooltip, callback in (
            ('Apply form edits', 'Apply form edits — Apply only modified, unlocked fields to the captured selection. File save remains manual.\n폼 편집 적용 — 실제 수정한 잠금 해제 필드만 고정된 선택 객체에 적용합니다. 파일 저장은 별도입니다.', self.apply_form),
            ('Apply pending shortcuts', 'Apply pending shortcuts — Apply staged values to the targets captured when shortcuts were pressed.\n대기 단축키 적용 — 단축키 입력 시 고정한 대상에 대기값을 적용합니다. 현재 선택으로 대상을 바꾸지 않습니다.', self.apply_pending),
            ('Undo (Alt+Z)', 'Undo (Alt+Z) — Reset unapplied form inputs first; otherwise restore the last Quick Field Keys feature group and focus it. Other tools\' edits are protected.\n실행 취소 (Alt+Z) — 미적용 폼 입력이 있으면 먼저 초기화합니다. 그 외에는 마지막 객체의 플러그인 변경을 함께 복원하고 화면을 이동합니다. 다른 도구의 편집은 보호합니다.', self.undo),
            ('Discard pending', 'Discard pending — Remove staged shortcut values from memory; keep applied edits unchanged.\n대기값 폐기 — 메모리에 보관한 대기값을 버립니다. 이미 적용한 편집은 유지합니다.', self.discard_pending),
        ):
            button = QPushButton(text)
            button.setToolTip(tooltip)
            if text == 'Undo (Alt+Z)':
                button.setShortcut(QKeySequence('Alt+Z'))
            button.clicked.connect(callback)
            row.addWidget(button)
        layout.addLayout(row)
        close = QPushButton('Close')
        close.setToolTip('Close — Close the editor; ask before discarding unapplied form inputs.\n닫기 — 편집창을 닫습니다. 미적용 폼 입력이 있으면 폐기 여부를 확인합니다.')
        close.clicked.connect(self.close)
        layout.addWidget(close)
        self.refresh_status()
        layer.destroyed.connect(self.layer_deleted)

    def load_rows(self):
        for wrapper, lock in self.rows.values():
            wrapper.blockSignals(True)
            # Nested row layouts can outlive removal until Qt processes deferred deletion.
            wrapper.widget().hide()
            wrapper.widget().deleteLater()
            lock.hide()
            lock.deleteLater()
            wrapper.deleteLater()
        while self.form.rowCount():
            self.form.removeRow(0)
        self.rows = {}
        self.changed_fields = set()
        self.initial_values = {}
        if hasattr(self, 'save_button'):
            self.save_button.setEnabled(False)
        if self.layer is None:
            return
        features = [self.layer.getFeature(fid) for fid in self.ids]
        for name in self.visible_names:
            index = self.layer.fields().indexFromName(name)
            if index not in writable_indices(self.layer):
                continue
            registry = QgsGui.editorWidgetRegistry()
            if self.layer.editorWidgetSetup(index).type() == 'Hidden':
                wrapper = registry.create('TextEdit', self.layer, index, {}, None, self.form_widget)
            else:
                wrapper = registry.create(self.layer, index, None, self.form_widget)
            if wrapper is None:
                continue
            editor = wrapper.widget()
            wrapper.setEnabled(bool(features) and not self.layer.readOnly())
            values = [feature[name] for feature in features if feature.isValid()]
            same = bool(values) and all(self.equal(value, values[0]) for value in values)
            wrapper.setValue(values[0] if same else None)
            self.initial_values[name] = (same, values[0] if same else None)
            for button in editor.findChildren(QToolButton):
                if not button.toolTip():
                    button.setToolTip(f'Field input control — Change the input for {name}; use the save-feature icon to apply it to the edit buffer.\n필드 입력 도구 — {name}의 입력값을 바꿉니다. 피처 저장 아이콘을 눌러야 편집 버퍼에 반영됩니다.')
            lock = QToolButton(self.form_widget)
            lock.setObjectName(f'lock_{name}')
            lock.setCheckable(True)
            lock.setChecked(name in locked_names(self.layer))
            lock.toggled.connect(lambda checked, field=name: self.set_field_lock(field, checked))
            wrapper.valueChanged.connect(lambda *args, field=name: self.field_changed(field))
            row = QHBoxLayout()
            row.addWidget(editor, 1)
            row.addWidget(lock)
            self.form.addRow(name + ('' if same else ' (mixed / empty)'), row)
            self.rows[name] = (wrapper, lock)
            self.refresh_field_lock(name)

    def field_changed(self, name):
        if name not in self.rows or name in locked_names(self.layer):
            return
        same, initial = self.initial_values[name]
        if same and self.equal(self.rows[name][0].value(), initial):
            self.changed_fields.discard(name)
        else:
            self.changed_fields.add(name)
        if hasattr(self, 'save_button'):
            self.save_button.setEnabled(bool(self.changed_fields))

    def refresh_field_lock(self, name):
        wrapper, lock = self.rows[name]
        locked = name in locked_names(self.layer)
        editable = bool(self.ids) and not self.layer.readOnly() and not locked
        wrapper.setEnabled(editable)
        wrapper.widget().setEnabled(editable)
        lock.setIcon(QIcon(str(Path(__file__).with_name('field_locked.svg' if locked else 'field_unlocked.svg'))))
        lock.setAccessibleName(f'{"Unlock" if locked else "Lock"} {name}')
        lock.setToolTip(
            f'Unlock {name} — Allow edits to this column in Quick Field Keys.\n{name} 잠금 해제 — 이 플러그인에서 해당 컬럼을 다시 수정할 수 있게 합니다.' if locked else
            f'Lock {name} — Block this plugin\'s form, shortcuts, pending Apply and Undo writes to this column. Other QGIS tools are unaffected.\n{name} 잠금 — 이 플러그인의 폼·단축키·대기값 적용·Undo에서 해당 컬럼 변경을 차단합니다. 다른 QGIS 도구에는 적용되지 않습니다.')

    def set_field_lock(self, name, locked):
        wrapper, lock = self.rows[name]
        if locked and name in self.changed_fields:
            answer = QMessageBox.question(self, 'Lock field / 필드 잠금',
                f'Discard unapplied input for {name} and lock it?\n{name}의 미적용 입력을 버리고 잠글까요?',
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, QMessageBox.StandardButton.No)
            if answer != QMessageBox.StandardButton.Yes:
                lock.blockSignals(True)
                lock.setChecked(False)
                lock.blockSignals(False)
                return
            wrapper.setValue(self.initial_values[name][1])
            self.changed_fields.discard(name)
        names = locked_names(self.layer)
        if locked:
            names.add(name)
        else:
            names.discard(name)
        QgsSettings().setValue(f'quick_field_keys/locked_fields/{self.layer.id()}', json.dumps(sorted(names)))
        self.refresh_field_lock(name)
        if hasattr(self, 'save_button'):
            self.save_button.setEnabled(bool(self.changed_fields))

    @staticmethod
    def equal(left, right):
        return (QgsVariantUtils.isNull(left) and QgsVariantUtils.isNull(right)) or left == right

    def choose_fields(self, checked=False):
        if self.layer is None:
            self.plugin.warn('The target layer was removed.')
            return False
        if self.has_form_edits() and not self.confirm_discard_form():
            return False
        dialog = QDialog(self)
        dialog.setWindowTitle('Choose fields shown in this editor')
        layout = QVBoxLayout(dialog)
        items = QListWidget()
        for index in writable_indices(self.layer):
            name = self.layer.fields()[index].name()
            item = QListWidgetItem(name, items)
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            item.setCheckState(Qt.CheckState.Checked if name in self.visible_names else Qt.CheckState.Unchecked)
        layout.addWidget(items)
        row = QHBoxLayout()
        for name, tooltip, state in (
            ('Select all', 'Select all — Check every available field.\n일괄 선택 — 사용 가능한 모든 필드를 체크합니다.', Qt.CheckState.Checked),
            ('Deselect all', 'Deselect all — Uncheck every field; values are not deleted.\n일괄 해제 — 모든 필드의 체크를 해제합니다. 필드 값은 삭제하지 않습니다.', Qt.CheckState.Unchecked),
        ):
            button = QPushButton(name)
            button.setToolTip(tooltip)
            button.clicked.connect(lambda checked=False, value=state: [items.item(i).setCheckState(value) for i in range(items.count())])
            row.addWidget(button)
        layout.addLayout(row)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.button(QDialogButtonBox.StandardButton.Ok).setToolTip('OK — Remember the chosen columns and rebuild the form.\n확인 — 선택한 컬럼을 기억하고 편집창에 표시합니다.')
        buttons.button(QDialogButtonBox.StandardButton.Cancel).setToolTip('Cancel — Keep the current column selection unchanged.\n취소 — 기존 컬럼 선택을 유지합니다.')
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        layout.addWidget(buttons)
        was_visible = self.isVisible() and not self.embedded
        if was_visible:
            self.hide()
        try:
            accepted = dialog.exec() == QDialog.DialogCode.Accepted
        finally:
            if was_visible:
                self.show()
        if accepted:
            self.visible_names = [items.item(i).text() for i in range(items.count())
                                  if items.item(i).checkState() == Qt.CheckState.Checked]
            QgsSettings().setValue(self.setting, json.dumps(self.visible_names))
            self.load_rows()
            return True
        return False

    def has_form_edits(self):
        return bool(self.changed_fields)

    def confirm_discard_form(self):
        return QMessageBox.question(
            self, 'Unapplied form values', 'Discard unapplied values in this editor?',
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No) == QMessageBox.StandardButton.Yes

    def apply_form(self, checked=False):
        changes = {(fid, name): wrapper.value()
                   for name, (wrapper, lock) in self.rows.items() if name in self.changed_fields and not lock.isChecked()
                   for fid in self.ids}
        if self.plugin.apply_changes(self.layer, changes, 'Apply chosen fields'):
            self.load_rows()
            self.refresh_status()

    def apply_pending(self, checked=False):
        if self.plugin.pending_layer is not None and self.plugin.pending_layer is not self.layer:
            self.plugin.warn('Pending values belong to a different layer. Open its editor to apply them.')
            return
        if self.has_form_edits() and not self.confirm_discard_form():
            return
        if self.plugin.apply_pending():
            self.load_rows()

    def undo(self, checked=False):
        if self.has_form_edits():
            # Local form inputs are not layer edits; reset them before undoing layer edits.
            self.load_rows()
            self.refresh_status()
            return
        self.plugin.undo_edit(self.layer)
        self.load_rows()

    def discard_pending(self, checked=False):
        if self.plugin.pending_layer is not None and self.plugin.pending_layer is not self.layer:
            self.plugin.warn('Pending values belong to a different layer.')
            return
        self.plugin.discard_pending()

    def refresh_status(self):
        if self.embedded:
            return
        self.immediate.blockSignals(True)
        self.immediate.setChecked(self.plugin.immediate)
        self.immediate.blockSignals(False)
        pending = self.plugin.pending_changes
        fields = ', '.join(sorted({name for fid, name in pending}))
        try:
            target = self.plugin.pending_layer.name() if self.plugin.pending_layer is not None else 'none'
        except RuntimeError:
            target = '(removed layer - use Discard pending shortcuts from the plugin menu)'
        self.status.setText(
            f'Pending target: {target}. Shortcut changes: {len(pending)} ({fields or "none"}). '
            'Targets are captured when shortcuts are pressed; changing selection does not retarget them. '
            'Apply never saves the data file.')
        # ponytail: cap the preview at 100 entries; pending data itself is never truncated.
        lines = [f'FID {fid} | {name} = {value!r}'
                 for (fid, name), value in list(pending.items())[:100]]
        if len(pending) > 100:
            lines.append(f'... {len(pending) - 100} more changes not shown')
        self.preview.setPlainText('\n'.join(lines) or 'No pending shortcut values.')

    def layer_deleted(self, *args):
        self.layer = None
        self.form_widget.setEnabled(False)
        self.scope.setText('The target layer was removed. Form edits cannot be applied.')

    def closeEvent(self, event):
        if self.has_form_edits() and not self.confirm_discard_form():
            event.ignore()
            return
        event.accept()
