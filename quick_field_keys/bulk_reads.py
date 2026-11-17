"""SPDX-License-Identifier: GPL-3.0-or-later

Fresh per-phase QGIS snapshots for large attribute-edit batches.
Only edited attributes are needed; geometry stays in the source layer untouched.
"""
from qgis.core import Qgis, QgsFeature, QgsFeatureRequest


class BatchFeatureReader:
    def __init__(self, layer, changes):
        self.layer = layer
        self.ids = {fid for fid, name in changes}
        self.names = {name for fid, name in changes}
        self.bulk = len(self.ids) >= 32
        self.features = {}
        self.refresh()

    def refresh(self):
        if self.bulk:
            request = QgsFeatureRequest().setFilterFids(list(self.ids))
            request.setFlags(Qgis.FeatureRequestFlag.NoGeometry)
            request.setSubsetOfAttributes(list(self.names), self.layer.fields())
            self.features.clear()
            for feature in self.layer.getFeatures(request):
                # Some providers ignore NoGeometry. Discard it from this local copy only.
                feature.clearGeometry()
                self.features[feature.id()] = feature

    def get(self, fid):
        if not self.bulk:
            return self.layer.getFeature(fid)
        feature = self.features.get(fid)
        return QgsFeature() if feature is None else feature


_PythonBatchFeatureReader = BatchFeatureReader
