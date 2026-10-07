"""SPDX-License-Identifier: GPL-3.0-or-later

Edit only explicitly chosen fields for a fixed selection of features.
The layer form configuration is never changed. Edits require an explicit Apply.
"""
import json

from qgis.core import QgsSettings, QgsVariantUtils
from qgis.gui import QgsGui
from qgis.PyQt.QtCore import Qt
from qgis.PyQt.QtWidgets import (
    QCheckBox, QDialog, QDialogButtonBox, QFormLayout, QHBoxLayout,
    QLabel, QListWidget, QListWidgetItem, QMessageBox, QPushButton,
    QScrollArea, QTextEdit, QVBoxLayout, QWidget,
)

from .plugin import writable_indices


class FieldEditor(QDialog):
    def __init__(self, plugin, layer):
        super().__init__(plugin.iface.mainWindow())
        self.plugin = plugin
        self.layer = layer
        self.ids = list(layer.selectedFeatureIds())
        self.rows = {}
        self.setWindowTitle(f'Quick Field Keys - Chosen fields: {layer.name()}')
        self.resize(650, 550)
        layout = QVBoxLayout(self)
        self.scope = QLabel(f'Fixed selection: {len(self.ids)} features. Apply changes only checked fields.')
        self.scope.setWordWrap(True)
        layout.addWidget(self.scope)
        choose = QPushButton('Choose visible / editable fields...')
        choose.clicked.connect(self.choose_fields)
        layout.addWidget(choose)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        self.form_widget = QWidget()
        self.form = QFormLayout(self.form_widget)
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
        self.immediate = QCheckBox('Apply Alt+1-9 immediately to layer edits')
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
        for text, callback in (
            ('Apply form edits', self.apply_form), ('Apply pending shortcuts', self.apply_pending),
            ('Undo', self.undo), ('Discard pending', self.discard_pending),
        ):
            button = QPushButton(text)
            button.clicked.connect(callback)
            row.addWidget(button)
        layout.addLayout(row)
        close = QPushButton('Close')
        close.clicked.connect(self.close)
        layout.addWidget(close)
        self.refresh_status()
        layer.destroyed.connect(self.layer_deleted)

    def load_rows(self):
        for wrapper, checkbox in self.rows.values():
            wrapper.blockSignals(True)
            wrapper.deleteLater()
        while self.form.rowCount():
            self.form.removeRow(0)
        self.rows = {}
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
            apply = QCheckBox(f'Change {name}' + ('' if same else ' (mixed / empty)'))
            apply.setChecked(False)
            wrapper.valueChanged.connect(lambda *args, checkbox=apply: checkbox.setChecked(True))
            row = QHBoxLayout()
            row.addWidget(apply)
            row.addWidget(editor, 1)
            self.form.addRow(row)
            self.rows[name] = (wrapper, apply)

    @staticmethod
    def equal(left, right):
        return (QgsVariantUtils.isNull(left) and QgsVariantUtils.isNull(right)) or left == right

    def choose_fields(self, checked=False):
        if self.layer is None:
            self.plugin.warn('The target layer was removed.')
            return
        if self.has_form_edits() and not self.confirm_discard_form():
            return
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
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        layout.addWidget(buttons)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.visible_names = [items.item(i).text() for i in range(items.count())
                                  if items.item(i).checkState() == Qt.CheckState.Checked]
            QgsSettings().setValue(self.setting, json.dumps(self.visible_names))
            self.load_rows()

    def has_form_edits(self):
        return any(checkbox.isChecked() for wrapper, checkbox in self.rows.values())

    def confirm_discard_form(self):
        return QMessageBox.question(
            self, 'Unapplied form values', 'Discard unapplied values in this editor?',
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No) == QMessageBox.StandardButton.Yes

    def apply_form(self, checked=False):
        changes = {(fid, name): wrapper.value()
                   for name, (wrapper, checkbox) in self.rows.items() if checkbox.isChecked()
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
