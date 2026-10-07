"""Run in QGIS Python. Only a temporary memory layer is modified."""
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


layer = QgsVectorLayer('Point?crs=EPSG:4326', 'Plugin memory test', 'memory')
provider = layer.dataProvider()
provider.addAttributes([QgsField('status', QMetaType.Type.QString),
                        QgsField('number', QMetaType.Type.Int)])
layer.updateFields()
features = []
for n in range(3):
    feature = QgsFeature(layer.fields())
    feature.setAttributes(['original', n])
    features.append(feature)
assert provider.addFeatures(features)[0]
layer.setDefaultValueDefinition(1, QgsDefaultValue('99', True))
ids = [f.id() for f in layer.getFeatures()]
fake = TestIface(layer)
plugin = module.QuickFieldKeys(fake)
plugin.presets = {'1': {'field': 'status', 'value': 'done', 'null': False},
                  '2': {'field': 'number', 'value': '12', 'null': False}}
plugin.initGui()
assert set(fake.shortcuts) == {f'Alt+{n}' for n in range(1, 10)}

plugin.apply('1')
assert not layer.isEditable()
assert fake.bar.messages[-1][0] == 'warning'
layer.selectByIds(ids[:2])
fake.shortcuts['Alt+1'].trigger()
assert layer.isEditable()
assert [layer.getFeature(fid)['status'] for fid in ids] == ['done', 'done', 'original']
assert [layer.getFeature(fid)['number'] for fid in ids] == [0, 1, 2]
assert fake.bar.messages[-1][0] == 'success'
layer.undoStack().undo()
assert all(layer.getFeature(fid)['status'] == 'original' for fid in ids)

plugin.apply('2')
assert [layer.getFeature(fid)['number'] for fid in ids] == [12, 12, 2]
layer.undoStack().undo()
plugin.presets['2']['value'] = 'not a number'
plugin.apply('2')
assert [layer.getFeature(fid)['number'] for fid in ids] == [0, 1, 2]
assert fake.bar.messages[-1][0] == 'warning'
plugin.presets['2']['null'] = True
plugin.apply('2')
assert all(QgsVariantUtils.isNull(layer.getFeature(fid)['number']) for fid in ids[:2])
layer.undoStack().undo()

# Each QAction must apply its own preset, including Alt+3 through Alt+9.
for n in range(3, 10):
    plugin.presets[str(n)] = {'field': 'number', 'value': str(n), 'null': False}
    fake.shortcuts[f'Alt+{n}'].trigger()
    assert [layer.getFeature(fid)['number'] for fid in ids] == [n, n, 2]
    assert fake.bar.messages[-1][0] == 'success'
    layer.undoStack().undo()

# Revert a failed operation without discarding pre-existing edits.
layer.beginEditCommand('Existing user edit')
assert layer.changeAttributeValue(ids[2], 0, 'keep existing edit')
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
assert [layer.getFeature(fid)['status'] for fid in ids] == ['original', 'original', 'keep existing edit']
assert [f['status'] for f in provider.getFeatures()] == ['original'] * 3
assert layer.rollBack()

# Construct the dialog without saving settings or modifying the real QGIS window.
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
print('PASS: Alt+1-9, settings dialog, preset preservation, selected features only, no update defaults, no-selection safety, type validation, NULL, undo, failure rollback, no automatic save')
