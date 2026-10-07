"""QGIS Python에서 실행합니다. 메모리 레이어 외에는 수정하지 않습니다."""
import importlib.util
from pathlib import Path
from qgis.core import QgsDefaultValue, QgsFeature, QgsField, QgsVectorLayer, QgsVariantUtils
from qgis.PyQt.QtCore import QMetaType
from qgis.PyQt.QtWidgets import QMainWindow

path = Path(__file__).resolve().parents[1] / 'quick_field_keys' / 'plugin.py'
spec = importlib.util.spec_from_file_location('quick_field_keys_test', path)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class TestBar:
    def __init__(self):
        self.messages = []

    def pushWarning(self, *args):
        self.messages.append(('warning', args))

    def pushSuccess(self, *args):
        self.messages.append(('success', args))


class TestIface:
    def __init__(self, layer):
        self.layer = layer
        self.bar = TestBar()
        self.window = QMainWindow()
        self.shortcuts = {}

    def mainWindow(self):
        return self.window

    def registerMainWindowAction(self, action, shortcut):
        self.shortcuts[shortcut] = action

    def unregisterMainWindowAction(self, action):
        self.shortcuts = {k: v for k, v in self.shortcuts.items() if v != action}

    def addPluginToMenu(self, *args):
        pass

    def removePluginMenu(self, *args):
        pass

    def addToolBarIcon(self, *args):
        pass

    def removeToolBarIcon(self, *args):
        pass

    def activeLayer(self):
        return self.layer

    def messageBar(self):
        return self.bar


layer = QgsVectorLayer('Point?crs=EPSG:4326', '플러그인 메모리 테스트', 'memory')
provider = layer.dataProvider()
provider.addAttributes([QgsField('status', QMetaType.Type.QString),
                        QgsField('number', QMetaType.Type.Int)])
layer.updateFields()
features = []
for n in range(3):
    feature = QgsFeature(layer.fields())
    feature.setAttributes(['원래값', n])
    features.append(feature)
assert provider.addFeatures(features)[0]
layer.setDefaultValueDefinition(1, QgsDefaultValue('99', True))
ids = [f.id() for f in layer.getFeatures()]
fake = TestIface(layer)
plugin = module.QuickFieldKeys(fake)
plugin.presets = {'1': {'field': 'status', 'value': '완료', 'null': False},
                  '2': {'field': 'number', 'value': '12', 'null': False}}
plugin.initGui()
assert set(fake.shortcuts) == {f'Alt+{n}' for n in range(1, 10)}

plugin.apply('1')
assert not layer.isEditable()
assert fake.bar.messages[-1][0] == 'warning'
layer.selectByIds(ids[:2])
fake.shortcuts['Alt+1'].trigger()
assert layer.isEditable()
assert [layer.getFeature(fid)['status'] for fid in ids] == ['완료', '완료', '원래값']
assert [layer.getFeature(fid)['number'] for fid in ids] == [0, 1, 2]
assert fake.bar.messages[-1][0] == 'success'
layer.undoStack().undo()
assert all(layer.getFeature(fid)['status'] == '원래값' for fid in ids)

plugin.apply('2')
assert [layer.getFeature(fid)['number'] for fid in ids] == [12, 12, 2]
layer.undoStack().undo()
plugin.presets['2']['value'] = '숫자 아님'
plugin.apply('2')
assert [layer.getFeature(fid)['number'] for fid in ids] == [0, 1, 2]
assert fake.bar.messages[-1][0] == 'warning'
plugin.presets['2']['null'] = True
plugin.apply('2')
assert all(QgsVariantUtils.isNull(layer.getFeature(fid)['number']) for fid in ids[:2])
layer.undoStack().undo()

# Alt+3부터 Alt+9까지 각 QAction이 자기 설정을 사용해야 합니다.
for n in range(3, 10):
    plugin.presets[str(n)] = {'field': 'number', 'value': str(n), 'null': False}
    fake.shortcuts[f'Alt+{n}'].trigger()
    assert [layer.getFeature(fid)['number'] for fid in ids] == [n, n, 2]
    assert fake.bar.messages[-1][0] == 'success'
    layer.undoStack().undo()

# 실행 도중 실패하더라도 기존 편집 내용은 유지하고 이번 명령만 취소합니다.
layer.beginEditCommand('기존 사용자 편집')
assert layer.changeAttributeValue(ids[2], 0, '기존 편집 유지')
layer.endEditCommand()
original_change = layer.changeAttributeValue
calls = []


def fail_second(*args, **kwargs):
    calls.append(args)
    return False if len(calls) == 2 else original_change(*args, **kwargs)


layer.changeAttributeValue = fail_second
plugin.apply('1')
layer.changeAttributeValue = original_change
assert fake.bar.messages[-1][0] == 'warning'
assert [layer.getFeature(fid)['status'] for fid in ids] == ['원래값', '원래값', '기존 편집 유지']
assert [f['status'] for f in provider.getFeatures()] == ['원래값'] * 3
assert layer.rollBack()

# 설정 창 생성은 검사하지만 설정 저장이나 실제 QGIS 창 변경은 하지 않습니다.
original_dialog = module.QDialog


class TestDialog(original_dialog):
    def exec(self):
        from qgis.PyQt.QtWidgets import QComboBox
        combos = self.findChildren(QComboBox)
        assert len(combos) == 9
        assert all(combo.count() == 3 for combo in combos)
        assert combos[0].currentData() == 'status'
        assert combos[1].currentData() == 'number'
        self.reject()
        return 0


module.QDialog = TestDialog
try:
    plugin.configure()
finally:
    module.QDialog = original_dialog
plugin.unload()
assert not fake.shortcuts
print('PASS: Alt+1~9, 설정 창, 기존 설정 유지, 선택 객체만 변경, 다른 필드 기본값 업데이트 방지, 선택 없음 무수정, 자료형 검증, NULL, 실행 취소, 실패 원복, 자동 저장 없음')
