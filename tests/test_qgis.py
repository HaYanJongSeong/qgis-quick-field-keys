"""Run in QGIS Python. Only a temporary memory layer is modified."""
import importlib.util
from importlib import import_module
import sys
from pathlib import Path
from qgis.core import QgsDefaultValue, QgsFeature, QgsField, QgsVectorLayer, QgsVariantUtils
from qgis.PyQt.QtCore import QMetaType
from qgis.PyQt.QtWidgets import QMainWindow

path = Path(__file__).resolve().parents[1] / 'quick_field_keys'
package_name = '_quick_field_keys_core_test'
for loaded in list(sys.modules):
    if loaded == package_name or loaded.startswith(package_name + '.'):
        del sys.modules[loaded]
spec = importlib.util.spec_from_file_location(package_name, path / '__init__.py', submodule_search_locations=[str(path)])
package = importlib.util.module_from_spec(spec)
sys.modules[package_name] = package
spec.loader.exec_module(package)
module = import_module(package_name + '.plugin')


class MemorySettings:
    data = {}

    def value(self, key, default=None, type=None):
        value = self.data.get(key, default)
        return type(value) if type is not None else value

    def setValue(self, key, value):
        self.data[key] = value


module.QgsSettings = MemorySettings


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
        self.toolbar_actions = []

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
        self.toolbar_actions.append(args[0])

    def removeToolBarIcon(self, *args):
        if args[0] in self.toolbar_actions:
            self.toolbar_actions.remove(args[0])

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
plugin.immediate = True
plugin.presets = {'1': {'field': 'status', 'value': 'done', 'null': False},
                  '2': {'field': 'number', 'value': '12', 'null': False}}
plugin.initGui()
assert set(fake.shortcuts) == {f'Alt+{n}' for n in range(1, 10)}
assert plugin.navigation_action.isCheckable()
assert fake.toolbar_actions == [plugin.navigation_action]
assert not any(action.text() == 'Configure fields and values...' for action in plugin.actions)
assert plugin.dock_widget is None
assert any(action.text() == 'Discard pending shortcuts' for action in plugin.actions)

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
from qgis.PyQt.QtGui import QKeySequence
bindings = dict(plugin.shortcut_map)
bindings['preset_1'] = 'F13'
bindings['preset_2'] = ''
plugin.set_shortcuts(bindings)
assert 'Alt+1' not in fake.shortcuts and 'Alt+2' not in fake.shortcuts
assert fake.shortcuts['F13'] is plugin.preset_actions['1']
assert module.QuickFieldKeys(fake).shortcut_key('preset_1') == 'F13'
invalid = dict(bindings, preset_2='F13')
try:
    plugin.set_shortcuts(invalid)
    raise AssertionError('Duplicate keys must be rejected')
except ValueError:
    pass
assert plugin.shortcut_map == bindings
external = module.QAction('External QGIS action', fake.window)
external.setShortcut(QKeySequence('F14'))
try:
    plugin.set_shortcuts(dict(bindings, preset_1='F14'))
    raise AssertionError('External QGIS key conflicts must be rejected')
except ValueError:
    pass
assert external.shortcut().toString() == 'F14'
assert plugin.shortcut_map == bindings
original_register = fake.registerMainWindowAction


def fail_registration(action, shortcut):
    return False if shortcut == 'F15' else original_register(action, shortcut)


fake.registerMainWindowAction = fail_registration
try:
    plugin.set_shortcuts(dict(bindings, preset_1='F15'))
    raise AssertionError('Registration failure must roll back live keys and leave stored settings unchanged')
except ValueError:
    pass
finally:
    fake.registerMainWindowAction = original_register
assert plugin.shortcut_map == bindings and fake.shortcuts['F13'] is plugin.preset_actions['1']
assert module.QuickFieldKeys(fake).shortcut_key('preset_1') == 'F13'
plugin.unload()
assert not fake.shortcuts
assert not fake.toolbar_actions
print('PASS: Alt+1-9, settings dialog, preset preservation, selected features only, no update defaults, no-selection safety, type validation, NULL, undo, failure rollback, no automatic save')
