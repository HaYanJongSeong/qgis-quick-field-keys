"""SPDX-License-Identifier: GPL-3.0-or-later

Plugin-only shortcut configuration; never change other QGIS bindings.
"""
import json

from qgis.PyQt.QtGui import QKeySequence
from qgis.PyQt.QtCore import Qt
from qgis.PyQt.QtWidgets import (
    QDialog, QDialogButtonBox, QFormLayout, QHBoxLayout, QKeySequenceEdit, QLabel,
    QScrollArea, QStyle, QToolButton, QVBoxLayout, QWidget,
)


ACTIONS = {f'preset_{key}': (f'Preset {key} / 프리셋 {key}', f'Alt+{key}') for key in range(1, 10)}
ACTIONS.update({
    'first': ('First / 처음', 'Alt+Home'),
    'previous': ('Previous / 이전', 'Alt+Left'),
    'next': ('Next / 다음', 'Alt+Right'),
    'last': ('Last / 끝', 'Alt+End'),
    'back': ('Previous view / 직전 화면', 'Alt+Backspace'),
    'flash': ('Flash selected features / 선택 객체 반짝임', ''),
    'undo': ('Feature Undo / 객체 실행 취소', 'Alt+Z'),
    'presets': ('Field value presets / 필드 값 설정', ''),
    'columns': ('Visible columns / 표시 컬럼 선택', ''),
    'refresh': ('Apply filter and reload / 필터 적용·새로고침', ''),
    'expression': ('Expression builder / 표현식 작성기', ''),
    'clear': ('Clear filter input / 필터 입력 지우기', ''),
    'capture': ('Capture current selection / 현재 선택 고정', ''),
    'scope': ('Toggle captured selection only / 고정 선택 제한 전환', ''),
    'immediate': ('Toggle immediate application / 단축키 즉시 적용 전환', ''),
    'zoom': ('Cycle zoom mode / 줌 방식 순환', ''),
    'layer': ('Choose layer / 레이어 선택', ''),
    'sort': ('Choose sort field / 정렬 필드 선택', ''),
    'save_feature': ('Save target layer to file / 대상 레이어 파일 저장', ''),
    'lock_field': ('Lock/unlock focused field / 포커스 필드 잠금 전환', ''),
    'settings': ('Shortcut settings / 단축키 설정', ''),
})


def normalized(values):
    result, used = {}, {}
    for name in ACTIONS:
        value = values.get(name, '')
        if not isinstance(value, str):
            raise ValueError('Invalid shortcut value / 잘못된 단축키 값')
        sequence = QKeySequence(value)
        if sequence.count() > 1 or (value.strip() and sequence.isEmpty()):
            raise ValueError('Use one key combination per action / 기능마다 키 조합 하나를 지정하세요.')
        key = sequence.toString(QKeySequence.SequenceFormat.PortableText)
        if key:
            combination = sequence[0]
            modifiers = combination.keyboardModifiers()
            function_key = Qt.Key.Key_F1.value <= combination.key().value <= Qt.Key.Key_F35.value
            if not function_key and not (modifiers & (Qt.KeyboardModifier.ControlModifier | Qt.KeyboardModifier.AltModifier | Qt.KeyboardModifier.MetaModifier)):
                raise ValueError('Use Ctrl/Alt/Meta or a function key to avoid triggering edits while typing.\n입력 중 오작동을 막으려면 Ctrl/Alt/Meta 조합 또는 기능키를 사용하세요.')
        if key and key in used:
            raise ValueError(f'Duplicate shortcut {key}: {ACTIONS[used[key]][0]} / {ACTIONS[name][0]}')
        if key:
            used[key] = name
        result[name] = key
    return result


def load(settings):
    defaults = {name: default for name, (label, default) in ACTIONS.items()}
    try:
        saved = json.loads(settings.value('quick_field_keys/shortcuts', '{}'))
        if not isinstance(saved, dict):
            return defaults
        defaults.update({name: value for name, value in saved.items() if name in ACTIONS})
        return normalized(defaults)
    except (TypeError, ValueError):
        return {name: default for name, (label, default) in ACTIONS.items()}


def configure(plugin):
    dialog = QDialog(plugin.iface.mainWindow())
    dialog.setWindowTitle('Shortcut settings / 단축키 설정')
    dialog.resize(640, 560)
    layout = QVBoxLayout(dialog)
    note = QLabel('Press Ctrl/Alt/Meta + a key, or a function key. Clear a box to disable its shortcut.\nCtrl/Alt/Meta 조합이나 기능키를 누르세요. 비우면 단축키를 사용하지 않습니다.\nSave commits ALL target-layer edits / 저장은 대상 레이어의 모든 미저장 편집을 파일에 반영합니다.')
    note.setWordWrap(True)
    layout.addWidget(note)
    scroll = QScrollArea()
    scroll.setWidgetResizable(True)
    content = QWidget()
    form = QFormLayout(content)
    controls = {}
    for name, (label, default) in ACTIONS.items():
        edit = QKeySequenceEdit(QKeySequence(plugin.shortcut_map[name]))
        edit.setObjectName(name)
        edit.setToolTip(f'{label}\nPress a new key combination; clear to disable.\n키 조합을 눌러 지정합니다. 비우면 미지정 상태입니다.')
        clear = QToolButton(content)
        clear.setObjectName(f'clear_{name}')
        clear.setIcon(dialog.style().standardIcon(QStyle.StandardPixmap.SP_DialogCancelButton))
        clear.setAccessibleName(f'Clear shortcut / 단축키 지정 해제: {label}')
        clear.setToolTip(f'Clear shortcut — Remove the assignment for {label}; click Save to apply.\n단축키 지정 해제 — 이 기능의 키 지정을 비웁니다. 저장을 눌러야 적용됩니다.')
        clear.clicked.connect(edit.clear)
        row = QHBoxLayout()
        row.addWidget(edit, 1)
        row.addWidget(clear)
        form.addRow(label, row)
        controls[name] = edit
    scroll.setWidget(content)
    layout.addWidget(scroll)
    buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel | QDialogButtonBox.StandardButton.RestoreDefaults)
    buttons.button(QDialogButtonBox.StandardButton.Save).setToolTip('Save shortcuts — Validate and apply only this plugin\'s bindings.\n단축키 저장 — 중복·충돌을 확인하고 이 플러그인의 단축키만 적용합니다.')
    buttons.button(QDialogButtonBox.StandardButton.Cancel).setToolTip('Cancel — Keep current shortcuts.\n취소 — 기존 단축키를 유지합니다.')
    buttons.button(QDialogButtonBox.StandardButton.RestoreDefaults).setToolTip('Restore defaults — Fill in default keys; Save is still required.\n기본값 복원 — 기본 키를 입력합니다. 저장을 눌러야 적용됩니다.')

    def save():
        try:
            plugin.set_shortcuts({name: edit.keySequence().toString(QKeySequence.SequenceFormat.PortableText) for name, edit in controls.items()})
        except ValueError as error:
            plugin.warn(str(error))
            return
        dialog.accept()

    def defaults():
        for name, edit in controls.items():
            edit.setKeySequence(QKeySequence(ACTIONS[name][1]))

    buttons.accepted.connect(save)
    buttons.rejected.connect(dialog.reject)
    buttons.button(QDialogButtonBox.StandardButton.RestoreDefaults).clicked.connect(defaults)
    layout.addWidget(buttons)
    try:
        dialog.exec()
    finally:
        dialog.deleteLater()
