"""SPDX-License-Identifier: GPL-3.0-or-later

Navigation behavior is inspired by FeatureNavEd 1.0.8 by Irene Jaya (MIT).
This independent implementation uses explicit editing and an isolated namespace.
See LICENSE.FeatureNavEd for the original project's license and attribution.
"""
from qgis.core import (
    Qgis, QgsCoordinateTransform, QgsExpression, QgsFeatureRequest,
    QgsMapLayerProxyModel, QgsProject, QgsRectangle, QgsSettings, QgsVariantUtils,
    QgsVectorLayer,
)
from qgis.gui import QgsMapLayerComboBox, QgsMapToolIdentifyFeature
from qgis.PyQt.QtCore import Qt
from qgis.PyQt.QtGui import QKeySequence, QShortcut
from qgis.PyQt.QtWidgets import (
    QCheckBox, QComboBox, QDockWidget, QDoubleSpinBox, QFormLayout,
    QHBoxLayout, QLabel, QLineEdit, QPushButton, QVBoxLayout, QWidget,
)


class QuickFieldNavigator(QDockWidget):
    def __init__(self, plugin, project=None):
        super().__init__('Quick Field Keys - Navigator', plugin.iface.mainWindow())
        self.setObjectName('QuickFieldKeysNavigatorDock')
        self.plugin = plugin
        self.iface = plugin.iface
        self.project = project or QgsProject.instance()
        self.layer = None
        self.ids = []
        self.index = -1
        self.selection_snapshot = None
        self.pick_tool = None
        self.previous_tool = None
        self._navigating = False
        widget = QWidget(self)
        layout = QVBoxLayout(widget)
        self.setWidget(widget)
        self.layer_combo = QgsMapLayerComboBox()
        self.layer_combo.setProject(self.project)
        self.layer_combo.setFilters(QgsMapLayerProxyModel.VectorLayer)
        self.layer_combo.setAllowEmptyLayer(True)
        layout.addWidget(self.layer_combo)
        form = QFormLayout()
        layout.addLayout(form)
        self.sort_field = QComboBox()
        self.ascending = QCheckBox('Ascending')
        self.ascending.setChecked(True)
        sort_row = QHBoxLayout()
        sort_row.addWidget(self.sort_field, 1)
        sort_row.addWidget(self.ascending)
        form.addRow('Sort by', sort_row)
        self.position = QLabel('No features')
        layout.addWidget(self.position)
        row = QHBoxLayout()
        for text, callback in (
            ('First', lambda: self.go_to(0)), ('Previous', lambda: self.step(-1)),
            ('Next', lambda: self.step(1)), ('Last', lambda: self.go_to(len(self.ids) - 1)),
        ):
            button = QPushButton(text)
            button.clicked.connect(callback)
            row.addWidget(button)
        layout.addLayout(row)
        self.filter_expression = QLineEdit()
        self.filter_expression.setPlaceholderText('QGIS expression, e.g. "status" = \'review\'')
        filter_button = QPushButton('Apply filter / reload')
        filter_button.clicked.connect(self.reload_features)
        form.addRow('Filter', self.filter_expression)
        layout.addWidget(filter_button)
        self.selected_only = QCheckBox('Selected snapshot only')
        capture = QPushButton('Capture selection')
        capture.clicked.connect(self.capture_selection)
        row = QHBoxLayout()
        row.addWidget(self.selected_only)
        row.addWidget(capture)
        layout.addLayout(row)
        self.search_field = QComboBox()
        self.search_value = QLineEdit()
        self.search_value.setPlaceholderText('Exact field value')
        find = QPushButton('Find next')
        find.clicked.connect(self.find_next)
        row = QHBoxLayout()
        row.addWidget(self.search_field, 1)
        row.addWidget(self.search_value, 1)
        row.addWidget(find)
        layout.addLayout(row)
        self.auto_zoom = QCheckBox('Auto zoom')
        self.auto_zoom.setChecked(True)
        self.zoom_mode = QComboBox()
        self.zoom_mode.addItems(['Fit feature', 'Keep current scale', 'Fixed scale'])
        self.scale = QDoubleSpinBox()
        self.scale.setRange(1, 100000000)
        self.scale.setDecimals(0)
        self.scale.setValue(1000)
        row = QHBoxLayout()
        row.addWidget(self.auto_zoom)
        row.addWidget(self.zoom_mode, 1)
        row.addWidget(self.scale)
        layout.addLayout(row)
        self.pick_button = QPushButton('Pick from map')
        self.pick_button.setCheckable(True)
        self.pick_button.toggled.connect(self.toggle_pick)
        layout.addWidget(self.pick_button)
        row = QHBoxLayout()
        for text, callback in (
            ('Presets...', plugin.configure), ('Edit chosen fields...', plugin.open_field_editor),
            ('Undo', self.undo),
        ):
            button = QPushButton(text)
            button.clicked.connect(callback)
            row.addWidget(button)
        layout.addLayout(row)
        self.immediate = QCheckBox('Apply Alt+1-9 immediately to layer edits')
        self.immediate.setChecked(plugin.immediate)
        self.immediate.toggled.connect(plugin.set_immediate)
        layout.addWidget(self.immediate)
        self.pending_status = QLabel()
        layout.addWidget(self.pending_status)
        self.shortcuts_enabled = QCheckBox('Enable Alt+Left/Right/Home/End navigation')
        self.shortcuts_enabled.setToolTip('Disable FeatureNavEd before enabling these shortcuts.')
        layout.addWidget(self.shortcuts_enabled)
        self.shortcuts = []
        for key, callback in (
            ('Alt+Left', lambda: self.step(-1)), ('Alt+Right', lambda: self.step(1)),
            ('Alt+Home', lambda: self.go_to(0)), ('Alt+End', lambda: self.go_to(len(self.ids) - 1)),
        ):
            shortcut = QShortcut(QKeySequence(key), self)
            shortcut.setContext(Qt.ShortcutContext.ApplicationShortcut)
            shortcut.setAutoRepeat(False)
            shortcut.setEnabled(False)
            shortcut.activated.connect(callback)
            shortcut.activatedAmbiguously.connect(
                lambda: plugin.warn('Navigation shortcut conflict. Check other plugins and shortcuts.'))
            self.shortcuts.append(shortcut)
        self.shortcuts_enabled.toggled.connect(self.update_shortcuts)
        self.visibilityChanged.connect(self.update_shortcuts)
        self.layer_combo.layerChanged.connect(self.change_layer)
        self.sort_field.currentIndexChanged.connect(self.reload_features)
        self.ascending.toggled.connect(self.reload_features)
        self.selected_only.toggled.connect(self.capture_selection)
        self.project.layersWillBeRemoved.connect(self.layers_removed)
        current = self.iface.activeLayer()
        if isinstance(current, QgsVectorLayer) and self.project.mapLayer(current.id()) is current:
            self.layer_combo.setLayer(current)
        self.change_layer(self.layer_combo.currentLayer())
        self.refresh_quick_status()

    def change_layer(self, layer):
        self.stop_pick()
        if self.layer is not None:
            self.disconnect_layer()
        self.layer = layer if isinstance(layer, QgsVectorLayer) else None
        self.selection_snapshot = None
        self.ids = []
        self.index = -1
        self.filter_expression.clear()
        self.refresh_fields()
        if self.layer is not None:
            self.layer.selectionChanged.connect(self.selection_changed)
            self.layer.updatedFields.connect(self.refresh_fields)
            self.layer.featureAdded.connect(self.reload_features)
            self.layer.featureDeleted.connect(self.reload_features)
        if self.selected_only.isChecked() and self.layer is not None:
            self.selection_snapshot = set(self.layer.selectedFeatureIds())
        self.reload_features()

    def refresh_fields(self, *args):
        sort = self.sort_field.currentData()
        search = self.search_field.currentData()
        self.sort_field.blockSignals(True)
        self.search_field.blockSignals(True)
        self.sort_field.clear()
        self.search_field.clear()
        self.sort_field.addItem('(Feature ID)', '')
        if self.layer is not None:
            for field in self.layer.fields():
                self.sort_field.addItem(field.name(), field.name())
                self.search_field.addItem(field.name(), field.name())
        self.sort_field.setCurrentIndex(max(0, self.sort_field.findData(sort)))
        self.search_field.setCurrentIndex(max(0, self.search_field.findData(search)))
        self.sort_field.blockSignals(False)
        self.search_field.blockSignals(False)
        self.reload_features()

    def reload_features(self, *args):
        if self.layer is None or not self.layer.isValid():
            self.ids = []
            self.index = -1
            self.update_position()
            return
        expression = self.filter_expression.text().strip()
        if expression and QgsExpression(expression).hasParserError():
            self.plugin.warn('Invalid filter expression. The previous navigation list was retained.')
            return
        previous = self.ids[self.index] if 0 <= self.index < len(self.ids) else None
        request = QgsFeatureRequest().setFlags(Qgis.FeatureRequestFlag.NoGeometry)
        if expression:
            request.setFilterExpression(expression)
        name = self.sort_field.currentData()
        sort = QgsExpression.quotedColumnRef(name) if name else '$id'
        request.addOrderBy(sort, self.ascending.isChecked(), False)
        if name:
            request.addOrderBy('$id', True, False)
        try:
            ids = [feature.id() for feature in self.layer.getFeatures(request)]
        except Exception as error:
            self.plugin.warn(f'Could not load the navigation list: {error}')
            return
        if self.selected_only.isChecked():
            snapshot = self.selection_snapshot or set()
            ids = [fid for fid in ids if fid in snapshot]
        self.ids = ids
        selected = self.layer.selectedFeatureIds()
        current = previous if previous in ids else next((fid for fid in selected if fid in ids), None)
        self.index = ids.index(current) if current is not None else -1
        self.update_position()

    def capture_selection(self, *args):
        self.selection_snapshot = set(self.layer.selectedFeatureIds()) if self.layer is not None else set()
        self.reload_features()

    def selection_changed(self, *args):
        if self._navigating or self.layer is None:
            return
        selected = self.layer.selectedFeatureIds()
        if len(selected) == 1 and selected[0] in self.ids:
            self.index = self.ids.index(selected[0])
        self.update_position()

    def step(self, direction):
        if not self.ids:
            return
        target = (0 if direction > 0 else len(self.ids) - 1) if self.index < 0 else self.index + direction
        self.go_to(max(0, min(len(self.ids) - 1, target)))

    def go_to(self, index):
        if self.layer is None or not 0 <= index < len(self.ids):
            return
        feature = self.layer.getFeature(self.ids[index])
        if not feature.isValid():
            self.plugin.warn('The feature no longer exists. Reload the navigation list.')
            return
        # Align the navigation target with the existing Alt+number target contract.
        self.iface.setActiveLayer(self.layer)
        self._navigating = True
        try:
            self.layer.selectByIds([feature.id()])
        finally:
            self._navigating = False
        self.index = index
        if self.auto_zoom.isChecked() and feature.hasGeometry():
            self.zoom_to(feature)
        self.update_position()

    def zoom_to(self, feature):
        canvas = self.iface.mapCanvas()
        try:
            transform = QgsCoordinateTransform(
                self.layer.crs(), canvas.mapSettings().destinationCrs(), self.project)
            geometry = feature.geometry()
            if geometry.isEmpty():
                return
            box = transform.transformBoundingBox(geometry.boundingBox())
            if self.zoom_mode.currentIndex() == 0 and max(box.width(), box.height()) > 0:
                if min(box.width(), box.height()) <= 0:
                    box.grow(max(box.width(), box.height()) * 0.1)
                box.scale(1.2)
                canvas.setExtent(box)
            else:
                center = transform.transform(geometry.centroid().asPoint())
                # A blank canvas has no extent; setCenter/zoomScale alone cannot initialize it.
                if canvas.extent().isNull():
                    canvas.setExtent(QgsRectangle(center.x() - 1, center.y() - 1,
                                                  center.x() + 1, center.y() + 1))
                canvas.setCenter(center)
                if self.zoom_mode.currentIndex() != 1:
                    canvas.zoomScale(self.scale.value())
            canvas.refresh()
        except Exception as error:
            self.plugin.warn(f'Feature selected, but zoom failed: {error}')

    def update_position(self):
        if not self.ids:
            self.position.setText('No matching features')
            return
        text = f'{self.index + 1 if self.index >= 0 else "-"} / {len(self.ids)}'
        if self.layer is not None:
            text += f' | selected: {self.layer.selectedFeatureCount()}'
            if 0 <= self.index < len(self.ids):
                feature = self.layer.getFeature(self.ids[self.index])
                name = self.sort_field.currentData()
                if name and self.layer.fields().indexFromName(name) < 0:
                    name = ''
                value = feature[name] if name else feature.id()
                text += f' | {name or "FID"}: {value}'
        self.position.setText(text)

    def find_next(self, *args):
        if self.layer is None or not self.ids or not self.search_field.currentData():
            return
        if self.layer.fields().indexFromName(self.search_field.currentData()) < 0:
            self.refresh_fields()
            self.plugin.warn('The search field changed. Select a field and retry.')
            return
        target = self.search_value.text()
        for offset in range(1, len(self.ids) + 1):
            index = (self.index + offset) % len(self.ids)
            value = self.layer.getFeature(self.ids[index])[self.search_field.currentData()]
            if not QgsVariantUtils.isNull(value) and str(value) == target:
                self.go_to(index)
                return
        self.plugin.warn('No exact match inside the current navigation list.')

    def toggle_pick(self, enabled):
        if not enabled or self.layer is None:
            self.stop_pick()
            return
        canvas = self.iface.mapCanvas()
        self.previous_tool = canvas.mapTool()
        self.pick_tool = QgsMapToolIdentifyFeature(canvas, self.layer)
        self.pick_tool.featureIdentified.connect(self.picked)
        canvas.setMapTool(self.pick_tool)

    def picked(self, feature):
        fid = feature.id() if hasattr(feature, 'id') else int(feature)
        if fid in self.ids:
            self.go_to(self.ids.index(fid))
        else:
            self.plugin.warn('The picked feature is outside the current filter or selection snapshot.')

    def stop_pick(self):
        if self.pick_tool is not None:
            canvas = self.iface.mapCanvas()
            if canvas.mapTool() is self.pick_tool:
                if self.previous_tool is not None:
                    canvas.setMapTool(self.previous_tool)
                else:
                    canvas.unsetMapTool(self.pick_tool)
            self.pick_tool.deleteLater()
        self.pick_tool = None
        self.previous_tool = None
        self.pick_button.blockSignals(True)
        self.pick_button.setChecked(False)
        self.pick_button.blockSignals(False)

    def update_shortcuts(self, *args):
        import qgis.utils
        enabled = self.shortcuts_enabled.isChecked()
        if enabled and 'featurenaved' in qgis.utils.plugins:
            self.shortcuts_enabled.blockSignals(True)
            self.shortcuts_enabled.setChecked(False)
            self.shortcuts_enabled.blockSignals(False)
            enabled = False
            self.plugin.warn('Disable FeatureNavEd in Plugin Manager before enabling navigation shortcuts.')
        for shortcut in self.shortcuts:
            shortcut.setEnabled(enabled and self.isVisible())
        if not self.isVisible():
            self.stop_pick()

    def refresh_quick_status(self):
        self.immediate.blockSignals(True)
        self.immediate.setChecked(self.plugin.immediate)
        self.immediate.blockSignals(False)
        self.pending_status.setText(f'Pending shortcut field changes: {len(self.plugin.pending_changes)}. No automatic file save.')
        # ponytail: full O(n) reload keeps edited sort values current; use a provider cursor for very large layers.
        self.reload_features()

    def undo(self, *args):
        if self.layer is not None:
            self.plugin.undo_edit(self.layer)
            self.reload_features()

    def layers_removed(self, ids):
        if self.layer is not None and self.layer.id() in ids:
            self.stop_pick()
            self.layer_combo.setLayer(None)

    def shutdown(self):
        for shortcut in self.shortcuts:
            shortcut.setEnabled(False)
        self.stop_pick()
        if self.layer is not None:
            self.disconnect_layer()
        try:
            self.project.layersWillBeRemoved.disconnect(self.layers_removed)
        except (TypeError, RuntimeError):
            pass

    def disconnect_layer(self):
        for name, callback in (
            ('selectionChanged', self.selection_changed), ('updatedFields', self.refresh_fields),
            ('featureAdded', self.reload_features), ('featureDeleted', self.reload_features),
        ):
            try:
                getattr(self.layer, name).disconnect(callback)
            except (TypeError, RuntimeError):
                pass
