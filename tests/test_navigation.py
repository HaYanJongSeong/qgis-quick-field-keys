"""Run in QGIS Python; only an isolated project, canvas and memory layers are used."""
import importlib.util
from pathlib import Path
import sys

from qgis.core import (
    QgsCoordinateReferenceSystem, QgsFeature, QgsGeometry, QgsPointXY,
    QgsProject, QgsVectorLayer,
)
from qgis.gui import QgsMapCanvas
from qgis.PyQt.QtWidgets import QMainWindow

root = Path(__file__).resolve().parents[1]
package_name = '_quick_field_keys_isolated_test'
for loaded in list(sys.modules):
    if loaded == package_name or loaded.startswith(package_name + '.'):
        del sys.modules[loaded]
spec = importlib.util.spec_from_file_location(
    package_name, root / 'quick_field_keys' / '__init__.py',
    submodule_search_locations=[str(root / 'quick_field_keys')])
package = importlib.util.module_from_spec(spec)
sys.modules[package_name] = package
spec.loader.exec_module(package)
from importlib import import_module
core = import_module(package_name + '.plugin')
navigation = import_module(package_name + '.navigation')
editing = import_module(package_name + '.field_editor')


class MemorySettings:
    data = {}

    def value(self, key, default=None, type=None):
        result = self.data.get(key, default)
        return type(result) if type is not None else result

    def setValue(self, key, value):
        self.data[key] = value


core.QgsSettings = MemorySettings
editing.QgsSettings = MemorySettings
navigation.QgsSettings = MemorySettings


class Messages:
    def __init__(self):
        self.rows = []

    def pushWarning(self, *args):
        self.rows.append(('warning', args))

    def pushSuccess(self, *args):
        self.rows.append(('success', args))


class IsolatedIface:
    def __init__(self, layer):
        self.layer = layer
        self.window = QMainWindow()
        self.canvas = QgsMapCanvas(self.window)
        self.canvas.setDestinationCrs(QgsCoordinateReferenceSystem('EPSG:3857'))
        self.messages = Messages()

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
        return self.messages


layer = QgsVectorLayer('Point?crs=EPSG:4326&field=status:string&field=rank:integer', 'Isolated navigation', 'memory')
features = []
for i, rank in enumerate((3, 1, None, 2)):
    feature = QgsFeature(layer.fields())
    feature.setAttributes(['original', rank])
    feature.setGeometry(QgsGeometry.fromPointXY(QgsPointXY(10 + i, 10 + i)))
    features.append(feature)
assert layer.dataProvider().addFeatures(features)[0]
ids = [feature.id() for feature in layer.getFeatures()]
project = QgsProject()
project.addMapLayer(layer)
other = QgsVectorLayer('Point?crs=EPSG:4326&field=status:string', 'Other memory layer', 'memory')
project.addMapLayer(other)
fake = IsolatedIface(layer)
plugin = core.QuickFieldKeys(fake)
plugin.immediate = True
plugin.presets = {'1': {'field': 'status', 'value': 'done', 'null': False}}
layer.selectByIds(ids[:2])
nav = navigation.QuickFieldNavigator(plugin, project)
plugin.dock_widget = nav
assert set(layer.selectedFeatureIds()) == set(ids[:2]), 'Opening navigator must preserve multiselection'
nav.sort_field.setCurrentIndex(nav.sort_field.findData('rank'))
assert nav.ids == [ids[1], ids[3], ids[0], ids[2]], nav.ids
nav.ascending.setChecked(False)
assert nav.ids == [ids[0], ids[3], ids[1], ids[2]], nav.ids
nav.ascending.setChecked(True)
fake.layer = other
nav.go_to(0)
assert fake.activeLayer() is layer
assert layer.selectedFeatureIds() == [ids[1]]
assert '1 / 4' in nav.position.text()
assert 'rank: 1' in nav.position.text()
assert not any('zoom failed' in str(message) for message in fake.messages.rows)
assert fake.canvas.extent().center().x() > 1000000, 'Zoom must transform WGS84 coordinates to the canvas CRS'
plugin.apply('1')
assert layer.getFeature(ids[1])['status'] == 'done'
assert [layer.getFeature(fid)['status'] for fid in (ids[0], ids[2], ids[3])] == ['original'] * 3
nav.step(1)
assert layer.selectedFeatureIds() == [ids[3]]
nav.go_to(len(nav.ids) - 1)
nav.step(1)
assert nav.index == len(nav.ids) - 1
nav.go_to(0)
nav.step(-1)
assert nav.index == 0
nav.shortcuts[1].activated.emit()
assert nav.index == 1
assert all(not shortcut.isEnabled() for shortcut in nav.shortcuts)
import qgis.utils
nav.shortcuts_enabled.setChecked(True)
if 'featurenaved' in qgis.utils.plugins:
    assert not nav.shortcuts_enabled.isChecked(), 'The installed FeatureNavEd must not share navigation keys'
nav.shortcuts_enabled.setChecked(False)

nav.filter_expression.setText('"rank" >= 2')
nav.reload_features()
assert nav.ids == [ids[3], ids[0]]
previous = list(nav.ids)
nav.filter_expression.setText('"rank" = ')
nav.reload_features()
assert nav.ids == previous
nav.filter_expression.clear()
nav.reload_features()
layer.selectByIds([ids[0], ids[3]])
nav.selected_only.setChecked(True)
assert nav.ids == [ids[3], ids[0]]
nav.go_to(0)
assert nav.ids == [ids[3], ids[0]], 'Navigation must not collapse the captured selection scope'
nav.step(1)
assert layer.selectedFeatureIds() == [ids[0]]
nav.selected_only.setChecked(False)
nav.search_field.setCurrentIndex(nav.search_field.findData('rank'))
nav.search_value.setText('2')
nav.find_next()
assert layer.selectedFeatureIds() == [ids[3]]
nav.picked(layer.getFeature(ids[0]))
assert layer.selectedFeatureIds() == [ids[0]]
nav.toggle_pick(True)
assert fake.canvas.mapTool() is nav.pick_tool
nav.stop_pick()
assert nav.pick_tool is None

# Staged shortcuts must keep their original targets even after selection changes.
plugin.set_immediate(False)
layer.selectByIds(ids[:2])
before = [layer.getFeature(fid)['status'] for fid in ids]
plugin.presets['1']['value'] = 'staged'
plugin.apply('1')
assert [layer.getFeature(fid)['status'] for fid in ids] == before
assert len(plugin.pending_changes) == 2
layer.selectByIds([ids[3]])
assert plugin.apply_pending()
assert [layer.getFeature(fid)['status'] for fid in ids[:2]] == ['staged', 'staged']
assert layer.getFeature(ids[3])['status'] == before[3]
plugin.undo_edit(layer)
assert [layer.getFeature(fid)['status'] for fid in ids] == before
layer.selectByIds(ids[:2])
plugin.apply('1')
plugin.undo_edit(layer)
assert not plugin.pending_changes
assert [layer.getFeature(fid)['status'] for fid in ids] == before
plugin.apply('1')
plugin.pending_changes[(ids[0], 'missing_field')] = 'invalid'
assert not plugin.apply_pending()
assert [layer.getFeature(fid)['status'] for fid in ids] == before
assert plugin.pending_changes
plugin.discard_pending()

# Only the explicitly chosen field is visible and writable in the dedicated form.
MemorySettings.data[f'quick_field_keys/visible_fields/{layer.id()}'] = '["status"]'
layer.selectByIds(ids[:2])
editor = editing.FieldEditor(plugin, layer)
plugin.field_editor = editor
assert set(editor.rows) == {'status'}
assert not editor.has_form_edits()
original_dialog = editing.QDialog


class ChooseOnlyRank(original_dialog):
    def exec(self):
        from qgis.PyQt.QtCore import Qt
        from qgis.PyQt.QtWidgets import QListWidget
        items = self.findChild(QListWidget)
        for i in range(items.count()):
            items.item(i).setCheckState(Qt.CheckState.Checked if items.item(i).text() == 'rank' else Qt.CheckState.Unchecked)
        return int(original_dialog.DialogCode.Accepted)


editing.QDialog = ChooseOnlyRank
try:
    editor.choose_fields()
finally:
    editing.QDialog = original_dialog
assert set(editor.rows) == {'rank'}
assert MemorySettings.data[editor.setting] == '["rank"]'
editor.visible_names = ['status']
editor.load_rows()
layer.selectByIds(ids[:2])
plugin.apply('1')
assert 'staged' in editor.preview.toPlainText()
editor.discard_pending()
rank_before = [layer.getFeature(fid)['rank'] for fid in ids]
wrapper, checkbox = editor.rows['status']
wrapper.setValue('form value')
checkbox.setChecked(True)
assert [layer.getFeature(fid)['status'] for fid in ids] == before
editor.apply_form()
assert [layer.getFeature(fid)['status'] for fid in ids[:2]] == ['form value', 'form value']
assert [layer.getFeature(fid)['rank'] for fid in ids] == rank_before
assert not editor.has_form_edits()
editor.undo()
assert [layer.getFeature(fid)['status'] for fid in ids] == before
wrapper, checkbox = editor.rows['status']
wrapper.setValue('unapplied input')
checkbox.setChecked(True)
editor.undo()
assert not editor.has_form_edits()
assert [layer.getFeature(fid)['status'] for fid in ids] == before
assert [feature['status'] for feature in layer.dataProvider().getFeatures()] == ['original'] * 4
editor.close()
plugin.field_editor = None
editor.deleteLater()
nav.sort_field.setCurrentIndex(nav.sort_field.findData('rank'))
nav.search_field.setCurrentIndex(nav.search_field.findData('rank'))
layer.beginEditCommand('Delete field in isolated layer')
assert layer.deleteAttribute(layer.fields().indexFromName('rank'))
layer.endEditCommand()
assert nav.sort_field.currentData() == ''
assert nav.search_field.findData('rank') == -1
nav.update_position()
nav.find_next()
layer.undoStack().undo()
assert nav.sort_field.findData('rank') >= 0

doomed = QgsVectorLayer('Point?field=status:string', 'Removed staged target', 'memory')
feature = QgsFeature(doomed.fields())
feature.setAttributes(['original'])
assert doomed.dataProvider().addFeatures([feature])[0]
project.addMapLayer(doomed)
doomed.selectAll()
fake.layer = doomed
plugin.apply('1')
assert plugin.pending_layer is doomed
project.removeMapLayer(doomed.id())
assert not plugin.apply_pending(), 'A removed target must not be written'
assert plugin.pending_changes, 'Failed apply must retain pending values for explicit discard'
plugin.discard_pending()
fake.layer = layer
layer.selectByIds(ids[:2])
plugin.apply('1')
assert plugin.pending_layer is layer, 'Global discard must allow staging another layer after removal'
plugin.discard_pending()
nav.shutdown()
assert all(not shortcut.isEnabled() for shortcut in nav.shortcuts)
plugin.dock_widget = None
nav.deleteLater()
assert layer.rollBack()
project.clear()
print('PASS: sort/NULL order, bounds, selection and active-layer alignment, CRS zoom, filter, captured selection, search, pick lifecycle, chosen-field multi-edit, stage/manual apply, captured targets, undo, invalid-stage retention, schema change, removed-target recovery, no file save')
