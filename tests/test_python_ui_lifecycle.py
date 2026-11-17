"""Isolated real-widget and lifecycle regressions, run through run_python_qgis.py."""
from collections import Counter
from importlib import import_module
from pathlib import Path
import sys

from qgis.core import QgsFeature, QgsProject, QgsVectorLayer
from qgis.gui import QgsMapCanvas
from qgis.PyQt.QtCore import QEvent, Qt
from qgis.PyQt.QtWidgets import QApplication, QCheckBox, QHBoxLayout, QMainWindow

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
core = import_module('quick_field_keys.plugin')
navigation = import_module('quick_field_keys.navigation')
editing = import_module('quick_field_keys.field_editor')


class MemorySettings:
    data = {'quick_field_keys/immediate': False}

    def value(self, key, default=None, type=None):
        value = self.data.get(key, default)
        return type(value) if type is not None else value

    def setValue(self, key, value):
        self.data[key] = value


class Iface:
    def __init__(self, layer):
        self.layer = layer
        self.window = QMainWindow()
        self.canvas = QgsMapCanvas(self.window)
        self.actions = set()
        self.toolbar = set()
        self.messages = []

    def mainWindow(self):
        return self.window

    def activeLayer(self):
        return self.layer

    def setActiveLayer(self, layer):
        self.layer = layer
        return True

    def mapCanvas(self):
        return self.canvas

    def messageBar(self):
        return self

    def pushWarning(self, *args):
        self.messages.append(args)

    def pushSuccess(self, *args):
        self.messages.append(args)

    def registerMainWindowAction(self, action, shortcut):
        self.window.addAction(action)

    def unregisterMainWindowAction(self, action):
        self.window.removeAction(action)

    def addPluginToMenu(self, menu, action):
        self.actions.add(action)

    def removePluginMenu(self, menu, action):
        self.actions.discard(action)

    def addToolBarIcon(self, action):
        self.toolbar.add(action)

    def removeToolBarIcon(self, action):
        self.toolbar.discard(action)

    def addDockWidget(self, area, dock):
        self.window.addDockWidget(area, dock)

    def removeDockWidget(self, dock):
        self.window.removeDockWidget(dock)


for module in (core, navigation, editing):
    module.QgsSettings = MemorySettings
project = QgsProject.instance()
layer = QgsVectorLayer('Point?field=status:string', 'Python lifecycle fixture', 'memory')
feature = QgsFeature(layer.fields())
feature.setAttributes(['original'])
assert layer.dataProvider().addFeatures([feature])[0]
project.addMapLayer(layer)
fid = next(layer.getFeatures()).id()
layer.selectByIds([fid])
iface = Iface(layer)
calls = Counter()


def observed(method):
    def record(self, *args):
        calls[id(self), method.__name__] += 1
        return method(self, *args)
    return record


for name in ('selection_changed', 'refresh_fields', 'refresh_save_state', 'layers_removed'):
    setattr(navigation.QuickFieldNavigator, name, observed(getattr(navigation.QuickFieldNavigator, name)))

for cycle in range(3):
    plugin = core.QuickFieldKeys(iface)
    assert plugin.immediate is True, 'Stored false must not disable immediate startup'
    plugin.initGui()
    plugin.toggle_navigation(True)
    nav = plugin.dock_widget
    standalone = editing.FieldEditor(plugin, layer)
    plugin.field_editor = standalone
    for editor in (nav.inline_editor, standalone):
        assert not editor.findChildren(QCheckBox), 'Field editors must not contain Change/immediate checkboxes'
    toolbar = nav.findChild(QHBoxLayout, 'preset_toolbar')
    actual = [toolbar.itemAt(i).widget() for i in range(toolbar.count())]
    assert actual == [nav.presets_button, nav.columns_button, nav.save_button, nav.undo_button, nav.settings_button]
    assert all(not widget.icon().isNull() for widget in actual[1:])
    layer.removeSelection()
    layer.selectByIds([fid])
    assert calls[id(nav), 'selection_changed'] >= 2
    plugin.unload()
    snapshot = calls.copy()
    layer.removeSelection()
    layer.selectByIds([fid])
    layer.updateFields()
    project.layersWillBeRemoved.emit(['nonexistent-test-layer'])
    assert calls == snapshot, 'Unloaded navigator received stale layer/project signals'
    assert not iface.actions and not iface.toolbar and not iface.window.actions()
    assert plugin.dock_widget is None and plugin.field_editor is None
    QApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
    QApplication.processEvents()
    print(f'PASS: widget defaults, checkbox absence, toolbar order, unload/stale signals cycle {cycle + 1}', flush=True)

# Given pending edits with no inline form, file Save must still apply and commit.
plugin = core.QuickFieldKeys(iface)
plugin.initGui()
plugin.toggle_navigation(True)
nav = plugin.dock_widget
editor = nav.inline_editor
nav.fields_layout.removeWidget(editor)
editor.deleteLater()
nav.inline_editor = None
plugin.pending_layer = layer
plugin.pending_changes = {(fid, 'status'): 'pending without form'}
plugin.pending_targets = [fid]
saved = nav.save_current_fields()
assert saved is True
assert layer.getFeature(fid)['status'] == 'pending without form'
assert not layer.isModified() and not plugin.pending_changes
plugin.unload()
print('PASS: pending file Save with inline_editor=None applies and commits', flush=True)
