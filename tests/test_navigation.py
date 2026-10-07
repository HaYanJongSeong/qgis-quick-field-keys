"""Run in QGIS Python; only an isolated project, canvas and memory layers are used."""
import importlib.util
from pathlib import Path
import sys

from qgis.core import (
    QgsCoordinateReferenceSystem, QgsFeature, QgsGeometry, QgsPointXY,
    QgsProject, QgsVectorLayer,
)
from qgis.gui import QgsExpressionBuilderDialog, QgsExpressionLineEdit, QgsMapCanvas
from qgis.PyQt.QtCore import QTimer
from qgis.PyQt import sip
from qgis.PyQt.QtWidgets import QApplication, QGroupBox, QMainWindow, QPushButton, QToolButton

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
navigation.QgsSettings = MemorySettings
editing.QgsSettings = MemorySettings


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
assert nav.inline_editor is not None and nav.inline_editor.embedded
assert not nav.inline_editor.isWindow(), 'Fields must be embedded at the bottom, not shown in another window'
assert set(nav.inline_editor.rows) == {'status', 'rank'}
assert not any(checkbox.text().startswith('Change ') for checkbox in nav.findChildren(navigation.QCheckBox))
assert not nav.inline_editor.save_button.icon().isNull()
assert isinstance(nav.filter_expression, QgsExpressionLineEdit)
panel_layout = nav.widget().widget().layout()
assert not nav.findChildren(QGroupBox), 'The compact panel must have no section title rows'
assert [panel_layout.itemAt(i).widget().objectName() for i in range(panel_layout.count())
        if panel_layout.itemAt(i).widget() is not None] == [
    'layer_controls', 'filter_controls', 'navigation_controls', 'edit_controls']
assert panel_layout.spacing() == 4
navigation_row = nav.position.parentWidget().layout().itemAt(0).layout()
assert navigation_row.itemAt(0).widget() is nav.position
assert [navigation_row.itemAt(i).widget().objectName() for i in range(1, 5)] == [
    'first_feature', 'previous_feature', 'next_feature', 'last_feature']
assert not nav.back_button.icon().isNull()
assert not nav.flash_button.icon().isNull() and nav.flash_button.isEnabled()
navigation_flashes = []
fake.canvas.flashFeatureIds = lambda target, targets: navigation_flashes.append((target, list(targets)))
selection_before_flash = set(layer.selectedFeatureIds())
extent_before_flash = fake.canvas.extent().toString(8)
fake.layer = other
nav.flash_button.click()
assert navigation_flashes[-1] == (layer, list(layer.selectedFeatureIds()))
assert set(layer.selectedFeatureIds()) == selection_before_flash
assert fake.canvas.extent().toString(8) == extent_before_flash and fake.activeLayer() is other
layer.removeSelection()
assert not nav.flash_button.isEnabled()
flash_count = len(navigation_flashes)
nav.flash_selected()
assert len(navigation_flashes) == flash_count
layer.selectByIds(list(selection_before_flash))
for name in ('first_feature', 'previous_feature', 'next_feature', 'last_feature'):
    button = nav.findChild(QToolButton, name)
    assert button is not None and not button.icon().isNull()
    assert button.toolTip() and button.accessibleName() and not button.text()
assert all(panel_layout.itemAt(i).widget().layout().contentsMargins().top() == 0
           for i in range(4))
assert not hasattr(nav, 'pick_button')
assert not hasattr(nav, 'search_field')
assert not hasattr(nav, 'auto_zoom')
assert not nav.filter_refresh.icon().isNull() and not nav.filter_clear.icon().isNull()
assert nav.filter_refresh.accessibleName() == 'Apply filter and reload'
assert nav.filter_clear.accessibleName() == 'Clear filter'
assert [nav.zoom_mode.itemText(i) for i in range(nav.zoom_mode.count())] == [
    'Fit feature', 'Keep current scale', 'Fixed scale', 'No zoom']
assert not nav.scale.isEnabled()
assert not any(button.text() in ('Choose visible / editable columns...', 'Edit chosen fields...')
               for button in nav.findChildren(QPushButton))
assert nav.columns_button.objectName() == 'column_visibility'
assert not nav.columns_button.icon().isNull()
assert not hasattr(nav, 'shortcuts_enabled'), 'Navigation toggle must be removed'
assert any(button.text() == 'Field value presets...' for button in nav.findChildren(QPushButton))
nav_undo = nav.undo_button
assert nav_undo.shortcut().toString() == 'Alt+Z'
assert not nav_undo.icon().isNull()
assert not nav.settings_button.icon().isNull()
edit_row = nav.immediate.parentWidget().layout().itemAt(1).layout()
assert [edit_row.itemAt(i).widget() for i in range(edit_row.count())] == [
    nav.immediate, nav.save_button, nav.undo_button, nav.settings_button]
assert nav.inline_editor.save_button is nav.save_button
assert not any(button.text() in ('Apply pending', 'Discard pending') for button in nav.findChildren(QPushButton))
for button in nav.findChildren(QPushButton) + nav.findChildren(QToolButton):
    tooltip = button.toolTip()
    assert any('a' <= character.lower() <= 'z' for character in tooltip), button.text()
    assert any('\uac00' <= character <= '\ud7a3' for character in tooltip), button.text()
    assert '\n' in tooltip, button.text()
if globals().get('screenshot_path'):
    nav.resize(460, 980)
    nav.ensurePolished()
    nav.widget().widget().layout().activate()
    assert nav.grab().save(str(screenshot_path))
nav.sort_field.setCurrentIndex(nav.sort_field.findData('rank'))
assert nav.ids == [ids[1], ids[3], ids[0], ids[2]], nav.ids
nav.ascending.setChecked(False)
assert nav.ids == [ids[0], ids[3], ids[1], ids[2]], nav.ids
nav.ascending.setChecked(True)
fake.layer = other
nav.go_to(0)
assert fake.activeLayer() is layer
assert navigation_flashes[-1] == (layer, [ids[1]]), 'Navigation must flash the new selection'
assert layer.selectedFeatureIds() == [ids[1]]
assert '1 / 4' in nav.position.text()
assert 'rank: 1' in nav.position.text()
assert nav.inline_editor.ids == [ids[1]]
assert nav.inline_editor.rows['rank'][0].value() == 1
inline = nav.inline_editor
assert not inline.rows['status'][1].isChecked()
inline.rows['status'][1].click()
assert inline.rows['status'][1].isChecked()
assert not inline.rows['status'][0].widget().isEnabled()
assert 'status' in core.locked_names(layer)
plugin.apply('1')
assert layer.getFeature(ids[1])['status'] == 'original'
assert not plugin.apply_changes(layer, {(ids[1], 'status'): 'blocked', (ids[1], 'rank'): 999}, 'Locked batch')
assert layer.getFeature(ids[1])['rank'] == 1
inline.load_rows()
assert inline.rows['status'][1].isChecked(), 'Column locks must survive form reload'
inline.rows['status'][1].click()
assert 'status' not in core.locked_names(layer)
assert inline.rows['status'][0].widget().isEnabled()
inline.rows['status'][0].setValue('unsaved inline value')
assert inline.has_form_edits()
original_confirm = inline.confirm_discard_form
inline.confirm_discard_form = lambda: False
nav.step(1)
assert nav.index == 0 and inline.has_form_edits(), 'Cancelled navigation must preserve inline input'
assert layer.getFeature(ids[1])['status'] == 'original'
inline.confirm_discard_form = lambda: True
nav.step(1)
assert nav.index == 1 and not inline.has_form_edits()
inline.confirm_discard_form = original_confirm
nav.go_to(0)
assert not any('zoom failed' in str(message) for message in fake.messages.rows)
assert fake.canvas.extent().center().x() > 1000000, 'Zoom must transform WGS84 coordinates to the canvas CRS'
extent_before = fake.canvas.extent().toString(8)
nav.zoom_mode.setCurrentIndex(3)
flash_count = len(navigation_flashes)
nav.go_to(1)
assert len(navigation_flashes) == flash_count + 1, 'No zoom must still flash on navigation'
assert fake.canvas.extent().toString(8) == extent_before
assert not nav.scale.isEnabled()
nav.zoom_mode.setCurrentIndex(2)
assert nav.scale.isEnabled()
nav.zoom_mode.setCurrentIndex(0)
nav.go_to(0)
plugin.apply('1')
assert layer.getFeature(ids[1])['status'] == 'done'
assert nav.save_button.isEnabled(), 'File Save must enable after an immediately applied preset'
inline = nav.inline_editor
inline.rows['status'][0].setValue('inline verified')
assert inline.has_form_edits() and inline.save_button.isEnabled()
inline.apply_form()
assert layer.getFeature(ids[1])['status'] == 'inline verified'
nav.undo_button.click()
assert layer.getFeature(ids[1])['status'] == 'original', 'Undo must restore the whole consecutive feature edit group'
assert [layer.getFeature(fid)['status'] for fid in (ids[0], ids[2], ids[3])] == ['original'] * 3
nav.step(1)
assert layer.selectedFeatureIds() == [ids[3]]
nav.go_to(len(nav.ids) - 1)
nav.step(1)
assert nav.index == 0
assert layer.selectedFeatureIds() == [nav.ids[0]]
nav.go_to(0)
nav.step(-1)
assert nav.index == len(nav.ids) - 1
nav.findChild(QToolButton, 'first_feature').click()
assert nav.index == 0
nav.findChild(QToolButton, 'previous_feature').click()
assert nav.index == len(nav.ids) - 1
nav.findChild(QToolButton, 'first_feature').click()
nav.findChild(QToolButton, 'next_feature').click()
assert nav.index == 1
nav.findChild(QToolButton, 'last_feature').click()
assert nav.index == len(nav.ids) - 1
nav.findChild(QToolButton, 'next_feature').click()
assert nav.index == 0
nav.go_to(len(nav.ids) - 1)
nav.shortcuts[1].activated.emit()
assert nav.index == 0
nav.go_to(0)
nav.shortcuts[1].activated.emit()
assert nav.index == 1
nav.go_to(0)
previous_fid = layer.selectedFeatureIds()[0]
previous_extent = fake.canvas.extent().toString(8)
nav.filter_expression.setExpression(f'$id <> {previous_fid}')
nav.filter_refresh.click()
nav.go_to(0)
assert previous_fid not in nav.ids
assert nav.back_button.shortcut().toString() == 'Alt+Backspace'
assert not nav.back_button.icon().isNull()
nav.back_button.click()
assert layer.selectedFeatureIds() == [previous_fid]
assert nav.filter_expression.expression() == f'$id <> {previous_fid}'
assert previous_fid not in nav.ids
assert fake.canvas.extent().toString(8) == previous_extent
nav.filter_clear.click()
assert nav.filter_expression.expression() == ''
assert previous_fid not in nav.ids, 'Clearing draft text must not re-evaluate the active filter'
nav.filter_refresh.click()
assert set(nav.ids) == set(ids)
assert all(not shortcut.isEnabled() for shortcut in nav.shortcuts)
import qgis.utils
nav.update_shortcuts()
if 'featurenaved' in qgis.utils.plugins:
    assert all(not shortcut.isEnabled() for shortcut in nav.shortcuts)
    assert 'paused' in nav.shortcuts_status.text()

builder_result = {}


def finish_expression_builder():
    for dialog in QApplication.topLevelWidgets():
        if dialog.metaObject().className() == 'QgsExpressionBuilderDialog' and dialog.windowTitle() == 'Build a navigation filter':
            dialog = sip.cast(dialog, QgsExpressionBuilderDialog)
            try:
                builder_result['has_layer_fields'] = dialog.expressionContext().fields().indexFromName('rank') >= 0
                dialog.setExpressionText('"rank" >= 2')
                builder_result['opened'] = True
                dialog.accept()
            except Exception as error:
                builder_result['error'] = str(error)
                dialog.reject()
            return


QTimer.singleShot(0, finish_expression_builder)
nav.filter_expression.findChild(QToolButton).click()
assert builder_result.get('opened'), builder_result
assert builder_result.get('has_layer_fields'), builder_result
assert nav.filter_expression.expression() == '"rank" >= 2'
nav.reload_features()
assert nav.ids == [ids[3], ids[0]]
previous = list(nav.ids)
nav.filter_expression.setExpression('"rank" = ')
nav.reload_features()
assert nav.ids == previous
nav.clear_filter()
nav.filter_refresh.click()
layer.selectByIds([ids[0], ids[3]])
nav.use_current_selection()
assert nav.selected_only.isChecked()
assert '2 captured' in nav.scope_status.text()
assert nav.ids == [ids[3], ids[0]]
nav.go_to(0)
assert nav.ids == [ids[3], ids[0]], 'Navigation must not collapse the captured selection scope'
nav.step(1)
assert layer.selectedFeatureIds() == [ids[0]]
nav.selected_only.setChecked(False)

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
editor_undo = next(button for button in editor.findChildren(QPushButton) if button.text() == 'Undo (Alt+Z)')
assert editor_undo.shortcut().toString() == 'Alt+Z'
for button in editor.findChildren(QPushButton):
    tooltip = button.toolTip()
    assert any('a' <= character.lower() <= 'z' for character in tooltip), button.text()
    assert any('\uac00' <= character <= '\ud7a3' for character in tooltip), button.text()
    assert '\n' in tooltip, button.text()
original_dialog = editing.QDialog


class ChooseOnlyRank(original_dialog):
    def exec(self):
        from qgis.PyQt.QtCore import Qt
        from qgis.PyQt.QtWidgets import QListWidget
        items = self.findChild(QListWidget)
        assert not self.parentWidget().isVisible(), 'Do not show the editor behind the navigator column chooser'
        select = next(button for button in self.findChildren(QPushButton) if button.text() == 'Select all')
        deselect = next(button for button in self.findChildren(QPushButton) if button.text() == 'Deselect all')
        select.click()
        assert all(items.item(i).checkState() == Qt.CheckState.Checked for i in range(items.count()))
        deselect.click()
        assert all(items.item(i).checkState() == Qt.CheckState.Unchecked for i in range(items.count()))
        select.click()
        if globals().get('chooser_screenshot_path'):
            self.resize(380, 300)
            self.ensurePolished()
            self.layout().activate()
            assert self.grab().save(str(chooser_screenshot_path))
        for i in range(items.count()):
            items.item(i).setCheckState(Qt.CheckState.Checked if items.item(i).text() == 'rank' else Qt.CheckState.Unchecked)
        return int(original_dialog.DialogCode.Accepted)


editing.QDialog = ChooseOnlyRank
try:
    fake.layer = other
    nav.columns_button.click()
    assert nav.inline_editor.layer is layer
    assert not nav.inline_editor.isWindow()
    assert set(nav.inline_editor.rows) == {'rank'}
    assert fake.activeLayer() is other, 'Choosing visible fields must not alter the active layer'
    editor.choose_fields()
    fake.layer = layer
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
wrapper, lock = editor.rows['status']
wrapper.setValue('form value')
assert editor.has_form_edits()
assert [layer.getFeature(fid)['status'] for fid in ids] == before
editor.apply_form()
assert [layer.getFeature(fid)['status'] for fid in ids[:2]] == ['form value', 'form value']
assert [layer.getFeature(fid)['rank'] for fid in ids] == rank_before
assert not editor.has_form_edits()
editor.undo()
assert [layer.getFeature(fid)['status'] for fid in ids] == before
wrapper, lock = editor.rows['status']
wrapper.setValue('unapplied input')
assert editor.has_form_edits()
editor.undo()
assert not editor.has_form_edits()
assert [layer.getFeature(fid)['status'] for fid in ids] == before
assert [feature['status'] for feature in layer.dataProvider().getFeatures()] == ['original'] * 4
editor.close()
plugin.field_editor = None
editor.deleteLater()
nav.sort_field.setCurrentIndex(nav.sort_field.findData('rank'))
layer.beginEditCommand('Delete field in isolated layer')
assert layer.deleteAttribute(layer.fields().indexFromName('rank'))
layer.endEditCommand()
assert nav.sort_field.currentData() == ''
nav.update_position()
layer.undoStack().undo()
assert nav.sort_field.findData('rank') >= 0

doomed = QgsVectorLayer('Point?field=status:string', 'Removed staged target', 'memory')
feature = QgsFeature(doomed.fields())
feature.setAttributes(['original'])
assert doomed.dataProvider().addFeatures([feature])[0]
project.addMapLayer(doomed)
doomed.selectAll()
fake.layer = doomed
nav.layer_combo.setLayer(doomed)
plugin.apply('1')
assert plugin.pending_layer is doomed
project.removeMapLayer(doomed.id())
assert not plugin.apply_pending(), 'A removed target must not be written'
assert plugin.pending_changes, 'Failed apply must retain pending values for explicit discard'
plugin.discard_pending()
fake.layer = layer
nav.layer_combo.setLayer(layer)
layer.selectByIds(ids[:2])
plugin.apply('1')
assert plugin.pending_layer is layer, 'Global discard must allow staging another layer after removal'
plugin.discard_pending()
nav.shutdown()
assert all(not shortcut.isEnabled() for shortcut in nav.shortcuts)
nav.filter_expression.setExpression('"rank" >= 2')
nav.reload_features()
nav.go_to(1)
saved_fid = nav.ids[nav.index]
nav.save_session()
restored = navigation.QuickFieldNavigator(plugin, project)
assert restored.layer is layer
assert restored.filter_expression.expression() == '"rank" >= 2'
assert restored.ids[restored.index] == saved_fid
assert restored.sort_field.currentData() == nav.sort_field.currentData()
restored.restore_layout()
restored.save_layout()
assert restored.read_state('quick_field_keys/navigator/layout')['geometry']
restored.restore_on_open()
assert layer.selectedFeatureIds() == [saved_fid]
restored.shutdown()
restored.deleteLater()
plugin.dock_widget = None
nav.deleteLater()
assert layer.rollBack()

# Feature-aware Undo must restore the whole plugin edit group without touching other tools.
polygon = QgsVectorLayer('Polygon?crs=EPSG:4326&field=status:string&field=rank:integer', 'Feature Undo test', 'memory')
polygon_features = []
for x in (10, 30):
    feature = QgsFeature(polygon.fields())
    feature.setAttributes(['original', 1])
    feature.setGeometry(QgsGeometry.fromWkt(f'POLYGON(({x} 10,{x+1} 10,{x+1} 11,{x} 11,{x} 10))'))
    polygon_features.append(feature)
assert polygon.dataProvider().addFeatures(polygon_features)[0]
project.addMapLayer(polygon)
polygon_ids = [feature.id() for feature in polygon.getFeatures()]
plugin.applied_history.clear()
fake.layer = polygon
feature_nav = navigation.QuickFieldNavigator(plugin, project)
plugin.dock_widget = feature_nav
feature_nav.layer_combo.setLayer(polygon)
plugin.immediate = True
flashes = []
original_flash = fake.canvas.flashFeatureIds
fake.canvas.flashFeatureIds = lambda target, targets: flashes.append((target, list(targets)))
first, second = polygon_ids
feature_nav.filter_expression.setExpression('"status" = \'original\'')
feature_nav.filter_refresh.click()
frozen_ids = list(feature_nav.ids)
assert plugin.apply_changes(polygon, {(first, 'status'): 'edited'}, 'First field')
assert feature_nav.ids == frozen_ids, 'Attribute editing must not refresh filter membership'
feature_nav.filter_expression.setExpression(f'$id = {second}')
assert plugin.apply_changes(polygon, {(first, 'rank'): 99}, 'Second field')
assert plugin.apply_changes(polygon, {(first, 'status'): 'edited again'}, 'Repeated field')
assert feature_nav.ids == frozen_ids and first in feature_nav.ids
assert feature_nav.applied_filter == '"status" = \'original\'', 'Draft expressions must not apply during edits'
feature_nav.ascending.setChecked(False)
feature_nav.ascending.setChecked(True)
assert set(feature_nav.ids) == set(frozen_ids), 'Sorting must not evaluate the draft expression'
assert len(plugin.applied_history) == 1
if globals().get('undo_before_screenshot'):
    feature_nav.go_to(feature_nav.ids.index(first))
    feature_nav.resize(460, 430)
    feature_nav.ensurePolished()
    feature_nav.widget().widget().layout().activate()
    QApplication.processEvents()
    assert feature_nav.grab().save(str(undo_before_screenshot))
feature_nav.filter_expression.setExpression(f'$id = {second}')
feature_nav.filter_refresh.click()
assert feature_nav.ids == [second], 'Only the refresh button applies the new expression'
feature_nav.go_to(0)
feature_nav.zoom_mode.setCurrentIndex(3)
feature_nav.undo_button.click()
assert polygon.getFeature(first)['status'] == 'original'
assert polygon.getFeature(first)['rank'] == 1
assert polygon.getFeature(second)['status'] == 'original'
assert polygon.selectedFeatureIds() == [first]
assert feature_nav.filter_expression.expression() == f'$id = {second}'
assert first not in feature_nav.ids, 'Undo focus must work even outside the filter'
assert feature_nav.index == -1, 'The position must not claim a different filtered feature is selected'
assert feature_nav.inline_editor.ids == [first]
assert flashes[-1] == (polygon, [first])
assert fake.canvas.extent().center().x() < 2000000, 'Undo must focus the first polygon even in No zoom mode'
if globals().get('undo_after_screenshot'):
    feature_nav.widget().widget().layout().activate()
    QApplication.processEvents()
    assert feature_nav.grab().save(str(undo_after_screenshot))

# Changes to an unrelated field made outside the plugin must survive.
assert plugin.apply_changes(polygon, {(first, 'status'): 'plugin change'}, 'Plugin edit')
polygon.beginEditCommand('Other tool: different field')
assert polygon.changeAttributeValue(first, polygon.fields().indexFromName('rank'), 777)
polygon.endEditCommand()
assert plugin.undo_edit(polygon)
assert polygon.getFeature(first)['status'] == 'original'
assert polygon.getFeature(first)['rank'] == 777

# A conflicting edit to the same field must block the whole restore.
assert plugin.apply_changes(polygon, {(first, 'status'): 'plugin value'}, 'Plugin edit')
polygon.beginEditCommand('Other tool: same field')
assert polygon.changeAttributeValue(first, polygon.fields().indexFromName('status'), 'external value')
polygon.endEditCommand()
flash_count = len(flashes)
assert not plugin.undo_edit(polygon)
assert polygon.getFeature(first)['status'] == 'external value'
assert len(flashes) == flash_count
polygon.undoStack().undo()
assert not plugin.applied_history, 'External layer Undo must invalidate stale feature history'
assert polygon.rollBack()

# A failed multi-field restore must be atomic and retain its retryable history.
assert plugin.apply_changes(polygon, {(first, 'status'): 'retry', (first, 'rank'): 42}, 'Two fields')
original_polygon_change = polygon.changeAttributeValue
restore_calls = []


def fail_second_restore(*args, **kwargs):
    restore_calls.append(args)
    return False if len(restore_calls) == 2 else original_polygon_change(*args, **kwargs)


polygon.changeAttributeValue = fail_second_restore
assert not plugin.undo_edit(polygon)
polygon.changeAttributeValue = original_polygon_change
assert polygon.getFeature(first)['status'] == 'retry' and polygon.getFeature(first)['rank'] == 42
assert len(plugin.applied_history) == 1
assert plugin.undo_edit(polygon)
assert polygon.getFeature(first)['status'] == 'original' and polygon.getFeature(first)['rank'] == 1
assert plugin.apply_changes(polygon, {(first, 'status'): None, (second, 'status'): None}, 'NULL multi-selection')
assert plugin.undo_edit(polygon)
assert all(polygon.getFeature(fid)['status'] == 'original' for fid in polygon_ids)
assert set(polygon.selectedFeatureIds()) == set(polygon_ids)
assert flashes[-1] == (polygon, polygon_ids)

# Locks apply to all plugin writes, including grouped Undo and staged shortcut application.
assert plugin.apply_changes(polygon, {(first, 'status'): 'before lock'}, 'Locked Undo test')
feature_nav.inline_editor.rows['status'][1].click()
assert not plugin.undo_edit(polygon)
assert polygon.getFeature(first)['status'] == 'before lock'
assert len(plugin.applied_history) == 1
plugin.immediate = False
plugin.apply('1')
assert not plugin.pending_changes, 'Locked shortcut fields must not be staged'
feature_nav.inline_editor.rows['status'][1].click()
assert plugin.undo_edit(polygon)
assert polygon.getFeature(first)['status'] == 'original'
polygon.selectByIds([first])
plugin.apply('1')
assert plugin.pending_changes
feature_nav.inline_editor.rows['status'][1].click()
assert not plugin.apply_pending()
assert plugin.pending_changes and polygon.getFeature(first)['status'] == 'original'
feature_nav.inline_editor.rows['status'][1].click()
assert plugin.apply_pending()
assert plugin.undo_edit(polygon)
assert polygon.getFeature(first)['status'] == 'original'
plugin.immediate = True
assert plugin.apply_changes(polygon, {(first, 'status'): 'saved'}, 'Before isolated memory commit')
assert polygon.commitChanges()
assert not plugin.applied_history and not plugin.undo_edit(polygon)
assert polygon.getFeature(first)['status'] == 'saved', 'Saved edits must not be restored by in-session Undo'

# Presets keep the designated target even when another layer is active and the dock is hidden.
polygon.selectByIds([first])
layer.selectByIds([ids[0]])
fake.layer = layer
other_before = layer.getFeature(ids[0])['status']
plugin.immediate = True
plugin.apply('1')
assert polygon.getFeature(first)['status'] == plugin.presets['1']['value']
assert layer.getFeature(ids[0])['status'] == other_before and not layer.isEditable()
assert fake.activeLayer() is layer, 'Applying a preset must not activate or edit the unrelated active layer'
assert plugin.undo_edit(polygon)
assert polygon.getFeature(first)['status'] == 'saved'
fake.layer = layer
plugin.immediate = False
plugin.apply('1')
assert plugin.pending_layer is polygon
assert all(fid == first for fid, name in plugin.pending_changes)
plugin.discard_pending()
plugin.immediate = True

# The settings dialog assigns live bindings, persists them and leaves other QGIS keys alone.
shortcut_config = core.shortcut_config
original_shortcut_dialog = shortcut_config.QDialog


class ShortcutSettingsDialog(original_shortcut_dialog):
    def exec(self):
        from qgis.PyQt.QtGui import QKeySequence
        from qgis.PyQt.QtWidgets import QDialogButtonBox, QKeySequenceEdit
        edits = {edit.objectName(): edit for edit in self.findChildren(QKeySequenceEdit)}
        assert set(edits) == set(shortcut_config.ACTIONS)
        clear = self.findChild(QToolButton, 'clear_preset_9')
        assert clear is not None and not clear.icon().isNull()
        clear.click()
        assert edits['preset_9'].keySequence().isEmpty()
        assert plugin.shortcut_key('preset_9') == 'Alt+9', 'Clearing the dialog input must not apply until Save'
        for name, key in {'undo': 'Ctrl+Alt+U', 'next': 'Ctrl+Alt+N', 'refresh': 'Ctrl+Alt+R',
                          'save_feature': 'Ctrl+Alt+F10', 'lock_field': 'Ctrl+Alt+L', 'flash': 'Ctrl+Alt+F9'}.items():
            edits[name].setKeySequence(QKeySequence(key))
        if globals().get('shortcut_screenshot_path'):
            self.ensurePolished()
            self.layout().activate()
            assert self.grab().save(str(shortcut_screenshot_path))
        self.findChild(QDialogButtonBox).button(QDialogButtonBox.StandardButton.Save).click()
        assert self.result() == int(original_shortcut_dialog.DialogCode.Accepted)
        return self.result()


shortcut_config.QDialog = ShortcutSettingsDialog
try:
    feature_nav.settings_button.click()
finally:
    shortcut_config.QDialog = original_shortcut_dialog
assert feature_nav.undo_button.shortcut().toString() == 'Ctrl+Alt+U'
assert feature_nav.shortcuts[1].key().toString() == 'Ctrl+Alt+N'
assert feature_nav.filter_refresh.shortcut().toString() == 'Ctrl+Alt+R'
assert feature_nav.inline_editor.save_button.shortcut().toString() == 'Ctrl+Alt+F10'
assert feature_nav.flash_button.shortcut().toString() == 'Ctrl+Alt+F9'
assert 'Ctrl+Alt+U' in feature_nav.undo_button.toolTip()
assert plugin.shortcut_key('preset_9') == ''
assert core.QuickFieldKeys(fake).shortcut_key('undo') == 'Ctrl+Alt+U'
old_bindings = dict(plugin.shortcut_map)
for bad in (dict(old_bindings, next=old_bindings['undo']), dict(old_bindings, undo='A')):
    try:
        plugin.set_shortcuts(bad)
        raise AssertionError('Duplicate or bare typing keys must be rejected')
    except ValueError:
        pass
    assert plugin.shortcut_map == old_bindings
plugin.set_shortcuts(dict(old_bindings, refresh=''))
assert feature_nav.filter_refresh.shortcut().isEmpty()
plugin.set_shortcuts(old_bindings)
if globals().get('final_panel_screenshot'):
    feature_nav.clear_filter()
    feature_nav.filter_refresh.click()
    feature_nav.go_to(feature_nav.ids.index(first))
    feature_nav.inline_editor.rows['rank'][1].click()
    feature_nav.inline_editor.rows['status'][0].setValue('editable input')
    feature_nav.refresh_quick_status()
    feature_nav.resize(460, 410)
    feature_nav.ensurePolished()
    feature_nav.widget().widget().layout().activate()
    QApplication.processEvents()
    assert feature_nav.grab().save(str(final_panel_screenshot))
    feature_nav.inline_editor.load_rows()
fake.canvas.flashFeatureIds = original_flash
# File Save commits the designated layer, not the active QGIS layer.
feature_nav.inline_editor.load_rows()
if feature_nav.inline_editor.rows['rank'][1].isChecked():
    feature_nav.inline_editor.rows['rank'][1].click()
polygon.selectByIds([first])
fake.layer = layer
assert plugin.apply_changes(polygon, {(first, 'status'): 'file saved'}, 'Save immediate preset')
assert feature_nav.save_button.isEnabled()
feature_nav.save_button.click()
assert next(f for f in polygon.dataProvider().getFeatures() if f.id() == first)['status'] == 'file saved'
assert not polygon.isModified() and polygon.isEditable()
assert not feature_nav.save_button.isEnabled()
assert not plugin.applied_history and not plugin.undo_edit(polygon)
assert fake.activeLayer() is layer and not layer.isEditable()

# Stage and type into the form: Save applies both, then commits all layer edits.
plugin.immediate = False
plugin.apply('1')
assert feature_nav.save_button.isEnabled()
feature_nav.inline_editor.rows['rank'][0].setValue(123)
assert feature_nav.save_current_fields()
stored = next(f for f in polygon.dataProvider().getFeatures() if f.id() == first)
assert stored['status'] == plugin.presets['1']['value'] and stored['rank'] == 123
assert not plugin.pending_changes and not polygon.isModified()
plugin.immediate = True

# External edits also enable Save; commit failure retains the edit buffer and history.
assert polygon.changeAttributeValue(first, polygon.fields().indexFromName('status'), 'external edit')
assert feature_nav.save_button.isEnabled()
original_commit = polygon.commitChanges
polygon.commitChanges = lambda stopEditing=True: False
assert not feature_nav.save_current_fields()
assert polygon.isModified() and feature_nav.save_button.isEnabled()
assert polygon.getFeature(first)['status'] == 'external edit'
polygon.commitChanges = original_commit
assert feature_nav.save_current_fields()
assert not feature_nav.save_button.isEnabled()

# Locked drafts cannot be applied or committed by Save.
feature_nav.inline_editor.rows['status'][1].click()
plugin.immediate = False
plugin.apply('1')
assert not plugin.pending_changes and not feature_nav.save_button.isEnabled()
feature_nav.inline_editor.rows['status'][1].click()
plugin.immediate = True
feature_nav.shutdown()
feature_nav.deleteLater()
plugin.dock_widget = None
project.clear()
print('PASS: requested panel order, no Find/Pick controls, direct column chooser, one-icon integration, native expression builder, automatic navigation, Previous wrap, filter-independent view history, chosen-field multi-edit, captured targets, Undo, remembered state, schema change, removed-target recovery, no automatic file save')
print('PASS: grouped feature Undo, repeated fields, filter-independent selection/focus/flash, No zoom override, foreign-field preservation, conflict blocking, external-Undo invalidation, atomic failure/retry, commit boundary')
print('PASS: filter membership frozen during edits, draft expressions and sorting; clear is draft-only; explicit refresh applies the filter')
print('PASS: no Change checkboxes, automatic modified-field tracking, feature-save icon, persistent right-side locks, shortcut/staging/Apply/Undo lock guards, atomic locked batches')
print('PASS: settings icon, native key-sequence dialog, live remapping, reload persistence, unassigned keys, duplicate/bare-key/external-conflict guards')
print('PASS: designated target independent of active QGIS layer or dock visibility, no unrelated-layer writes, pinned staged targets')
print('PASS: explicit file Save, immediate/staged/form/external edits enable Save, designated-layer-only commit, keep editing, saved Undo boundary, failed commit retains edits, locks')
print('PASS: bulb button flashes designated-layer selection without changing selection/view/active layer; automatic navigation flash including No zoom')
