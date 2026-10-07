"""SPDX-License-Identifier: GPL-3.0-or-later"""
import json
from pathlib import Path

from qgis.core import QgsFields, QgsSettings, QgsVectorLayer
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

    def unload(self):
        for action in self.actions:
            self.iface.unregisterMainWindowAction(action)
            self.iface.removePluginMenu(MENU, action)
            self.iface.removeToolBarIcon(action)
            action.deleteLater()
        self.actions.clear()

    def warn(self, message):
        self.iface.messageBar().pushWarning(MENU, message)

    def active_vector(self):
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
        if layer.readOnly():
            self.warn('The layer is read-only.')
            return
        if not layer.isEditable() and not layer.startEditing():
            self.warn('Could not start editing the layer.')
            return
        layer.beginEditCommand(f'Alt+{key}: set {preset["field"]}')
        try:
            for fid in ids:
                if not layer.changeAttributeValue(fid, index, value, skipDefaultValues=True):
                    raise RuntimeError(f'Could not update feature {fid}. This operation was reverted.')
            for fid in ids:
                actual = layer.getFeature(fid).attribute(index)
                if value is not None and actual != value:
                    raise RuntimeError('Value verification failed. This operation was reverted.')
                if value is None:
                    from qgis.core import QgsVariantUtils
                    if not QgsVariantUtils.isNull(actual):
                        raise RuntimeError('NULL verification failed. This operation was reverted.')
        except Exception as error:
            layer.destroyEditCommand()
            self.warn(str(error))
            return
        layer.endEditCommand()
        layer.triggerRepaint()
        self.iface.messageBar().pushSuccess(
            MENU, f'{layer.name()}: updated {len(ids)} selected features. Changes are unsaved and can be undone.')
