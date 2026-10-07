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
MENU = '선택 객체 빠른 필드 입력'
KEYS = tuple(str(n) for n in range(1, 10))


def converted_value(field, text, use_null):
    if use_null:
        return None
    result = field.convertCompatible(text)
    # QGIS 3은 (성공 여부, 값), QGIS 4는 변환된 값을 반환합니다.
    if isinstance(result, tuple):
        if not result[0]:
            raise ValueError('필드 자료형에 맞지 않는 값입니다.')
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
            action = QAction(f'빠른 필드 입력 Alt+{key}', self.iface.mainWindow())
            action.triggered.connect(lambda checked=False, k=key: self.apply(k))
            self.iface.registerMainWindowAction(action, f'Alt+{key}')
            self.iface.addPluginToMenu(MENU, action)
            self.actions.append(action)
        action = QAction('필드·값 설정…', self.iface.mainWindow())
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
            self.warn('유효한 벡터 레이어를 선택하세요.')
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
        note = QLabel('현재 활성 레이어의 필드로 설정합니다.\n'
                      '단축키 실행 시 활성 레이어의 선택 객체만 수정합니다.\n'
                      '같은 이름의 필드를 가진 다른 레이어에도 적용됩니다.\n'
                      '기존 값을 덮어쓰며 자동 저장하지 않습니다.')
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
            combo.addItem('(사용 안 함)', '')
            for i in writable_indices(layer):
                field = layer.fields()[i]
                combo.addItem(f'{field.name()} ({field.typeName()})', field.name())
            found = combo.findData(preset.get('field', ''))
            combo.setCurrentIndex(max(0, found))
            text = QLineEdit(str(preset.get('value', '')))
            text.setPlaceholderText('입력값')
            null = QCheckBox('NULL 입력')
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
                            raise ValueError('필드가 없어졌습니다. 설정 창을 다시 여세요.')
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
            self.warn('선택 객체가 없습니다. 아무것도 수정하지 않았습니다.')
            return
        preset = self.presets.get(key, {})
        if not isinstance(preset, dict) or not preset.get('field'):
            self.warn(f'Alt+{key}의 필드·값을 먼저 설정하세요.')
            self.configure()
            return
        index = layer.fields().indexFromName(preset['field'])
        if index < 0 or index not in writable_indices(layer):
            self.warn('설정 필드가 없거나 수정할 수 없습니다. 필드·값 설정을 확인하세요.')
            return
        try:
            value = converted_value(layer.fields()[index], preset.get('value', ''), preset.get('null', False))
        except (ValueError, TypeError, OverflowError) as error:
            self.warn(str(error))
            return
        if layer.readOnly():
            self.warn('읽기 전용 레이어입니다.')
            return
        if not layer.isEditable() and not layer.startEditing():
            self.warn('편집 모드를 시작할 수 없습니다.')
            return
        layer.beginEditCommand(f'Alt+{key}: {preset["field"]} 입력')
        try:
            for fid in ids:
                if not layer.changeAttributeValue(fid, index, value, skipDefaultValues=True):
                    raise RuntimeError(f'객체 {fid} 입력 실패. 이번 실행을 취소했습니다.')
            for fid in ids:
                actual = layer.getFeature(fid).attribute(index)
                if value is not None and actual != value:
                    raise RuntimeError('입력값 검증 실패. 이번 실행을 취소했습니다.')
                if value is None:
                    from qgis.core import QgsVariantUtils
                    if not QgsVariantUtils.isNull(actual):
                        raise RuntimeError('NULL 입력 검증 실패. 이번 실행을 취소했습니다.')
        except Exception as error:
            layer.destroyEditCommand()
            self.warn(str(error))
            return
        layer.endEditCommand()
        layer.triggerRepaint()
        self.iface.messageBar().pushSuccess(
            MENU, f'{layer.name()}: 선택 {len(ids)}개 입력. 저장 전 상태이며 실행 취소할 수 있습니다.')
