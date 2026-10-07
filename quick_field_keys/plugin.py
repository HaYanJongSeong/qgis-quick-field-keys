"""SPDX-License-Identifier: GPL-3.0-or-later"""
import json
from pathlib import Path

from qgis.core import QgsFields, QgsSettings, QgsVariantUtils, QgsVectorLayer
from qgis.PyQt.QtCore import Qt
from qgis.PyQt.QtGui import QIcon, QKeySequence, QShortcut
try:
    from qgis.PyQt.QtGui import QAction
except ImportError:
    from qgis.PyQt.QtWidgets import QAction
from qgis.PyQt.QtWidgets import (
    QCheckBox, QComboBox, QDialog, QDialogButtonBox, QFormLayout, QHBoxLayout,
    QLabel, QLineEdit, QVBoxLayout,
)
from . import shortcuts as shortcut_config


SETTING = 'quick_field_keys/presets'
MENU = 'Quick Field Keys'
KEYS = tuple(str(n) for n in range(1, 10))


def converted_value(field, text, use_null):
    if use_null:
        return None
    result = field.convertCompatible(text)
    # Accept both the historical tuple and the QGIS 4 converted-value result.
    if isinstance(result, tuple):
        if not result[0]:
            raise ValueError('The value is incompatible with the field type.')
        return result[1]
    return result


def writable_indices(layer):
    fields = layer.fields()
    primary = set(layer.dataProvider().pkAttributeIndexes())
    return [i for i in range(len(fields))
            if fields.fieldOrigin(i) in (QgsFields.OriginProvider, QgsFields.OriginEdit)
            and not (fields.fieldOrigin(i) == QgsFields.OriginProvider
                      and fields.fieldOriginIndex(i) in primary)]


def locked_names(layer):
    try:
        names = json.loads(QgsSettings().value(f'quick_field_keys/locked_fields/{layer.id()}', '[]'))
        return set(name for name in names if isinstance(name, str)) if isinstance(names, list) else set()
    except (TypeError, ValueError):
        return set()


class QuickFieldKeys:
    def __init__(self, iface):
        self.iface = iface
        self.actions = []
        self.presets = self.load_presets()
        self.dock_widget = None
        self.navigation_action = None
        self.field_editor = None
        self.immediate = QgsSettings().value('quick_field_keys/immediate', True, type=bool)
        self.pending_layer = None
        self.pending_changes = {}
        self.pending_undo = []
        self.pending_targets = []
        self.applied_history = []
        self.history_layers = {}
        self._writing = False
        self.shortcut_map = shortcut_config.load(QgsSettings())
        self.preset_actions = {}

    def load_presets(self):
        try:
            data = json.loads(QgsSettings().value(SETTING, '{}'))
            return data if isinstance(data, dict) else {}
        except (TypeError, ValueError):
            return {}

    def initGui(self):
        for key in KEYS:
            action = QAction(f'Quick Field Keys: preset {key} ({self.shortcut_key(f"preset_{key}") or "unassigned"})', self.iface.mainWindow())
            action.triggered.connect(lambda checked=False, k=key: self.apply(k))
            binding = self.shortcut_key(f'preset_{key}')
            if binding:
                self.iface.registerMainWindowAction(action, binding)
            self.preset_actions[key] = action
            self.iface.addPluginToMenu(MENU, action)
            self.actions.append(action)
        action = QAction('Feature navigation and editing', self.iface.mainWindow())
        action.setToolTip('Quick Field Keys — Open or hide the navigation and editing panel.\n빠른 필드 입력 — 객체 탐색과 선택 필드 편집 패널을 열거나 숨깁니다.')
        action.setIcon(QIcon(str(Path(__file__).with_name('icon.svg'))))
        action.setCheckable(True)
        action.triggered.connect(self.toggle_navigation)
        self.iface.addPluginToMenu(MENU, action)
        self.iface.addToolBarIcon(action)
        self.actions.append(action)
        self.navigation_action = action

        for text, callback in (
            ('Apply pending shortcuts', self.apply_pending),
            ('Discard pending shortcuts', self.discard_pending),
        ):
            action = QAction(text, self.iface.mainWindow())
            action.triggered.connect(lambda checked=False, fn=callback: fn())
            self.iface.addPluginToMenu(MENU, action)
            self.actions.append(action)

    def toggle_navigation(self, checked=False):
        if self.dock_widget is None:
            from .navigation import QuickFieldNavigator
            self.dock_widget = QuickFieldNavigator(self)
            self.dock_widget.visibilityChanged.connect(self.navigation_action.setChecked)
            if not self.iface.mainWindow().restoreDockWidget(self.dock_widget):
                self.iface.addDockWidget(self.dock_widget.preferred_dock_area(), self.dock_widget)
            self.dock_widget.restore_layout()
        if checked:
            self.dock_widget.restore_on_open()
        self.dock_widget.setVisible(checked)
        if checked:
            self.dock_widget.raise_()

    def unload(self):
        for layer, _, stack_slot, stop_slot, destroy_slot in list(self.history_layers.values()):
            try:
                layer.undoStack().indexChanged.disconnect(stack_slot)
                layer.editingStopped.disconnect(stop_slot)
                layer.destroyed.disconnect(destroy_slot)
            except (RuntimeError, TypeError):
                pass
        self.history_layers.clear()
        self.applied_history.clear()
        if self.pending_changes:
            self.warn('Unapplied shortcut values are being discarded on plugin unload.')
        if self.field_editor is not None:
            if self.field_editor.has_form_edits():
                self.warn('Unapplied form inputs will not be saved when the plugin is unloaded.')
            self.field_editor.close()
            self.field_editor.deleteLater()
            self.field_editor = None
        if self.dock_widget is not None:
            self.dock_widget.shutdown()
            self.iface.removeDockWidget(self.dock_widget)
            self.dock_widget.deleteLater()
            self.dock_widget = None
        for action in self.actions:
            self.iface.unregisterMainWindowAction(action)
            self.iface.removePluginMenu(MENU, action)
            self.iface.removeToolBarIcon(action)
            action.deleteLater()
        self.actions.clear()
        self.preset_actions.clear()

    def shortcut_key(self, name):
        return self.shortcut_map[name]

    def configure_shortcuts(self, checked=False):
        shortcut_config.configure(self)

    def set_shortcuts(self, values):
        result = shortcut_config.normalized(values)
        own = list(self.actions)
        if self.dock_widget is not None:
            own.extend(self.dock_widget.shortcuts)
        occupied = {}
        for action in self.iface.mainWindow().findChildren(QAction):
            if action not in own:
                for sequence in action.shortcuts():
                    key = sequence.toString(QKeySequence.SequenceFormat.PortableText)
                    if key:
                        occupied[key] = action.text()
        for shortcut in self.iface.mainWindow().findChildren(QShortcut):
            if shortcut not in own and shortcut.isEnabled():
                key = shortcut.key().toString(QKeySequence.SequenceFormat.PortableText)
                if key:
                    occupied[key] = shortcut.objectName() or 'another QGIS shortcut'
        for name, key in result.items():
            if key and key in occupied:
                raise ValueError(f'Shortcut conflict / 단축키 충돌: {key} ({occupied[key]})')
        previous = dict(self.shortcut_map)
        try:
            for key, action in self.preset_actions.items():
                self.iface.unregisterMainWindowAction(action)
                binding = result[f'preset_{key}']
                if binding:
                    if self.iface.registerMainWindowAction(action, binding) is False:
                        raise ValueError(f'Could not register shortcut / 단축키 등록 실패: {binding}')
                else:
                    action.setShortcut(QKeySequence())
        except Exception:
            for key, action in self.preset_actions.items():
                self.iface.unregisterMainWindowAction(action)
                binding = previous[f'preset_{key}']
                if binding:
                    self.iface.registerMainWindowAction(action, binding)
                else:
                    action.setShortcut(QKeySequence())
            raise
        self.shortcut_map = result
        QgsSettings().setValue('quick_field_keys/shortcuts', json.dumps(result))
        for key, action in self.preset_actions.items():
            binding = result[f'preset_{key}']
            action.setText(f'Quick Field Keys: preset {key} ({binding or "unassigned"})')
        if self.dock_widget is not None:
            self.dock_widget.update_bindings()

    def open_field_editor(self, checked=False, show=True):
        layer = self.active_vector()
        if layer is None:
            return False
        if self.field_editor is not None:
            if not self.field_editor.close():
                return False
            self.field_editor.deleteLater()
        from .field_editor import FieldEditor
        self.field_editor = FieldEditor(self, layer)
        if show:
            self.field_editor.show()
            self.field_editor.raise_()
        return True

    def set_immediate(self, enabled):
        self.immediate = bool(enabled)
        QgsSettings().setValue('quick_field_keys/immediate', self.immediate)
        self.refresh_edit_windows()

    def refresh_edit_windows(self):
        if self.field_editor is not None:
            self.field_editor.refresh_status()
        if self.dock_widget is not None:
            self.dock_widget.refresh_quick_status()

    def apply_pending(self):
        if not self.pending_changes:
            self.warn('No pending shortcut values.')
            return False
        if not self.apply_changes(self.pending_layer, self.pending_changes, 'Apply pending shortcuts'):
            return False
        self.pending_changes = {}
        self.pending_undo = []
        self.pending_targets = []
        self.pending_layer = None
        self.refresh_edit_windows()
        return True

    def discard_pending(self):
        self.pending_changes = {}
        self.pending_undo = []
        self.pending_targets = []
        self.pending_layer = None
        self.refresh_edit_windows()

    def undo_edit(self, layer):
        if self.pending_layer is not None and self.pending_undo:
            target_layer = self.pending_layer
            try:
                if not target_layer.isValid():
                    raise ValueError('The pending target layer is unavailable. Discard its pending values explicitly.')
            except (RuntimeError, ValueError) as error:
                self.warn(str(error))
                return False
            targets = self.pending_targets[-1]
            while self.pending_targets and self.pending_targets[-1] == targets:
                self.pending_targets.pop()
                self.pending_changes = self.pending_undo.pop()
            if not self.pending_changes:
                self.pending_layer = None
            self.refresh_edit_windows()
            self.reveal_undone(target_layer, targets)
            return True
        if not self.applied_history:
            self.warn('No Quick Field Keys feature edits to undo. Other tools\' edits are not undone.')
            return False
        entry = self.applied_history[-1]
        target_layer = entry['layer']
        try:
            if not target_layer.isValid() or not target_layer.isEditable():
                raise ValueError('The last edited layer is unavailable or its edit session ended.')
            for (fid, name), expected in entry['after'].items():
                feature = target_layer.getFeature(fid)
                if not feature.isValid() or target_layer.fields().indexFromName(name) < 0:
                    raise ValueError('An edited feature or field was removed. Nothing was reverted.')
                if not self.same_value(feature[name], expected):
                    raise ValueError('An edited value changed outside this history. Nothing was reverted; other edits are protected.')
        except (RuntimeError, ValueError) as error:
            self.warn(str(error))
            return False
        if not self.apply_changes(target_layer, entry['before'], 'Undo Quick Field Keys feature edits', record_history=False):
            return False
        self.applied_history.pop()
        self.reveal_undone(target_layer, entry['targets'])
        return True

    @staticmethod
    def same_value(left, right):
        return (QgsVariantUtils.isNull(left) and QgsVariantUtils.isNull(right)) or left == right

    def track_history_layer(self, layer):
        key = layer.id()
        if key in self.history_layers:
            return

        def index_changed(index):
            state = self.history_layers.get(key)
            if state is not None:
                if index < state[1] and not self._writing:
                    self.clear_feature_history(key)
                state[1] = index

        def stopped():
            self.clear_feature_history(key)

        def destroyed(*args):
            self.clear_feature_history(key)
            self.history_layers.pop(key, None)

        self.history_layers[key] = [layer, layer.undoStack().index(), index_changed, stopped, destroyed]
        layer.undoStack().indexChanged.connect(index_changed)
        layer.editingStopped.connect(stopped)
        layer.destroyed.connect(destroyed)

    def clear_feature_history(self, layer_id):
        self.applied_history = [entry for entry in self.applied_history if entry['layer_id'] != layer_id]

    def remember_feature_edit(self, layer, before, after):
        targets = tuple(sorted({fid for fid, name in after}))
        previous = self.applied_history[-1] if self.applied_history else None
        merge = previous is not None and previous['layer'] is layer and previous['targets'] == targets
        if merge:
            merge = all(self.same_value(before.get(key, layer.getFeature(key[0])[key[1]]), expected)
                        for key, expected in previous['after'].items())
        if merge:
            for key, value in before.items():
                previous['before'].setdefault(key, value)
            previous['after'].update(after)
        else:
            self.applied_history.append({'layer': layer, 'layer_id': layer.id(), 'targets': targets,
                                         'before': before, 'after': after})
            # ponytail: retain 200 in-session feature groups; no saved-file or cross-session Undo.
            del self.applied_history[:-200]

    def reveal_undone(self, layer, targets):
        try:
            if self.dock_widget is not None:
                self.dock_widget.reveal_undone(layer, targets)
            else:
                self.iface.setActiveLayer(layer)
                layer.selectByIds(list(targets))
                canvas = self.iface.mapCanvas()
                canvas.zoomToSelected(layer)
                canvas.flashFeatureIds(layer, list(targets))
        except Exception as error:
            self.warn(f'Values reverted, but map focus or flash failed: {error}')

    def apply_changes(self, layer, changes, title, record_history=True):
        try:
            available = isinstance(layer, QgsVectorLayer) and layer.isValid() and not layer.readOnly()
        except RuntimeError:
            available = False
        if not available:
            self.warn('The target layer is unavailable or read-only.')
            return False
        if not changes:
            self.warn('No changed fields to apply.')
            return False
        allowed = writable_indices(layer)
        locks = locked_names(layer)
        converted = []
        try:
            for (fid, name), value in changes.items():
                if name in locks:
                    raise ValueError(f'Field "{name}" is locked. Unlock it before applying or undoing changes.')
                index = layer.fields().indexFromName(name)
                if index not in allowed or not layer.getFeature(fid).isValid():
                    raise ValueError('A target feature or writable field no longer exists.')
                value = converted_value(layer.fields()[index], value, QgsVariantUtils.isNull(value))
                converted.append((fid, index, value))
        except (ValueError, TypeError, OverflowError) as error:
            self.warn(str(error))
            return False
        if not layer.isEditable() and not layer.startEditing():
            self.warn('Could not start editing the layer.')
            return False
        self.track_history_layer(layer)
        before = {(fid, layer.fields()[index].name()): layer.getFeature(fid).attribute(index)
                  for fid, index, value in converted}
        self._writing = True
        try:
            layer.beginEditCommand(title)
            for fid, index, value in converted:
                if not layer.changeAttributeValue(fid, index, value, skipDefaultValues=True):
                    raise RuntimeError(f'Could not update feature {fid}. This operation was reverted.')
            for fid, index, value in converted:
                actual = layer.getFeature(fid).attribute(index)
                if ((QgsVariantUtils.isNull(value) and not QgsVariantUtils.isNull(actual))
                        or (not QgsVariantUtils.isNull(value) and actual != value)):
                    raise RuntimeError('Value verification failed. This operation was reverted.')
        except Exception as error:
            layer.destroyEditCommand()
            self.warn(str(error))
            return False
        finally:
            self._writing = False
        layer.endEditCommand()
        if record_history:
            after = {(fid, layer.fields()[index].name()): value for fid, index, value in converted}
            self.remember_feature_edit(layer, before, after)
        layer.triggerRepaint()
        self.iface.messageBar().pushSuccess(
            MENU, f'{layer.name()}: updated {len({fid for fid, _, _ in converted})} features. Changes are unsaved and can be undone.')
        self.refresh_edit_windows()
        return True

    def warn(self, message):
        self.iface.messageBar().pushWarning(MENU, message)

    def active_vector(self):
        # Once the panel exists, its chosen layer is the target even while hidden.
        layer = self.dock_widget.layer if self.dock_widget is not None else self.iface.activeLayer()
        try:
            valid = isinstance(layer, QgsVectorLayer) and layer.isValid()
        except RuntimeError:
            valid = False
        if not valid:
            self.warn('Choose a valid target layer in the navigator. / 이동 패널에서 유효한 반영 대상 레이어를 지정하세요.')
            return None
        return layer

    def configure(self, checked=False):
        layer = self.active_vector()
        if layer is None:
            return
        dialog = QDialog(self.iface.mainWindow())
        dialog.setWindowTitle(MENU)
        dialog.resize(700, 450)
        layout = QVBoxLayout(dialog)
        note = QLabel(f'Target layer: {layer.name()}\n'
                      'Presets use the navigator\'s designated layer, not the active layer panel item.\n'
                      'Shortcuts change only selected features in that designated layer.\n'
                      'Existing values are overwritten. Changes are not saved automatically.')
        note.setWordWrap(True)
        layout.addWidget(note)
        form = QFormLayout()
        layout.addLayout(form)
        controls = {}
        for key in KEYS:
            preset = self.presets.get(key, {})
            if not isinstance(preset, dict):
                preset = {}
            combo = QComboBox()
            combo.addItem('(Disabled)', '')
            for i in writable_indices(layer):
                field = layer.fields()[i]
                combo.addItem(f'{field.name()} ({field.typeName()})', field.name())
            found = combo.findData(preset.get('field', ''))
            combo.setCurrentIndex(max(0, found))
            text = QLineEdit(str(preset.get('value', '')))
            text.setPlaceholderText('Value')
            null = QCheckBox('Set NULL')
            null.setToolTip('Set NULL — Assign NULL instead of the entered text.\nNULL 지정 — 입력한 값 대신 NULL을 적용합니다.')
            null.setChecked(bool(preset.get('null', False)))
            text.setEnabled(not null.isChecked())
            null.toggled.connect(lambda enabled, widget=text: widget.setEnabled(not enabled))
            row = QHBoxLayout()
            row.addWidget(combo, 1)
            row.addWidget(text, 1)
            row.addWidget(null)
            form.addRow(f'Preset {key} ({self.shortcut_key(f"preset_{key}") or "unassigned"})', row)
            controls[key] = (combo, text, null)
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.button(QDialogButtonBox.StandardButton.Ok).setToolTip('OK — Validate and save Alt+1–9 presets; do not edit feature values yet.\n확인 — Alt+1~9 프리셋을 검증하고 저장합니다. 객체 값은 아직 수정하지 않습니다.')
        buttons.button(QDialogButtonBox.StandardButton.Cancel).setToolTip('Cancel — Close without changing the saved presets.\n취소 — 저장된 프리셋을 변경하지 않고 닫습니다.')
        layout.addWidget(buttons)
        buttons.rejected.connect(dialog.reject)

        def save():
            presets = {}
            try:
                for key, (combo, text, null) in controls.items():
                    name = combo.currentData()
                    if name:
                        index = layer.fields().indexFromName(name)
                        if index < 0:
                            raise ValueError('The field no longer exists. Reopen the settings dialog.')
                        converted_value(layer.fields()[index], text.text(), null.isChecked())
                    presets[key] = {'field': name, 'value': text.text(), 'null': null.isChecked()}
            except (ValueError, TypeError, OverflowError) as error:
                self.warn(str(error))
                return
            QgsSettings().setValue(SETTING, json.dumps(presets, ensure_ascii=False))
            self.presets = presets
            dialog.accept()

        buttons.accepted.connect(save)
        dialog.exec()

    def apply(self, key):
        layer = self.active_vector()
        if layer is None:
            return
        ids = layer.selectedFeatureIds()
        if not ids:
            self.warn('No features selected. Nothing was changed.')
            return
        preset = self.presets.get(key, {})
        if not isinstance(preset, dict) or not preset.get('field'):
            self.warn(f'Configure a field and value for Alt+{key} first.')
            self.configure()
            return
        index = layer.fields().indexFromName(preset['field'])
        if preset['field'] in locked_names(layer):
            self.warn(f'Field "{preset["field"]}" is locked. No values were changed or staged.')
            return
        if index < 0 or index not in writable_indices(layer):
            self.warn('The configured field is missing or not writable. Check the preset.')
            return
        try:
            value = converted_value(layer.fields()[index], preset.get('value', ''), preset.get('null', False))
        except (ValueError, TypeError, OverflowError) as error:
            self.warn(str(error))
            return
        changes = {(fid, preset['field']): value for fid in ids}
        if self.immediate:
            self.apply_changes(layer, changes, f'Preset {key}: set {preset["field"]}')
        else:
            if self.pending_layer is not None and self.pending_layer is not layer:
                self.warn('Apply or discard pending values before staging values for another layer.')
                return
            self.pending_layer = layer
            self.pending_undo.append(dict(self.pending_changes))
            self.pending_targets.append(tuple(sorted(ids)))
            self.pending_changes.update(changes)
            self.refresh_edit_windows()
            self.iface.messageBar().pushSuccess(
                MENU, f'Staged {len(ids)} features. No layer values changed. Use Apply pending shortcuts.')
