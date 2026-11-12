"""Run in QGIS Python; only isolated settings, a project and memory layers are used."""
import importlib.util
from importlib import import_module
from pathlib import Path
import sys
import unittest

from qgis.core import (
    QgsEditorWidgetSetup, QgsFeature, QgsFeatureRequest, QgsField, QgsGeometry,
    QgsPointXY, QgsProject, QgsVectorLayer,
)
from qgis.gui import QgsMapCanvas
from qgis.PyQt.QtCore import QMetaType
from qgis.PyQt.QtWidgets import QApplication, QMainWindow

root = Path(__file__).resolve().parents[1]
package_name = '_quick_field_keys_optimization_test'
for loaded in list(sys.modules):
    if loaded == package_name or loaded.startswith(package_name + '.'):
        del sys.modules[loaded]
spec = importlib.util.spec_from_file_location(
    package_name, root / 'quick_field_keys' / '__init__.py',
    submodule_search_locations=[str(root / 'quick_field_keys')])
package = importlib.util.module_from_spec(spec)
sys.modules[package_name] = package
spec.loader.exec_module(package)
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
        self.canvas.setDestinationCrs(layer.crs())
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


class OptimizationTests(unittest.TestCase):
    def setUp(self):
        MemorySettings.data.clear()
        self.layer = QgsVectorLayer(
            'Point?crs=EPSG:4326&field=status:string&field=rank:integer&field=note:string&field=tag:string',
            'Optimization memory test', 'memory')
        features = []
        xs = (40, 10, 50, 20, 30)
        for x, rank in zip(xs, (3, 1, None, 1, 2)):
            feature = QgsFeature(self.layer.fields())
            feature.setAttributes(['original', rank, 'same note', 'same tag'])
            feature.setGeometry(QgsGeometry.fromPointXY(QgsPointXY(x, 10)))
            features.append(feature)
        self.assertTrue(self.layer.dataProvider().addFeatures(features)[0])
        self.ids = [feature.id() for feature in self.layer.getFeatures()]
        self.x_by_id = dict(zip(self.ids, xs))
        self.project = QgsProject()
        self.project.addMapLayer(self.layer)
        self.iface = IsolatedIface(self.layer)
        self.plugin = core.QuickFieldKeys(self.iface)
        self.nav = None
        self.editor = None

    def tearDown(self):
        if self.editor is not None:
            self.editor.changed_fields.clear()
            self.editor.close()
            self.editor.deleteLater()
        if self.nav is not None:
            self.nav.shutdown()
            self.plugin.dock_widget = None
            self.nav.deleteLater()
        self.plugin.unload()
        if self.layer.isEditable():
            self.layer.rollBack()
        self.project.clear()
        self.iface.window.close()
        self.iface.window.deleteLater()
        QApplication.processEvents()

    def test_repeated_field_merge_avoids_extra_reads_for_zero_and_null(self):
        fid = self.ids[0]
        initial = self.layer.getFeature(fid)['rank']
        original_get = self.layer.getFeature
        reads = []
        counts = []

        def counted_get(feature_id: int):
            reads.append(feature_id)
            return original_get(feature_id)

        self.layer.getFeature = counted_get
        try:
            for value in (0, None, 7):
                reads.clear()
                self.assertTrue(self.plugin.apply_changes(
                    self.layer, {(fid, 'rank'): value}, 'Repeated field'))
                counts.append(len(reads))
        finally:
            self.layer.getFeature = original_get
        self.assertEqual(self.layer.getFeature(fid)['rank'], 7)
        self.assertEqual(len(self.plugin.applied_history), 1)
        entry = self.plugin.applied_history[0]
        self.assertEqual(entry['before'], {(fid, 'rank'): initial})
        self.assertEqual(entry['after'], {(fid, 'rank'): 7})
        self.assertTrue(self.plugin.undo_edit(self.layer))
        self.assertEqual(self.layer.getFeature(fid)['rank'], initial)
        self.assertGreater(counts[0], 0)
        self.assertEqual(counts, [counts[0]] * 3,
                         'Existing before keys, including 0 and NULL, must add no feature reads')

    def test_missing_before_key_checks_external_conflict(self):
        fid = self.ids[0]
        initial_rank = self.layer.getFeature(fid)['rank']
        self.assertTrue(self.plugin.apply_changes(
            self.layer, {(fid, 'status'): 'plugin value'}, 'First field'))
        self.layer.beginEditCommand('Other tool changes previous field')
        self.assertTrue(self.layer.changeAttributeValue(
            fid, self.layer.fields().indexFromName('status'), 'external value'))
        self.layer.endEditCommand()
        self.assertTrue(self.plugin.apply_changes(
            self.layer, {(fid, 'rank'): 99}, 'Different field'))
        self.assertEqual(len(self.plugin.applied_history), 2,
                         'A previous field absent from before must still be read to prevent a conflicting merge')
        self.assertEqual(self.plugin.applied_history[-1]['before'], {(fid, 'rank'): initial_rank})
        self.assertEqual(self.layer.getFeature(fid)['rank'], 99)
        self.assertTrue(self.plugin.undo_edit(self.layer))
        self.assertEqual(self.layer.getFeature(fid)['rank'], initial_rank)
        self.assertEqual(self.layer.getFeature(fid)['status'], 'external value')
        self.assertFalse(self.plugin.undo_edit(self.layer))
        self.assertEqual(self.layer.getFeature(fid)['status'], 'external value')
        self.assertEqual(len(self.plugin.applied_history), 1)

    def test_reorder_preserves_sorting_and_virtual_field_values(self):
        self.layer.addExpressionField('$x', QgsField('x_sort', QMetaType.Type.Double))
        self.nav = navigation.QuickFieldNavigator(self.plugin, self.project)
        self.plugin.dock_widget = self.nav
        self.nav.filter_expression.setExpression(f'$id <> {self.ids[4]}')
        self.nav.reload_features()
        frozen = list(self.nav.filtered_ids)
        applied = self.nav.applied_filter
        self.nav.filter_expression.setExpression('FALSE')
        original_get = self.layer.getFeatures
        request = QgsFeatureRequest().setFilterFids(frozen)
        request.addOrderBy('"x_sort"', True, False)
        request.addOrderBy('$id', True, False)
        reference = list(original_get(request))
        self.assertTrue(all(feature.hasGeometry() for feature in reference))
        x_order = [feature.id() for feature in reference]
        self.assertEqual(x_order, sorted(frozen, key=self.x_by_id.__getitem__))
        returned = []

        def observed_get(feature_request):
            for feature in original_get(feature_request):
                returned.append(feature)
                yield feature

        self.layer.getFeatures = observed_get
        try:
            for name, ascending, expected in (
                ('rank', True, [self.ids[1], self.ids[3], self.ids[0], self.ids[2]]),
                ('rank', False, [self.ids[0], self.ids[1], self.ids[3], self.ids[2]]),
                ('', True, sorted(frozen)),
                ('', False, sorted(frozen, reverse=True)),
                ('x_sort', True, x_order),
                ('x_sort', False, list(reversed(x_order))),
            ):
                with self.subTest(field=name, ascending=ascending):
                    self.nav.sort_field.blockSignals(True)
                    self.nav.ascending.blockSignals(True)
                    try:
                        self.nav.sort_field.setCurrentIndex(self.nav.sort_field.findData(name))
                        self.nav.ascending.setChecked(ascending)
                    finally:
                        self.nav.sort_field.blockSignals(False)
                        self.nav.ascending.blockSignals(False)
                    returned.clear()
                    self.nav.reorder_features()
                    self.assertEqual(self.nav.ids, expected)
                    self.assertEqual([feature.id() for feature in returned], expected)
                    self.assertTrue(returned)
                    self.assertEqual([feature['x_sort'] for feature in returned],
                                     [self.x_by_id[fid] for fid in expected])
                    self.assertEqual(self.nav.filtered_ids, frozen)
                    self.assertEqual(self.nav.applied_filter, applied)
            self.layer.selectByIds([self.ids[0], self.ids[3]])
            returned.clear()
            self.nav.use_current_selection()
            self.assertEqual(self.nav.ids, [self.ids[0], self.ids[3]])
            self.assertEqual([feature.id() for feature in returned], list(reversed(x_order)))
            self.assertEqual(self.nav.selection_snapshot, {self.ids[0], self.ids[3]})
            self.assertEqual(self.nav.filtered_ids, frozen)
            self.assertEqual(self.nav.applied_filter, applied)
            self.assertEqual(self.nav.filter_expression.expression(), 'FALSE')
        finally:
            self.layer.getFeatures = original_get

    def test_load_rows_reuses_lookups_and_preserves_guards(self):
        status_index = self.layer.fields().indexFromName('status')
        self.layer.setEditorWidgetSetup(status_index, QgsEditorWidgetSetup('Hidden', {}))
        self.layer.addExpressionField('$x', QgsField('x_sort', QMetaType.Type.Double))
        schema = [field.name() for field in self.layer.fields()]
        MemorySettings.data[f'quick_field_keys/locked_fields/{self.layer.id()}'] = '["note"]'
        self.layer.selectByIds(self.ids[:2])
        self.editor = editing.FieldEditor(self.plugin, self.layer, embedded=True)
        self.editor.visible_names = ['status', 'rank', 'note', 'tag', 'x_sort', 'missing']
        original_writable = editing.writable_indices
        original_registry = editing.QgsGui.editorWidgetRegistry
        writable_calls = []
        registry_calls = []

        def counted_writable(layer: QgsVectorLayer) -> list[int]:
            writable_calls.append(layer)
            return original_writable(layer)

        def counted_registry():
            registry_calls.append(True)
            return original_registry()

        editing.writable_indices = counted_writable
        editing.QgsGui.editorWidgetRegistry = counted_registry
        try:
            self.editor.load_rows()
        finally:
            editing.writable_indices = original_writable
            editing.QgsGui.editorWidgetRegistry = original_registry
        expected_rows = {'status', 'rank', 'note', 'tag'}
        self.assertEqual(set(self.editor.rows), expected_rows)
        self.assertEqual(self.editor.form.rowCount(), len(expected_rows))
        self.assertEqual(self.editor.rows['status'][0].value(), 'original')
        self.assertTrue(self.editor.rows['status'][0].widget().isEnabled())
        self.assertTrue(self.editor.rows['note'][1].isChecked())
        self.assertFalse(self.editor.rows['note'][0].widget().isEnabled())
        self.editor.rows['note'][1].click()
        self.assertNotIn('note', core.locked_names(self.layer))
        self.assertTrue(self.editor.rows['note'][0].widget().isEnabled())
        self.editor.rows['note'][1].click()
        self.assertTrue(self.layer.setReadOnly(True))
        self.editor.load_rows()
        self.assertEqual(set(self.editor.rows), expected_rows)
        self.assertTrue(all(not wrapper.widget().isEnabled() for wrapper, lock in self.editor.rows.values()))
        self.assertTrue(self.layer.setReadOnly(False))
        self.editor.load_rows()
        self.assertTrue(self.editor.rows['status'][0].widget().isEnabled())
        self.assertTrue(self.editor.rows['note'][1].isChecked())
        self.assertFalse(self.editor.rows['note'][0].widget().isEnabled())
        self.layer.selectByIds([self.ids[4]])
        self.editor.rows['status'][0].setValue('hidden field draft')
        self.assertEqual(self.editor.form_changes(),
                         {(fid, 'status'): 'hidden field draft' for fid in self.ids[:2]})
        self.assertTrue(self.editor.apply_form())
        self.assertEqual([self.layer.getFeature(fid)['status'] for fid in self.ids],
                         ['hidden field draft'] * 2 + ['original'] * 3)
        self.assertEqual([feature['status'] for feature in self.layer.dataProvider().getFeatures()],
                         ['original'] * 5)
        self.assertEqual([field.name() for field in self.layer.fields()], schema)
        self.assertEqual(self.layer.editorWidgetSetup(status_index).type(), 'Hidden')
        self.assertEqual(writable_calls, [self.layer], 'One writable-field lookup per load_rows call')
        self.assertEqual(len(registry_calls), 1, 'One editor registry lookup per load_rows call')

    def test_immediate_preset_refreshes_both_forms_without_losing_note_drafts(self):
        fid = self.ids[0]
        self.layer.selectByIds([fid])
        self.nav = navigation.QuickFieldNavigator(self.plugin, self.project)
        self.plugin.dock_widget = self.nav
        self.nav.zoom_mode.setCurrentIndex(3)
        self.assertTrue(self.plugin.open_field_editor(show=False))
        self.editor = self.plugin.field_editor
        editors = (self.nav.inline_editor, self.editor)
        captured = [list(editor.ids) for editor in editors]
        wrappers = [dict(editor.rows) for editor in editors]
        for editor in editors:
            editor.rows['note'][0].setValue('kept note draft')
        self.plugin.presets = {'1': {'field': 'status', 'value': 'preset result', 'null': False}}

        self.plugin.apply('1')

        self.assertEqual(self.layer.getFeature(fid)['status'], 'preset result')
        self.assertEqual(self.layer.getFeature(fid)['note'], 'same note')
        for editor, ids, rows in zip(editors, captured, wrappers):
            self.assertEqual(editor.ids, ids)
            self.assertIs(editor.rows['status'][0], rows['status'][0])
            self.assertIs(editor.rows['note'][0], rows['note'][0])
            self.assertEqual(editor.rows['status'][0].value(), 'preset result')
            self.assertEqual(editor.initial_values['status'], (True, 'preset result'))
            self.assertEqual(editor.rows['note'][0].value(), 'kept note draft')
            self.assertEqual(editor.initial_values['note'], (True, 'same note'))
            self.assertEqual(editor.changed_fields, {'note'})
        self.assertTrue(self.nav.save_button.isEnabled())

        self.nav.shortcuts[1].activated.emit()
        self.nav.go_to(self.nav.ids.index(fid))

        self.assertEqual([self.layer.getFeature(target)['status'] for target in self.ids],
                         ['preset result'] + ['original'] * 4)
        self.assertEqual(self.layer.getFeature(fid)['note'], 'kept note draft')
        self.assertEqual(self.nav.inline_editor.ids, [fid])
        self.assertEqual(self.nav.inline_editor.rows['status'][0].value(), 'preset result')
        self.assertEqual(self.nav.inline_editor.initial_values['status'], (True, 'preset result'))
        self.assertEqual(self.nav.inline_editor.changed_fields, set())
        self.assertEqual([feature['status'] for feature in self.layer.dataProvider().getFeatures()],
                         ['original'] * 5)
        self.assertEqual([feature['note'] for feature in self.layer.dataProvider().getFeatures()],
                         ['same note'] * 5)

    def test_fully_covered_preset_supersedes_only_its_own_field_draft(self):
        self.layer.selectByIds(self.ids[:2])
        self.nav = navigation.QuickFieldNavigator(self.plugin, self.project)
        self.plugin.dock_widget = self.nav
        self.nav.zoom_mode.setCurrentIndex(3)
        editor = self.nav.inline_editor
        captured = list(editor.ids)
        status, note = editor.rows['status'][0], editor.rows['note'][0]
        status.setValue('stale status draft')
        note.setValue('unrelated note draft')
        self.assertEqual(editor.changed_fields, {'status', 'note'})
        self.plugin.presets = {'1': {'field': 'status', 'value': 'preset wins', 'null': False}}

        self.plugin.apply('1')

        self.assertEqual([self.layer.getFeature(fid)['status'] for fid in self.ids],
                         ['preset wins'] * 2 + ['original'] * 3)
        self.assertEqual(editor.ids, captured)
        self.assertIs(editor.rows['status'][0], status)
        self.assertIs(editor.rows['note'][0], note)
        self.assertEqual(status.value(), 'preset wins')
        self.assertEqual(editor.initial_values['status'], (True, 'preset wins'))
        self.assertEqual(note.value(), 'unrelated note draft')
        self.assertEqual(editor.initial_values['note'], (True, 'same note'))
        self.assertEqual(editor.changed_fields, {'note'})
        self.assertEqual(editor.form_changes(),
                         {(fid, 'note'): 'unrelated note draft' for fid in captured})

        self.nav.shortcuts[1].activated.emit()
        self.nav.go_to(self.nav.ids.index(captured[0]))

        self.assertEqual([self.layer.getFeature(fid)['status'] for fid in self.ids],
                         ['preset wins'] * 2 + ['original'] * 3)
        self.assertEqual([self.layer.getFeature(fid)['note'] for fid in self.ids],
                         ['unrelated note draft'] * 2 + ['same note'] * 3)
        self.assertEqual(editor.ids, [captured[0]])
        self.assertEqual(editor.rows['status'][0].value(), 'preset wins')
        self.assertEqual(editor.initial_values['status'], (True, 'preset wins'))
        self.assertEqual(editor.changed_fields, set())
        self.assertEqual([feature['status'] for feature in self.layer.dataProvider().getFeatures()],
                         ['original'] * 5)

    def test_external_targets_preserve_drafts_and_refresh_only_captured_values(self):
        self.layer.selectByIds(self.ids[:2])
        self.nav = navigation.QuickFieldNavigator(self.plugin, self.project)
        self.plugin.dock_widget = self.nav
        self.assertTrue(self.plugin.open_field_editor(show=False))
        self.editor = self.plugin.field_editor
        editors = (self.nav.inline_editor, self.editor)
        captured = [list(editor.ids) for editor in editors]
        wrappers = [dict(editor.rows) for editor in editors]
        for editor in editors:
            editor.rows['status'][0].setValue('captured status draft')
            editor.rows['note'][0].setValue('captured note draft')
        self.plugin.presets = {
            '1': {'field': 'status', 'value': 'outside preset', 'null': False},
            '2': {'field': 'tag', 'value': 'partial tag', 'null': False},
        }

        for selected, value, expected in (
            ([self.ids[2]], 'outside preset', ['original', 'original', 'outside preset']),
            (self.ids[1:3], 'partial preset', ['original', 'partial preset', 'partial preset']),
        ):
            with self.subTest(selected=selected):
                self.layer.selectByIds(selected)
                self.plugin.presets['1']['value'] = value
                self.plugin.apply('1')
                self.assertEqual([self.layer.getFeature(fid)['status'] for fid in self.ids[:3]], expected)
                for editor, ids, rows in zip(editors, captured, wrappers):
                    self.assertEqual(editor.ids, ids)
                    self.assertIs(editor.rows['status'][0], rows['status'][0])
                    self.assertEqual(editor.rows['status'][0].value(), 'captured status draft')
                    self.assertEqual(editor.initial_values['status'], (True, 'original'))
                    self.assertEqual(editor.rows['note'][0].value(), 'captured note draft')
                    self.assertEqual(editor.initial_values['note'], (True, 'same note'))
                    self.assertEqual(editor.changed_fields, {'status', 'note'})
                    self.assertEqual(set(editor.form_changes()),
                                     {(fid, name) for fid in ids for name in ('status', 'note')})

        self.plugin.apply('2')

        self.assertEqual([self.layer.getFeature(fid)['tag'] for fid in self.ids],
                         ['same tag', 'partial tag', 'partial tag', 'same tag', 'same tag'])
        for editor, ids, rows in zip(editors, captured, wrappers):
            self.assertEqual(editor.ids, ids)
            self.assertIs(editor.rows['tag'][0], rows['tag'][0])
            self.assertTrue(editor.equal(editor.rows['tag'][0].value(), None))
            self.assertEqual(editor.initial_values['tag'], (False, None))
            label = editor.form.itemAt(list(editor.rows).index('tag'),
                                      editing.QFormLayout.ItemRole.LabelRole).widget()
            self.assertEqual(label.text(), 'tag (mixed / empty)')
            self.assertEqual(editor.changed_fields, {'status', 'note'})

        other = QgsVectorLayer('Point?field=status:string', 'Other applied layer', 'memory')
        feature = QgsFeature(other.fields())
        feature.setAttributes(['other original'])
        self.assertTrue(other.dataProvider().addFeatures([feature])[0])
        self.project.addMapLayer(other)
        before = [(dict(editor.initial_values), dict(editor.form_changes())) for editor in editors]
        try:
            other_fid = next(other.getFeatures()).id()
            self.assertTrue(self.plugin.apply_changes(
                other, {(other_fid, 'status'): 'other applied'}, 'Other layer write'))
            self.assertEqual(other.getFeature(other_fid)['status'], 'other applied')
            for editor, ids, state in zip(editors, captured, before):
                self.assertEqual(editor.ids, ids)
                self.assertEqual((editor.initial_values, editor.form_changes()), state)
                self.assertEqual(editor.changed_fields, {'status', 'note'})
        finally:
            if other.isEditable():
                other.rollBack()

    def test_staged_nulls_refresh_only_after_apply_and_restore_signal_state(self):
        self.layer.selectByIds(self.ids[:2])
        self.nav = navigation.QuickFieldNavigator(self.plugin, self.project)
        self.plugin.dock_widget = self.nav
        editor = self.nav.inline_editor
        captured = list(editor.ids)
        status = editor.rows['status'][0]
        editor.rows['note'][0].setValue('keep through NULL presets')
        emissions = []
        status.valueChanged.connect(lambda *args: emissions.append(args))
        self.plugin.set_immediate(False)
        self.plugin.presets = {'1': {'field': 'status', 'value': '', 'null': True}}
        self.layer.selectByIds([self.ids[0]])

        self.plugin.apply('1')

        self.assertEqual(self.plugin.pending_changes, {(self.ids[0], 'status'): None})
        self.assertEqual([self.layer.getFeature(fid)['status'] for fid in self.ids], ['original'] * 5)
        self.assertEqual(editor.ids, captured)
        self.assertIs(editor.rows['status'][0], status)
        self.assertEqual(status.value(), 'original')
        self.assertEqual(editor.initial_values['status'], (True, 'original'))
        self.assertEqual(editor.changed_fields, {'note'})
        self.assertFalse(status.signalsBlocked())

        self.assertTrue(self.plugin.apply_pending())

        self.assertTrue(editor.equal(self.layer.getFeature(self.ids[0])['status'], None))
        self.assertEqual(self.layer.getFeature(self.ids[1])['status'], 'original')
        self.assertTrue(editor.equal(status.value(), None))
        self.assertEqual(editor.initial_values['status'], (False, None))
        label = editor.form.itemAt(list(editor.rows).index('status'),
                                  editing.QFormLayout.ItemRole.LabelRole).widget()
        self.assertEqual(label.text(), 'status (mixed / empty)')
        self.assertEqual(editor.changed_fields, {'note'})
        self.assertFalse(status.signalsBlocked())

        self.layer.selectByIds([self.ids[1]])
        blocked = status.blockSignals(True)
        try:
            self.plugin.apply('1')
            self.assertEqual(self.layer.getFeature(self.ids[1])['status'], 'original')
            self.assertEqual(editor.initial_values['status'], (False, None))
            self.assertTrue(self.plugin.apply_pending())
            self.assertTrue(status.signalsBlocked())
        finally:
            status.blockSignals(blocked)

        self.assertTrue(all(editor.equal(self.layer.getFeature(fid)['status'], None) for fid in captured))
        self.assertTrue(editor.equal(status.value(), None))
        self.assertTrue(editor.initial_values['status'][0])
        self.assertTrue(editor.equal(editor.initial_values['status'][1], None))
        self.assertEqual(label.text(), 'status')
        self.assertEqual(editor.ids, captured)
        self.assertIs(editor.rows['status'][0], status)
        self.assertEqual(editor.rows['note'][0].value(), 'keep through NULL presets')
        self.assertEqual(editor.initial_values['note'], (True, 'same note'))
        self.assertEqual(editor.changed_fields, {'note'})
        self.assertEqual(emissions, [])
        self.assertFalse(self.plugin.pending_changes)
        self.assertTrue(self.nav.save_button.isEnabled())
        self.assertEqual([feature['status'] for feature in self.layer.dataProvider().getFeatures()],
                         ['original'] * 5)

    def test_locked_and_failed_pending_writes_do_not_rebase_forms(self):
        self.layer.selectByIds(self.ids[:2])
        self.nav = navigation.QuickFieldNavigator(self.plugin, self.project)
        self.plugin.dock_widget = self.nav
        editor = self.nav.inline_editor
        captured = list(editor.ids)
        status, lock = editor.rows['status']
        editor.rows['note'][0].setValue('retained note draft')
        self.plugin.set_immediate(False)
        self.plugin.presets = {'1': {'field': 'status', 'value': 'pending winner', 'null': False}}
        self.plugin.apply('1')
        pending = dict(self.plugin.pending_changes)
        lock.click()

        self.assertFalse(self.plugin.apply_pending())

        self.assertTrue(lock.isChecked())
        self.assertFalse(status.widget().isEnabled())
        self.assertEqual([self.layer.getFeature(fid)['status'] for fid in self.ids], ['original'] * 5)
        self.assertEqual(status.value(), 'original')
        self.assertEqual(editor.initial_values['status'], (True, 'original'))
        self.assertEqual(editor.changed_fields, {'note'})
        self.assertEqual(editor.ids, captured)
        self.assertEqual(self.plugin.pending_changes, pending)
        lock.click()
        status.setValue('retry status draft')
        original_change = self.layer.changeAttributeValue
        calls = []

        def fail_second(*args, **kwargs):
            calls.append(args)
            return False if len(calls) == 2 else original_change(*args, **kwargs)

        self.layer.changeAttributeValue = fail_second
        try:
            self.assertFalse(self.plugin.apply_pending())
        finally:
            self.layer.changeAttributeValue = original_change

        self.assertEqual(len(calls), 2)
        self.assertEqual([self.layer.getFeature(fid)['status'] for fid in self.ids], ['original'] * 5)
        self.assertIs(editor.rows['status'][0], status)
        self.assertEqual(status.value(), 'retry status draft')
        self.assertEqual(editor.initial_values['status'], (True, 'original'))
        self.assertEqual(editor.rows['note'][0].value(), 'retained note draft')
        self.assertEqual(editor.initial_values['note'], (True, 'same note'))
        self.assertEqual(editor.changed_fields, {'status', 'note'})
        self.assertEqual(editor.ids, captured)
        self.assertEqual(self.plugin.pending_changes, pending)
        self.assertFalse(self.plugin.applied_history)
        self.assertFalse(lock.isChecked())
        self.assertTrue(status.widget().isEnabled())
        self.assertTrue(self.nav.save_button.isEnabled())

        self.assertTrue(self.plugin.apply_pending())

        self.assertEqual([self.layer.getFeature(fid)['status'] for fid in self.ids],
                         ['pending winner'] * 2 + ['original'] * 3)
        self.assertIs(editor.rows['status'][0], status)
        self.assertEqual(status.value(), 'pending winner')
        self.assertEqual(editor.initial_values['status'], (True, 'pending winner'))
        self.assertEqual(editor.rows['note'][0].value(), 'retained note draft')
        self.assertEqual(editor.initial_values['note'], (True, 'same note'))
        self.assertEqual(editor.changed_fields, {'note'})
        self.assertEqual(editor.ids, captured)
        self.assertFalse(self.plugin.pending_changes)
        self.assertEqual([feature['status'] for feature in self.layer.dataProvider().getFeatures()],
                         ['original'] * 5)


original_settings = (core.QgsSettings, navigation.QgsSettings, editing.QgsSettings)
core.QgsSettings = MemorySettings
navigation.QgsSettings = MemorySettings
editing.QgsSettings = MemorySettings
try:
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(OptimizationTests)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
finally:
    core.QgsSettings, navigation.QgsSettings, editing.QgsSettings = original_settings
assert result.wasSuccessful(), 'Optimization regression tests failed'
print('PASS: lazy feature reads, conflicting-history fallback, virtual-field sorting preserved, per-build row lookups and edit guards; applied-value synchronization preserves captured drafts, staging and failure guards', flush=True)
