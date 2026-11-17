"""Large-edit QGIS regression cases; no user profile or files are changed."""
from pathlib import Path
import sys
import tempfile

from qgis.core import Qgis, QgsFeature, QgsGeometry, QgsProject, QgsVectorFileWriter, QgsVectorLayer

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from quick_field_keys.plugin import QuickFieldKeys
from quick_field_keys.bulk_reads import BatchFeatureReader


class Messages:
    def pushSuccess(self, *args):
        pass

    def pushWarning(self, *args):
        pass


class Iface:
    def messageBar(self):
        return Messages()


def fixture():
    layer = QgsVectorLayer('Point?field=value:integer&field=note:string', 'bulk test', 'memory')
    features = []
    for i in range(40):
        feature = QgsFeature(layer.fields())
        feature.setAttributes([0, 'preserve'])
        feature.setGeometry(QgsGeometry.fromWkt(f'POINT ({i} {i})'))
        features.append(feature)
    assert layer.dataProvider().addFeatures(features)[0]
    ids = [feature.id() for feature in layer.getFeatures()]
    return layer, QuickFieldKeys(Iface()), ids


def test_large_apply_uses_three_fresh_snapshots():
    # Given
    layer, plugin, ids = fixture()
    one, many = layer.getFeature, layer.getFeatures
    calls = [0, 0]

    def read_one(fid):
        calls[0] += 1
        return one(fid)

    def read_many(request):
        calls[1] += 1
        features = list(many(request))
        # Providers may ignore fetch hints; request them without assuming compliance.
        assert request.flags() & Qgis.FeatureRequestFlag.NoGeometry
        assert request.subsetOfAttributes() == [0]
        return iter(features)

    layer.getFeature, layer.getFeatures = read_one, read_many
    try:
        # When
        result = plugin.apply_changes(layer, {(fid, 'value'): 9 for fid in ids}, 'bulk apply')
        # Then
        assert result
        assert calls == [0, 3], calls
        assert all(feature['value'] == 9 and feature['note'] == 'preserve' for feature in many())
        assert all(feature.hasGeometry() for feature in many())
        assert len(plugin.applied_history) == 1
        assert all(value == 0 for value in plugin.applied_history[0]['before'].values())
    finally:
        layer.getFeature, layer.getFeatures = one, many
        layer.rollBack()


def test_bulk_reader_keeps_geometry_out_of_cache_only():
    # Given
    layer, unused_plugin, ids = fixture()
    # When
    reader = BatchFeatureReader(layer, {(fid, 'value'): 9 for fid in ids})
    # Then
    assert all(not feature.hasGeometry() for feature in reader.features.values())
    assert all(feature.hasGeometry() for feature in layer.getFeatures())


def test_large_failure_reverts_only_its_own_writes():
    # Given
    layer, plugin, ids = fixture()
    assert layer.startEditing()
    assert layer.changeAttributeValue(ids[-1], 1, 'external edit')
    change = layer.changeAttributeValue
    calls = [0]

    def fail_third(*args, **kwargs):
        calls[0] += 1
        return False if calls[0] == 3 else change(*args, **kwargs)

    layer.changeAttributeValue = fail_third
    try:
        # When
        result = plugin.apply_changes(layer, {(fid, 'value'): 9 for fid in ids}, 'failed bulk apply')
        # Then
        assert not result
        assert all(feature['value'] == 0 for feature in layer.getFeatures())
        assert layer.getFeature(ids[-1])['note'] == 'external edit'
        assert not plugin.applied_history
    finally:
        layer.changeAttributeValue = change
        layer.rollBack()


def test_large_apply_rejects_missing_target_before_editing():
    # Given
    layer, plugin, ids = fixture()
    changes = {(fid, 'value'): 9 for fid in ids}
    changes[(max(ids) + 100, 'value')] = 9
    # When
    result = plugin.apply_changes(layer, changes, 'missing target')
    # Then
    assert not result and not layer.isEditable()
    assert all(feature['value'] == 0 for feature in layer.getFeatures())


def test_bulk_geopackage_requires_explicit_save():
    # Given
    memory, unused_plugin, unused_ids = fixture()
    with tempfile.TemporaryDirectory(prefix='qfk_bulk_gpkg_', ignore_cleanup_errors=True) as directory:
        filename = str(Path(directory) / 'bulk.gpkg')
        options = QgsVectorFileWriter.SaveVectorOptions()
        options.driverName = 'GPKG'
        options.layerName = 'bulk'
        written = QgsVectorFileWriter.writeAsVectorFormatV3(
            memory, filename, QgsProject.instance().transformContext(), options)
        assert written[0] == QgsVectorFileWriter.WriterError.NoError
        layer = QgsVectorLayer(filename + '|layername=bulk', 'bulk disk', 'ogr')
        assert layer.isValid()
        ids = [feature.id() for feature in layer.getFeatures()]
        plugin = QuickFieldKeys(Iface())
        # When
        assert plugin.apply_changes(layer, {(fid, 'value'): 7 for fid in ids}, 'disk bulk')
        before_save = QgsVectorLayer(filename + '|layername=bulk', 'before save', 'ogr')
        # Then
        assert all(feature['value'] == 0 for feature in before_save.getFeatures())
        assert all(feature['value'] == 7 for feature in layer.getFeatures())
        assert layer.commitChanges()
        reopened = QgsVectorLayer(filename + '|layername=bulk', 'after save', 'ogr')
        assert all(feature['value'] == 7 and feature.hasGeometry()
                   and feature['note'] == 'preserve' for feature in reopened.getFeatures())


test_large_apply_uses_three_fresh_snapshots()
test_bulk_reader_keeps_geometry_out_of_cache_only()
test_large_failure_reverts_only_its_own_writes()
test_large_apply_rejects_missing_target_before_editing()
test_bulk_geopackage_requires_explicit_save()
print('PASS: bulk snapshots 5/5: fresh reads, geometry-free cache, geometry retained, rollback, external edits, missing targets, explicit GeoPackage save')
