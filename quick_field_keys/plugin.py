"""SPDX-License-Identifier: GPL-3.0-or-later"""
import json
from pathlib import Path

from qgis.core import QgsFields, QgsSettings, QgsVariantUtils, QgsVectorLayer
from qgis.PyQt.QtCore import Qt
from qgis.PyQt.QtGui import QIcon
try:
    from qgis.PyQt.QtGui import QAction
except ImportError:
    from qgis.PyQt.QtWidgets import QAction
from qgis.PyQt.QtWidgets import (
    QCheckBox, QComboBox, QDialog, QDialogButtonBox, QFormLayout, QHBoxLayout,
    QLabel, QLineEdit, QVBoxLayout,
)


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

    def load_presets(self):
        try:
            data = json.loads(QgsSettings().value(SETTING, '{}'))
            return data if isinstance(data, dict) else {}
        except (TypeError, ValueError):
            return {}

    def initGui(self):
        for key in KEYS:
            action = QAction(f'Quick Field Keys: Alt+{key}', self.iface.mainWindow())
            action.triggered.connect(lambda checked=False, k=key: self.apply(k))
            self.iface.registerMainWindowAction(action, f'Alt+{key}')
            self.iface.addPluginToMenu(MENU, action)
            self.actions.append(action)
        action = QAction('Configure fields and values...', self.iface.mainWindow())
        action.setIcon(QIcon(str(Path(__file__).with_name('icon.svg'))))
        action.triggered.connect(self.configure)
        self.iface.addPluginToMenu(MENU, action)
        self.iface.addToolBarIcon(action)
        self.actions.append(action)
        action = QAction('Feature navigation and editing', self.iface.mainWindow())
        action.setIcon(QIcon(str(Path(__file__).with_name('icon.svg'))))
        action.setCheckable(True)
        action.triggered.connect(self.toggle_navigation)
        self.iface.addPluginToMenu(MENU, action)
        self.iface.addToolBarIcon(action)
        self.actions.append(action)
        self.navigation_action = action
        action = QAction('Edit chosen fields / pending shortcuts...', self.iface.mainWindow())
        action.triggered.connect(self.open_field_editor)
        self.iface.addPluginToMenu(MENU, action)
        self.actions.append(action)

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
            self.iface.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, self.dock_widget)
        self.dock_widget.setVisible(checked)
        if checked:
            self.dock_widget.raise_()

    def unload(self):
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

    def open_field_editor(self, checked=False):
        layer = self.active_vector()
        if layer is None:
            return
        if self.field_editor is not None:
            if not self.field_editor.close():
                return
            self.field_editor.deleteLater()
        from .field_editor import FieldEditor
        self.field_editor = FieldEditor(self, layer)
        self.field_editor.show()
        self.field_editor.raise_()

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
        self.pending_layer = None
        self.refresh_edit_windows()
        return True

    def discard_pending(self):
        self.pending_changes = {}
        self.pending_undo = []
        self.pending_layer = None
        self.refresh_edit_windows()

    def undo_edit(self, layer):
        if layer is None:
            self.warn('The target layer is unavailable.')
            return
        if self.pending_layer is layer and self.pending_undo:
            self.pending_changes = self.pending_undo.pop()
            if not self.pending_changes:
                self.pending_layer = None
        elif layer.isEditable() and layer.undoStack().canUndo():
            layer.undoStack().undo()
        else:
            self.warn('Nothing to undo for this layer.')
        self.refresh_edit_windows()

    def apply_changes(self, layer, changes, title):
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
        converted = []
        try:
            for (fid, name), value in changes.items():
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
        layer.beginEditCommand(title)
        try:
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
        layer.endEditCommand()
        layer.triggerRepaint()
        self.iface.messageBar().pushSuccess(
            MENU, f'{layer.name()}: updated {len({fid for fid, _, _ in converted})} features. Changes are unsaved and can be undone.')
        self.refresh_edit_windows()
        return True

    def warn(self, message):
        self.iface.messageBar().pushWarning(MENU, message)

    def active_vector(self):
        if self.dock_widget is not None and self.dock_widget.isVisible():
            dock_layer = self.dock_widget.layer
            if dock_layer is not None and dock_layer is not self.iface.activeLayer():
                self.warn('Activate the navigator layer before applying presets or editing chosen fields.')
                return None
        layer = self.iface.activeLayer()
        if not isinstance(layer, QgsVectorLayer) or not layer.isValid():
            self.warn('Select a valid vector layer.')
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
        note = QLabel('Configure presets using fields from the active layer.\n'
                      'Shortcuts change only selected features in the active layer.\n'
                      'Presets also apply to other layers with matching field names.\n'
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
            null.setChecked(bool(preset.get('null', False)))
            text.setEnabled(not null.isChecked())
            null.toggled.connect(lambda enabled, widget=text: widget.setEnabled(not enabled))
            row = QHBoxLayout()
            row.addWidget(combo, 1)
            row.addWidget(text, 1)
            row.addWidget(null)
            form.addRow(f'Alt+{key}', row)
            controls[key] = (combo, text, null)
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
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
            self.apply_changes(layer, changes, f'Alt+{key}: set {preset["field"]}')
        else:
            if self.pending_layer is not None and self.pending_layer is not layer:
                self.warn('Apply or discard pending values before staging values for another layer.')
                return
            self.pending_layer = layer
            self.pending_undo.append(dict(self.pending_changes))
            self.pending_changes.update(changes)
            self.refresh_edit_windows()
            self.iface.messageBar().pushSuccess(
                MENU, f'Staged {len(ids)} features. No layer values changed. Use Apply pending shortcuts.')
