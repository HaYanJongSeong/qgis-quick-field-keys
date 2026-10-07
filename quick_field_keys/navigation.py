"""SPDX-License-Identifier: GPL-3.0-or-later

Navigation behavior is inspired by FeatureNavEd 1.0.8 by Irene Jaya (MIT).
This independent implementation uses explicit editing and an isolated namespace.
See LICENSE.FeatureNavEd for the original project's license and attribution.
"""
import hashlib
import json
import os
from pathlib import Path

from qgis.core import (
    Qgis, QgsApplication, QgsCoordinateTransform, QgsExpression, QgsFeatureRequest,
    QgsMapLayerProxyModel, QgsProject, QgsRectangle, QgsSettings,
    QgsVectorLayer,
)
from qgis.gui import QgsExpressionLineEdit, QgsMapLayerComboBox
from qgis.PyQt.QtCore import QByteArray, Qt
from qgis.PyQt.QtGui import QIcon, QKeySequence
try:
    from qgis.PyQt.QtGui import QShortcut
except ImportError:
    from qgis.PyQt.QtWidgets import QShortcut
from qgis.PyQt.QtWidgets import (
    QApplication, QCheckBox, QComboBox, QDockWidget, QDoubleSpinBox,
    QHBoxLayout, QLabel, QPushButton, QScrollArea, QStyle, QToolButton, QVBoxLayout, QWidget,
)


class QuickFieldNavigator(QDockWidget):
    def __init__(self, plugin, project=None):
        super().__init__('Quick Field Keys - Navigator', plugin.iface.mainWindow())
        self.setObjectName('QuickFieldKeysNavigatorDock')
        self.plugin = plugin
        self.iface = plugin.iface
        self.project = project or QgsProject.instance()
        self._ready = False
        self._restoring = True
        self._layout_restored = False
        self._session_key = self.session_key()
        self._layout_state = self.read_state('quick_field_keys/navigator/layout')
        self.applied_filter = ''
        self.layer = None
        self.ids = []
        self.filtered_ids = []
        self.index = -1
        self.selection_snapshot = None
        self._navigating = False
        self.view_history = []
        self.inline_editor = None
        widget = QWidget(self)
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(4)
        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setWidget(widget)
        self.setWidget(scroll)
        layer_group = QWidget()
        layer_group.setObjectName('layer_controls')
        layer_layout = QVBoxLayout(layer_group)
        layer_layout.setContentsMargins(0, 0, 0, 0)
        layer_layout.setSpacing(4)
        layout.addWidget(layer_group)
        self.layer_combo = QgsMapLayerComboBox()
        self.layer_combo.setProject(self.project)
        self.layer_combo.setFilters(QgsMapLayerProxyModel.Filter.VectorLayer)
        self.layer_combo.setAllowEmptyLayer(True)
        self.layer_combo.setToolTip('Target layer — Navigation and preset writes use this layer even when another QGIS layer is active or this panel is hidden.\n반영 대상 레이어 — 탐색과 프리셋 입력은 여기서 지정한 레이어에 반영합니다. 다른 레이어를 활성화하거나 패널을 숨겨도 대상은 유지됩니다.')
        layer_layout.addWidget(self.layer_combo)
        self.sort_field = QComboBox()
        self.sort_field.setToolTip('Sort field — Choose the column used to order features.\n정렬 필드 — 객체 순서의 기준이 될 컬럼을 선택합니다.')
        self.ascending = QCheckBox('Ascending')
        self.ascending.setToolTip('Ascending — Checked: ascending order. Unchecked: descending order.\n오름차순 — 체크하면 오름차순, 해제하면 내림차순으로 정렬합니다.')
        self.ascending.setChecked(True)
        sort_row = QHBoxLayout()
        sort_row.addWidget(self.sort_field, 1)
        sort_row.addWidget(self.ascending)
        sort_row.insertWidget(0, QLabel('Sort by'))
        layer_layout.addLayout(sort_row)

        navigate_group = QWidget()
        navigate_group.setObjectName('navigation_controls')
        navigate_layout = QVBoxLayout(navigate_group)
        navigate_layout.setContentsMargins(0, 0, 0, 0)
        navigate_layout.setSpacing(4)
        # Insert after the filter section below.
        self.position = QLabel('No features')
        self.position.setWordWrap(True)
        row = QHBoxLayout()
        row.addWidget(self.position, 1)
        self.navigation_buttons = {}
        for name, tooltip, icon, callback in (
            ('first_feature', 'First (Alt+Home) — Select the first feature in the current list.\n처음 (Alt+Home) — 현재 목록의 첫 객체로 이동합니다.', QStyle.StandardPixmap.SP_MediaSkipBackward, lambda: self.go_to(0)),
            ('previous_feature', 'Previous (Alt+Left) — Select the previous feature; first wraps to last.\n이전 (Alt+Left) — 이전 객체로 이동합니다. 첫 객체에서는 마지막으로 이동합니다.', QStyle.StandardPixmap.SP_ArrowLeft, lambda: self.step(-1)),
            ('next_feature', 'Next (Alt+Right) — Select the next feature; last wraps to first.\n다음 (Alt+Right) — 다음 객체로 이동합니다. 마지막에서는 처음으로 돌아갑니다.', QStyle.StandardPixmap.SP_ArrowRight, lambda: self.step(1)),
            ('last_feature', 'Last (Alt+End) — Select the last feature in the current list.\n끝 (Alt+End) — 현재 목록의 마지막 객체로 이동합니다.', QStyle.StandardPixmap.SP_MediaSkipForward, lambda: self.go_to(len(self.ids) - 1)),
        ):
            button = QToolButton(self)
            button.setObjectName(name)
            button.setAccessibleName(tooltip.split(' (')[0])
            button.setToolTip(tooltip)
            button.setIcon(self.style().standardIcon(icon))
            button.clicked.connect(callback)
            row.addWidget(button)
            self.navigation_buttons[name] = button
        navigate_layout.addLayout(row)
        self.back_button = QToolButton(self)
        self.back_button.setIcon(QIcon(str(Path(__file__).with_name('previous_view.svg'))))
        self.back_button.setToolTip('Previous view (Alt+Backspace) — Restore the previous selection and map view without changing the filter.\n직전 화면 (Alt+Backspace) — 필터를 유지한 채 직전 선택 객체와 지도 화면을 복원합니다. 편집은 취소하지 않습니다.')
        self.back_button.setAccessibleName('Previous view')
        self.back_button.setShortcut(QKeySequence('Alt+Backspace'))
        self.back_button.setEnabled(False)
        self.back_button.clicked.connect(self.back_view)
        row.addSpacing(12)
        row.addWidget(self.back_button)
        self.flash_button = QToolButton(self)
        self.flash_button.setObjectName('flash_selected_features')
        self.flash_button.setIcon(QIcon(str(Path(__file__).with_name('flash_features.svg'))))
        self.flash_button.setAccessibleName('Flash selected features / 선택 객체 반짝임')
        self.flash_button.setToolTip('Flash selected features — Flash the designated layer\'s current selection without changing selection, zoom or values. Navigation flashes automatically.\n선택 객체 반짝임 — 지정 레이어의 현재 선택 객체를 반짝입니다. 선택·줌·값을 바꾸지 않으며 객체 이동 시에도 자동으로 반짝입니다.')
        self.flash_button.clicked.connect(self.flash_selected)
        row.addWidget(self.flash_button)
        self.zoom_mode = QComboBox()
        self.zoom_mode.addItems(['Fit feature', 'Keep current scale', 'Fixed scale', 'No zoom'])
        self.zoom_mode.setToolTip('Zoom mode — Fit feature, keep scale, fixed scale, or no zoom when navigating.\n줌 방식 — 객체 맞춤, 현재 축척 유지, 고정 축척, 줌 안 함 중 선택합니다.')
        self.scale = QDoubleSpinBox()
        self.scale.setRange(1, 100000000)
        self.scale.setDecimals(0)
        self.scale.setValue(1000)
        self.scale.setPrefix('1:')
        self.scale.setToolTip('Fixed scale — Enter the scale denominator; available only in Fixed scale mode.\n고정 축척 — 축척의 분모를 입력합니다. Fixed scale 선택 시에만 사용합니다.')
        self.scale.setEnabled(False)
        self.zoom_mode.currentIndexChanged.connect(lambda index: self.scale.setEnabled(index == 2))
        row = QHBoxLayout()
        row.addWidget(self.zoom_mode, 1)
        row.addWidget(self.scale)
        navigate_layout.addLayout(row)
        self.shortcuts_status = QLabel('Alt+Left/Right/Home/End: active while the panel is visible.')
        self.shortcuts_status.setWordWrap(True)
        navigate_layout.addWidget(self.shortcuts_status)

        filter_group = QWidget()
        filter_group.setObjectName('filter_controls')
        filter_layout = QVBoxLayout(filter_group)
        filter_layout.setContentsMargins(0, 0, 0, 0)
        filter_layout.setSpacing(4)
        layout.addWidget(filter_group)
        self.filter_expression = QgsExpressionLineEdit()
        self.filter_expression.setExpressionDialogTitle('Build a navigation filter')
        self.filter_expression.setToolTip(
            'Filter expression — Enter a QGIS expression, then click refresh to apply and reload.\n'
            '필터 입력 — QGIS 표현식을 입력한 뒤 새로고침을 눌러 적용합니다. 예: "status" = \'review\'')
        for button in self.filter_expression.findChildren(QToolButton):
            button.setToolTip('Expression builder — Build a filter using layer fields, operators and values.\n표현식 작성기 — 레이어의 필드·연산자·값을 골라 필터 작성을 돕는 창을 엽니다.')
            button.setAccessibleName('Expression builder / 표현식 작성기')
        self.expression_button = self.filter_expression.findChild(QToolButton)
        row = QHBoxLayout()
        row.addWidget(self.filter_expression, 1)
        self.filter_refresh = QToolButton(self)
        self.filter_refresh.setIcon(QgsApplication.getThemeIcon('/mActionRefresh.svg'))
        self.filter_refresh.setAccessibleName('Apply filter and reload')
        self.filter_refresh.setToolTip('Apply filter and reload — Apply the entered expression and rebuild the navigation list.\n필터 적용·새로고침 — 입력한 표현식을 적용하고 탐색 목록을 다시 불러옵니다.')
        self.filter_refresh.clicked.connect(self.reload_features)
        row.addWidget(self.filter_refresh)
        self.filter_clear = QToolButton(self)
        self.filter_clear.setIcon(QgsApplication.getThemeIcon('/mActionDeleteSelected.svg'))
        self.filter_clear.setAccessibleName('Clear filter')
        self.filter_clear.setToolTip('Clear filter input — Empty the expression box. Click refresh to apply; do not delete features.\n필터 입력 지우기 — 표현식 입력칸만 비웁니다. 새로고침을 눌러야 목록에 적용되며 객체를 삭제하지 않습니다.')
        self.filter_clear.clicked.connect(self.clear_filter)
        row.addWidget(self.filter_clear)
        filter_layout.addLayout(row)
        self.selected_only = QCheckBox('Captured selection only')
        self.selected_only.setToolTip('Captured selection only — Navigate only the captured feature IDs; uncheck to remove this restriction.\n고정 선택만 탐색 — 체크하면 선택 객체 범위를 고정합니다. 이동해도 범위가 줄지 않으며, 해제하면 제한을 풉니다.')
        capture = QPushButton('Use current selection')
        self.capture_button = capture
        capture.setToolTip('Use current selection — Capture the currently selected feature IDs and enable the restricted scope.\n현재 선택 사용 — 현재 선택 객체를 새 탐색 범위로 고정하고 고정 선택만 탐색을 켭니다.')
        capture.clicked.connect(self.use_current_selection)
        row = QHBoxLayout()
        row.addWidget(self.selected_only)
        row.addWidget(capture)
        filter_layout.addLayout(row)
        self.scope_status = QLabel('Scope: all filtered features')
        self.scope_status.setWordWrap(True)
        filter_layout.addWidget(self.scope_status)
        layout.addWidget(navigate_group)

        edit_group = QWidget()
        edit_group.setObjectName('edit_controls')
        edit_layout = QVBoxLayout(edit_group)
        edit_layout.setContentsMargins(0, 0, 0, 0)
        edit_layout.setSpacing(4)
        layout.addWidget(edit_group)
        row = QHBoxLayout()
        presets = QPushButton('Field value presets...')
        self.presets_button = presets
        presets.setToolTip('Field value presets — Configure preset fields and values. Default keys are Alt+1–9; change bindings in shortcut settings.\n필드 값 설정 — 프리셋의 필드와 값을 지정합니다. 기본 키는 Alt+1~9이며 단축키 설정에서 변경할 수 있습니다.')
        presets.clicked.connect(plugin.configure)
        row.addWidget(presets, 1)
        self.columns_button = QToolButton(self)
        self.columns_button.setObjectName('column_visibility')
        self.columns_button.setIcon(QIcon(str(Path(__file__).with_name('visible_fields.svg'))))
        self.columns_button.setAccessibleName('Visible fields / 표시 필드')
        self.columns_button.setToolTip('Visible fields — Choose which columns to show or hide; confirmed columns remain editable.\n표시 필드 — 보일 컬럼과 숨길 컬럼을 선택합니다. 확인하면 선택한 컬럼만 표시하고 편집할 수 있습니다.')
        self.columns_button.clicked.connect(self.choose_current_fields)
        row.addWidget(self.columns_button)
        edit_layout.addLayout(row)
        self.immediate = QCheckBox('Apply presets immediately to layer edits')
        self.immediate.setChecked(plugin.immediate)
        self.immediate.toggled.connect(plugin.set_immediate)
        row = QHBoxLayout()
        row.addWidget(self.immediate, 1)
        self.save_button = QToolButton(self)
        self.save_button.setObjectName('save_feature_edits')
        self.save_button.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_DialogSaveButton))
        self.save_button.setAccessibleName('Save target layer / 대상 레이어 파일 저장')
        self.save_button.setToolTip('Save target layer — Apply draft fields and pending presets, then save ALL unsaved edits in the designated layer to its data source. Saved edits cannot be restored by feature Undo.\n대상 레이어 파일 저장 — 미적용 필드와 대기 프리셋을 반영한 뒤 지정 레이어의 모든 미저장 편집을 파일에 저장합니다. 다른 도구의 편집도 함께 저장하며 저장 후 객체 Undo로 되돌릴 수 없습니다.')
        self.save_button.setEnabled(False)
        self.save_button.clicked.connect(self.save_current_fields)
        row.addWidget(self.save_button)
        self.undo_button = QToolButton(self)
        self.undo_button.setObjectName('undo_edits')
        self.undo_button.setIcon(QgsApplication.getThemeIcon('/mActionUndo.svg'))
        self.undo_button.setAccessibleName('Undo / 실행 취소')
        self.undo_button.setToolTip('Feature Undo (Alt+Z) — Restore all consecutive Quick Field Keys edits to the last edited feature group, then select, zoom and flash it. Other tools\' edits are protected.\n객체 실행 취소 (Alt+Z) — 마지막 객체에 연속 입력한 이 플러그인의 변경을 함께 되돌린 뒤 선택·화면 이동·반짝임으로 표시합니다. 다른 도구의 편집은 보호합니다.')
        self.undo_button.setShortcut(QKeySequence('Alt+Z'))
        self.undo_button.clicked.connect(self.undo)
        row.addWidget(self.undo_button)
        self.settings_button = QToolButton(self)
        self.settings_button.setIcon(QIcon(str(Path(__file__).with_name('settings.svg'))))
        self.settings_button.setAccessibleName('Shortcut settings / 단축키 설정')
        self.settings_button.setToolTip('Shortcut settings — Change or assign this plugin\'s action keys. Empty means unassigned.\n단축키 설정 — 기능별 단축키를 변경하거나 지정합니다. 입력칸을 비우면 미지정 상태가 됩니다.')
        self.settings_button.clicked.connect(plugin.configure_shortcuts)
        row.addWidget(self.settings_button)
        edit_layout.addLayout(row)
        self.pending_status = QLabel()
        self.pending_status.setWordWrap(True)
        edit_layout.addWidget(self.pending_status)
        self.fields_layout = QVBoxLayout()
        self.fields_layout.setContentsMargins(0, 0, 0, 0)
        self.fields_layout.setSpacing(4)
        layout.addLayout(self.fields_layout)
        layout.addStretch(1)
        self.shortcuts = []
        for name, callback in (
            ('previous', lambda: self.step(-1)), ('next', lambda: self.step(1)),
            ('first', lambda: self.go_to(0)), ('last', lambda: self.go_to(len(self.ids) - 1)),
            ('lock_field', self.toggle_focused_lock),
            ('zoom', lambda: self.zoom_mode.setCurrentIndex((self.zoom_mode.currentIndex() + 1) % self.zoom_mode.count())),
            ('layer', self.layer_combo.showPopup), ('sort', self.sort_field.showPopup),
        ):
            shortcut = QShortcut(QKeySequence(plugin.shortcut_key(name)), self)
            shortcut.setObjectName(name)
            shortcut.setContext(Qt.ShortcutContext.ApplicationShortcut)
            shortcut.setAutoRepeat(False)
            shortcut.setEnabled(False)
            shortcut.activated.connect(callback)
            shortcut.activatedAmbiguously.connect(
                lambda: plugin.warn('Navigation shortcut conflict. Check other plugins and shortcuts.'))
            self.shortcuts.append(shortcut)
        self.binding_tooltips = {}
        self.update_bindings()
        self.visibilityChanged.connect(self.update_shortcuts)
        self.layer_combo.layerChanged.connect(self.change_layer)
        self.sort_field.currentIndexChanged.connect(self.reorder_features)
        self.ascending.toggled.connect(self.reorder_features)
        self.selected_only.toggled.connect(self.capture_selection)
        self.project.layersWillBeRemoved.connect(self.layers_removed)
        self.project.readProject.connect(self.project_loaded)
        self.dockLocationChanged.connect(self.save_layout)
        current = self.iface.activeLayer()
        if isinstance(current, QgsVectorLayer) and self.project.mapLayer(current.id()) is current:
            self.layer_combo.setLayer(current)
        self.change_layer(self.layer_combo.currentLayer())
        self.restore_session()
        self._restoring = False
        self._ready = True
        self.refresh_quick_status()

    def change_layer(self, layer):
        if self.inline_editor is not None and self.layer is not layer and not self.allow_field_navigation():
            self.layer_combo.blockSignals(True)
            self.layer_combo.setLayer(self.layer)
            self.layer_combo.blockSignals(False)
            return
        if self.layer is not None:
            self.disconnect_layer()
        self.layer = layer if isinstance(layer, QgsVectorLayer) else None
        self.selection_snapshot = None
        self.ids = []
        self.filtered_ids = []
        self.index = -1
        self.filter_expression.setLayer(self.layer)
        self.filter_expression.setExpression('')
        self.applied_filter = ''
        self.refresh_fields()
        if self.layer is not None:
            self.layer.selectionChanged.connect(self.selection_changed)
            self.layer.updatedFields.connect(self.refresh_fields)
            self.layer.featureAdded.connect(self.update_position)
            self.layer.featureDeleted.connect(self.update_position)
            for signal in ('layerModified', 'editingStopped', 'afterCommitChanges', 'afterRollBack'):
                getattr(self.layer, signal).connect(self.refresh_save_state)
        if self.selected_only.isChecked() and self.layer is not None:
            self.selection_snapshot = set(self.layer.selectedFeatureIds())
        self.reload_features()

    def refresh_fields(self, *args):
        sort = self.sort_field.currentData()
        self.sort_field.blockSignals(True)
        self.sort_field.clear()
        self.sort_field.addItem('(Feature ID)', '')
        if self.layer is not None:
            for field in self.layer.fields():
                self.sort_field.addItem(field.name(), field.name())
        self.sort_field.setCurrentIndex(max(0, self.sort_field.findData(sort)))
        self.sort_field.blockSignals(False)
        self.reorder_features()

    def reload_features(self, *args):
        self.update_shortcuts()
        self.scope_status.setText(
            f'Scope: {len(self.selection_snapshot or set())} captured feature IDs'
            if self.selected_only.isChecked() else 'Scope: all filtered features')
        self.scope_status.setVisible(self.selected_only.isChecked())
        if self.layer is None or not self.layer.isValid():
            self.ids = []
            self.index = -1
            self.update_position()
            return
        expression = self.filter_expression.expression().strip()
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
        self.filtered_ids = list(ids)
        if self.selected_only.isChecked():
            snapshot = self.selection_snapshot or set()
            ids = [fid for fid in ids if fid in snapshot]
        self.ids = ids
        self.applied_filter = expression
        selected = self.layer.selectedFeatureIds()
        current = previous if previous in ids else next((fid for fid in selected if fid in ids), None)
        self.index = ids.index(current) if current is not None else -1
        self.update_position()
        self.save_session()

    def reorder_features(self, *args):
        if self.layer is None or not self.layer.isValid():
            self.ids = []
            self.index = -1
            self.update_position()
            return
        previous = self.ids[self.index] if 0 <= self.index < len(self.ids) else None
        request = QgsFeatureRequest().setFilterFids(self.filtered_ids)
        name = self.sort_field.currentData()
        request.addOrderBy(QgsExpression.quotedColumnRef(name) if name else '$id', self.ascending.isChecked(), False)
        if name:
            request.addOrderBy('$id', True, False)
        ids = [feature.id() for feature in self.layer.getFeatures(request)] if self.filtered_ids else []
        if self.selected_only.isChecked():
            ids = [fid for fid in ids if fid in (self.selection_snapshot or set())]
        self.ids = ids
        selected = self.layer.selectedFeatureIds()
        current = previous if previous in ids else next((fid for fid in selected if fid in ids), None)
        self.index = ids.index(current) if current is not None else -1
        self.scope_status.setText(f'Scope: {len(self.selection_snapshot or set())} captured feature IDs')
        self.scope_status.setVisible(self.selected_only.isChecked())
        self.update_position()
        self.save_session()

    def capture_selection(self, *args):
        self.selection_snapshot = set(self.layer.selectedFeatureIds()) if self.layer is not None else set()
        self.reorder_features()

    def use_current_selection(self, *args):
        self.selection_snapshot = set(self.layer.selectedFeatureIds()) if self.layer is not None else set()
        self.selected_only.blockSignals(True)
        self.selected_only.setChecked(True)
        self.selected_only.blockSignals(False)
        self.reorder_features()

    def clear_filter(self, *args):
        self.filter_expression.setExpression('')
        self.update_position()

    def selection_changed(self, *args):
        if self._navigating or self.layer is None:
            return
        selected = self.layer.selectedFeatureIds()
        if len(selected) == 1 and selected[0] in self.ids:
            self.index = self.ids.index(selected[0])
        self.update_position()
        self.save_session()

    def step(self, direction):
        if not self.ids:
            return
        target = (0 if direction > 0 else len(self.ids) - 1) if self.index < 0 else self.index + direction
        self.go_to(target % len(self.ids))

    def go_to(self, index):
        if self.layer is None or not 0 <= index < len(self.ids):
            return
        feature = self.layer.getFeature(self.ids[index])
        if not feature.isValid():
            self.plugin.warn('The feature no longer exists. Reload the navigation list.')
            return
        if not self.allow_field_navigation():
            return
        self.remember_view()
        # Align the navigation target with the existing Alt+number target contract.
        self.iface.setActiveLayer(self.layer)
        self._navigating = True
        try:
            self.layer.selectByIds([feature.id()])
        finally:
            self._navigating = False
        self.index = index
        if self.zoom_mode.currentIndex() != 3 and feature.hasGeometry():
            self.zoom_to(feature)
        self.flash_selected()
        self.update_position()
        self.save_session()

    def flash_selected(self, *args, layer=None):
        target = layer if layer is not None else self.layer
        if target is None or not target.isValid():
            return
        ids = target.selectedFeatureIds()
        if not ids:
            return
        try:
            self.iface.mapCanvas().flashFeatureIds(target, ids)
        except Exception as error:
            self.plugin.warn(f'Feature flash failed / 객체 반짝임 실패: {error}')

    def remember_view(self):
        canvas = self.iface.mapCanvas()
        active = self.iface.activeLayer()
        layer = active if isinstance(active, QgsVectorLayer) else self.layer
        self.view_history.append((layer.id(), list(layer.selectedFeatureIds()),
                                  QgsRectangle(canvas.extent()), canvas.mapSettings().destinationCrs()))
        # ponytail: keep the last 100 in-session views; no project-wide history storage.
        del self.view_history[:-100]
        self.back_button.setEnabled(True)

    def back_view(self, *args):
        if not self.view_history:
            return
        layer_id, selected, extent, crs = self.view_history[-1]
        layer = self.project.mapLayer(layer_id)
        if not isinstance(layer, QgsVectorLayer) or not layer.isValid():
            self.view_history.pop()
            self.back_button.setEnabled(bool(self.view_history))
            self.plugin.warn('The previous view layer was removed.')
            return
        canvas = self.iface.mapCanvas()
        try:
            if crs != canvas.mapSettings().destinationCrs():
                extent = QgsCoordinateTransform(crs, canvas.mapSettings().destinationCrs(), self.project).transformBoundingBox(extent)
        except Exception as error:
            self.plugin.warn(f'Could not restore the previous view: {error}')
            return
        if not self.allow_field_navigation():
            return
        self.view_history.pop()
        self.back_button.setEnabled(bool(self.view_history))
        self.iface.setActiveLayer(layer)
        self._navigating = True
        try:
            layer.selectByIds([fid for fid in selected if layer.getFeature(fid).isValid()])
        finally:
            self._navigating = False
        if not extent.isNull():
            canvas.setExtent(extent)
            canvas.refresh()
        if layer is self.layer:
            self.index = next((self.ids.index(fid) for fid in selected if fid in self.ids), -1)
        else:
            self.index = -1
        self.update_position()
        self.save_session()

        self.flash_selected(layer=layer)

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

    def update_position(self, *args):
        self.flash_button.setEnabled(self.layer is not None and self.layer.isValid() and self.layer.selectedFeatureCount() > 0)
        self.sync_inline_fields()
        if not self.ids:
            self.position.setText('No matching features')
            return
        text = f'{self.index + 1 if self.index >= 0 else "-"} / {len(self.ids)}'
        if self.layer is not None:
            text += f' | selected: {self.layer.selectedFeatureCount()}'
            if 0 <= self.index < len(self.ids):
                feature = self.layer.getFeature(self.ids[self.index])
                if not feature.isValid():
                    self.position.setText(text + ' | removed feature; refresh the list')
                    return
                name = self.sort_field.currentData()
                if name and self.layer.fields().indexFromName(name) < 0:
                    name = ''
                value = feature[name] if name else feature.id()
                text += f' | {name or "FID"}: {value}'
        self.position.setText(text)

    def choose_current_fields(self, *args):
        if self.layer is None or not self.layer.isValid():
            self.plugin.warn('Choose a valid layer first.')
            return
        self.sync_inline_fields()
        if self.inline_editor is not None:
            self.inline_editor.choose_fields()

    def allow_field_navigation(self):
        editor = self.inline_editor
        if editor is not None and editor.has_form_edits():
            if not editor.confirm_discard_form():
                return False
            editor.load_rows()
        return True

    def save_current_fields(self, *args):
        layer = self.layer
        if layer is None or not layer.isValid() or layer.readOnly():
            self.plugin.warn('Choose a writable target layer. / 저장 가능한 대상 레이어를 지정하세요.')
            return False
        if self.plugin.pending_changes and self.plugin.pending_layer is not layer:
            self.plugin.warn('Pending presets belong to another layer. Apply or discard them first. / 다른 레이어의 대기 프리셋을 먼저 적용하거나 폐기하세요.')
            return False
        changes = dict(self.plugin.pending_changes)
        editor = self.inline_editor
        if editor is not None and editor.layer is layer:
            changes.update(editor.form_changes())
        if changes:
            if not self.plugin.apply_changes(layer, changes, 'Apply drafts before file save'):
                return False
            self.plugin.discard_pending()
            editor.load_rows()
        if not layer.isEditable() or not layer.isModified():
            self.refresh_save_state()
            return False
        if not layer.commitChanges(False):
            self.plugin.warn('File save failed; edits remain available. / 파일 저장 실패. 편집을 유지합니다.\n' + '\n'.join(layer.commitErrors()))
            self.refresh_save_state()
            return False
        self.plugin.clear_feature_history(layer.id())
        self.update_position()
        self.plugin.iface.messageBar().pushSuccess('Quick Field Keys', f'{layer.name()}: saved all layer edits. / 레이어의 모든 편집을 파일에 저장했습니다.')
        return True

    def refresh_save_state(self, *args):
        layer = self.layer
        editor = self.inline_editor
        try:
            valid = layer is not None and layer.isValid() and not layer.readOnly()
            pending = bool(self.plugin.pending_changes) and self.plugin.pending_layer is layer
            draft = editor is not None and editor.layer is layer and editor.has_form_edits()
            enabled = valid and (draft or pending or (layer.isEditable() and layer.isModified()))
        except RuntimeError:
            enabled = False
        self.save_button.setEnabled(bool(enabled))

    def sync_inline_fields(self):
        editor = self.inline_editor
        if self.layer is None or not self.layer.isValid():
            self.save_button.setEnabled(False)
            if editor is not None:
                editor.hide()
                self.fields_layout.removeWidget(editor)
                editor.deleteLater()
                self.inline_editor = None
            return
        if editor is None or editor.layer is not self.layer:
            if editor is not None:
                editor.hide()
                self.fields_layout.removeWidget(editor)
                editor.deleteLater()
            from .field_editor import FieldEditor
            editor = FieldEditor(self.plugin, self.layer, embedded=True, parent=self, save_button=self.save_button)
            self.inline_editor = editor
            self.fields_layout.addWidget(editor)
        selected = list(self.layer.selectedFeatureIds())
        if editor.has_form_edits():
            editor.scope.setText('Unapplied field edits keep their original selection. Apply or Undo before retargeting.\n미적용 필드 편집은 원래 대상을 유지합니다. 적용 또는 Undo 후 이동하세요.')
            editor.scope.setVisible(set(editor.ids) != set(selected))
            return
        editor.ids = selected
        editor.scope.hide()
        editor.load_rows()
        self.refresh_save_state()

    def update_shortcuts(self, *args):
        import qgis.utils
        conflict = 'featurenaved' in qgis.utils.plugins
        for shortcut in self.shortcuts:
            shortcut.setEnabled(self.isVisible() and not shortcut.key().isEmpty()
                                and (not conflict or shortcut.objectName() not in ('previous', 'next', 'first', 'last')))
        self.shortcuts_status.setText(
            'Navigation shortcuts paused: disable FeatureNavEd to avoid conflicts.' if conflict
            else 'Navigation shortcuts: ' + ', '.join(self.plugin.shortcut_key(name) or 'unassigned' for name in ('previous', 'next', 'first', 'last')))
        self.shortcuts_status.setVisible(conflict)
        self.position.setToolTip(self.shortcuts_status.text())

    def update_bindings(self):
        from .shortcuts import ACTIONS
        buttons = {
            'first': self.navigation_buttons['first_feature'], 'previous': self.navigation_buttons['previous_feature'],
            'next': self.navigation_buttons['next_feature'], 'last': self.navigation_buttons['last_feature'],
            'back': self.back_button, 'undo': self.undo_button, 'presets': self.presets_button,
            'columns': self.columns_button, 'refresh': self.filter_refresh, 'clear': self.filter_clear,
            'capture': self.capture_button, 'scope': self.selected_only, 'settings': self.settings_button,
            'immediate': self.immediate, 'expression': self.expression_button,
            'save_feature': self.save_button,
            'flash': self.flash_button,
        }
        for shortcut in self.shortcuts:
            shortcut.setKey(QKeySequence(self.plugin.shortcut_key(shortcut.objectName())))
        for name, button in buttons.items():
            base = self.binding_tooltips.setdefault(name, button.toolTip())
            key = self.plugin.shortcut_key(name)
            default = ACTIONS[name][1]
            button.setToolTip(base.replace(default, key or 'unassigned / 미지정') if default else
                              base + '\nShortcut / 단축키: ' + (key or 'unassigned / 미지정'))
            # Navigation uses the existing application shortcuts, not duplicate button bindings.
            if name not in ('first', 'previous', 'next', 'last'):
                button.setShortcut(QKeySequence(key))
        if self.inline_editor is not None:
            self.inline_editor.save_button.setShortcut(QKeySequence(self.plugin.shortcut_key('save_feature')))
        self.update_shortcuts()

    def toggle_focused_lock(self):
        focus = QApplication.focusWidget()
        if self.inline_editor is not None and focus is not None:
            for wrapper, lock in self.inline_editor.rows.values():
                if focus is lock or focus is wrapper.widget() or wrapper.widget().isAncestorOf(focus):
                    lock.click()
                    return
        self.plugin.warn('Focus a field input or its lock button first. / 먼저 필드 입력칸이나 잠금 버튼에 포커스를 두세요.')

    def refresh_quick_status(self):
        self.immediate.blockSignals(True)
        self.immediate.setChecked(self.plugin.immediate)
        self.immediate.blockSignals(False)
        self.pending_status.setText(f'Pending changes: {len(self.plugin.pending_changes)}. Apply / discard from the plugin menu; file save remains manual.')
        self.pending_status.setVisible(bool(self.plugin.pending_changes))
        self.immediate.setToolTip('Immediate preset application — On: apply preset shortcuts to the edit buffer. Off: stage until Apply pending shortcuts in the plugin menu. File save remains manual.\n프리셋 즉시 적용 — 켜면 지정한 단축키를 편집 버퍼에 적용합니다. 끄면 대기값으로 보관하며 플러그인 메뉴에서 적용·폐기합니다. 실제 파일 저장은 별도입니다.')
        self.update_position()

    def undo(self, *args):
        if not self.allow_field_navigation():
            return
        self.plugin.undo_edit(self.layer)
        self.update_position()

    def reveal_undone(self, layer, targets):
        if self.layer is not None and self.layer.isValid():
            self.remember_view()
        if self.layer is not layer:
            self.layer_combo.setLayer(layer)
        self.iface.setActiveLayer(layer)
        self._navigating = True
        try:
            layer.selectByIds(list(targets))
        finally:
            self._navigating = False
        self.index = next((self.ids.index(fid) for fid in targets if fid in self.ids), -1)
        self.update_position()
        canvas = self.iface.mapCanvas()
        canvas.zoomToSelected(layer)
        canvas.flashFeatureIds(layer, list(targets))

    def layers_removed(self, ids):
        if self.layer is not None and self.layer.id() in ids:
            self.layer_combo.setLayer(None)

    def shutdown(self):
        self.save_session()
        self.save_layout()
        for shortcut in self.shortcuts:
            shortcut.setEnabled(False)
        if self.layer is not None:
            self.disconnect_layer()
        try:
            self.project.layersWillBeRemoved.disconnect(self.layers_removed)
        except (TypeError, RuntimeError):
            pass
        try:
            self.project.readProject.disconnect(self.project_loaded)
        except (TypeError, RuntimeError):
            pass

    def disconnect_layer(self):
        for name, callback in (
            ('selectionChanged', self.selection_changed), ('updatedFields', self.refresh_fields),
            ('featureAdded', self.update_position), ('featureDeleted', self.update_position),
            ('layerModified', self.refresh_save_state), ('editingStopped', self.refresh_save_state),
            ('afterCommitChanges', self.refresh_save_state), ('afterRollBack', self.refresh_save_state),
        ):
            try:
                getattr(self.layer, name).disconnect(callback)
            except (TypeError, RuntimeError):
                pass

    @staticmethod
    def read_state(key):
        try:
            state = json.loads(QgsSettings().value(key, '{}'))
            return state if isinstance(state, dict) else {}
        except (TypeError, ValueError):
            return {}

    def session_key(self):
        path = self.project.absoluteFilePath() or self.project.fileName()
        identity = os.path.normcase(os.path.abspath(path)) if path else '__unsaved_project__'
        return 'quick_field_keys/navigator/sessions/' + hashlib.sha256(identity.encode('utf-8')).hexdigest()

    @staticmethod
    def source_hash(layer):
        return hashlib.sha256((layer.providerType() + '\n' + layer.source()).encode('utf-8')).hexdigest()

    def save_session(self, *args):
        if not self._ready or self._restoring or self.layer is None:
            return
        if self.session_key() != self._session_key:
            # Do not overwrite another project's saved state during project loading.
            return
        try:
            if self.project.mapLayer(self.layer.id()) is not self.layer:
                return
            current = self.ids[self.index] if 0 <= self.index < len(self.ids) else None
            state = {
                'layer_id': self.layer.id(), 'layer_name': self.layer.name(),
                'source_hash': self.source_hash(self.layer), 'filter': self.applied_filter,
                'sort_field': self.sort_field.currentData(), 'ascending': self.ascending.isChecked(),
                'feature_id': current, 'index': self.index,
                'selection': self.layer.selectedFeatureIds(),
                'selected_only': self.selected_only.isChecked(),
                'selection_snapshot': sorted(self.selection_snapshot or set()),
                'zoom_mode': self.zoom_mode.currentIndex(),
                'scale': self.scale.value(),
            }
        except RuntimeError:
            return
        QgsSettings().setValue(self._session_key, json.dumps(state, ensure_ascii=False))

    def restore_session(self):
        self._session_key = self.session_key()
        state = self.read_state(self._session_key)
        if not state:
            return False
        layer = self.project.mapLayer(state.get('layer_id', ''))
        if not isinstance(layer, QgsVectorLayer) or self.source_hash(layer) != state.get('source_hash'):
            matches = [candidate for candidate in self.project.mapLayers().values()
                       if isinstance(candidate, QgsVectorLayer)
                       and candidate.name() == state.get('layer_name')
                       and self.source_hash(candidate) == state.get('source_hash')]
            layer = matches[0] if len(matches) == 1 else None
        if layer is None:
            return False
        previous = self._restoring
        self._restoring = True
        try:
            self.layer_combo.blockSignals(True)
            self.layer_combo.setLayer(layer)
            self.layer_combo.blockSignals(False)
            self.change_layer(layer)
            for combo, name in ((self.sort_field, state.get('sort_field')),):
                combo.blockSignals(True)
                combo.setCurrentIndex(max(0, combo.findData(name)))
                combo.blockSignals(False)
            self.ascending.blockSignals(True)
            self.ascending.setChecked(bool(state.get('ascending', True)))
            self.ascending.blockSignals(False)
            expression = state.get('filter', '')
            if not isinstance(expression, str) or QgsExpression(expression).hasParserError():
                expression = ''
            self.filter_expression.setExpression(expression)
            self.selected_only.blockSignals(True)
            self.selected_only.setChecked(bool(state.get('selected_only', False)))
            self.selected_only.blockSignals(False)
            snapshot = state.get('selection_snapshot', [])
            self.selection_snapshot = {fid for fid in snapshot if isinstance(fid, int)} if isinstance(snapshot, list) else set()
            mode = state.get('zoom_mode', 0)
            # Migrate the old checkbox state without losing the user's no-zoom choice.
            if state.get('auto_zoom') is False:
                mode = 3
            self.zoom_mode.setCurrentIndex(mode if isinstance(mode, int) and 0 <= mode <= 3 else 0)
            scale = state.get('scale', 1000)
            self.scale.setValue(scale if isinstance(scale, (int, float)) and 1 <= scale <= 100000000 else 1000)
            self.reload_features()
            fid = state.get('feature_id')
            index = state.get('index', -1)
            if fid in self.ids:
                self.index = self.ids.index(fid)
            elif isinstance(index, int) and index >= 0 and self.ids:
                self.index = min(index, len(self.ids) - 1)
            else:
                self.index = -1
            self.update_position()
            self._restored_selection = state.get('selection', [])
            return True
        finally:
            self._restoring = previous

    def restore_on_open(self):
        if self.session_key() != self._session_key:
            self.restore_session()
        if self.layer is None or not self.layer.isValid():
            return
        selected = getattr(self, '_restored_selection', None)
        self._restored_selection = None
        if isinstance(selected, list) and len(selected) > 1:
            selected = [fid for fid in selected if isinstance(fid, int) and self.layer.getFeature(fid).isValid()]
            self.iface.setActiveLayer(self.layer)
            self._navigating = True
            try:
                self.layer.selectByIds(selected)
            finally:
                self._navigating = False
            if self.zoom_mode.currentIndex() != 3 and 0 <= self.index < len(self.ids):
                self.zoom_to(self.layer.getFeature(self.ids[self.index]))
            self.update_position()
        elif 0 <= self.index < len(self.ids):
            self.go_to(self.index)

    def project_loaded(self, *args):
        self.restore_session()
        if self.isVisible():
            self.restore_on_open()

    def preferred_dock_area(self):
        right = Qt.DockWidgetArea.RightDockWidgetArea
        value = self._layout_state.get('area', getattr(right, 'value', right))
        allowed = (Qt.DockWidgetArea.LeftDockWidgetArea, Qt.DockWidgetArea.RightDockWidgetArea,
                   Qt.DockWidgetArea.TopDockWidgetArea, Qt.DockWidgetArea.BottomDockWidgetArea)
        return next((area for area in allowed if getattr(area, 'value', area) == value), right)

    def restore_layout(self):
        previous = self._restoring
        self._restoring = True
        try:
            self.setFloating(bool(self._layout_state.get('floating', False)))
            geometry = self._layout_state.get('geometry')
            if isinstance(geometry, str):
                self.restoreGeometry(QByteArray.fromBase64(geometry.encode('ascii', errors='ignore')))
        finally:
            self._restoring = previous
            self._layout_restored = True

    def save_layout(self, *args):
        if not self._ready or self._restoring or not self._layout_restored:
            return
        area = self.iface.mainWindow().dockWidgetArea(self)
        if area == Qt.DockWidgetArea.NoDockWidgetArea:
            area = self.preferred_dock_area()
        state = {
            'area': getattr(area, 'value', area),
            'floating': self.isFloating(),
            'geometry': bytes(self.saveGeometry().toBase64()).decode('ascii'),
        }
        self._layout_state = state
        QgsSettings().setValue('quick_field_keys/navigator/layout', json.dumps(state))

    def hideEvent(self, event):
        self.save_session()
        self.save_layout()
        super().hideEvent(event)

    def moveEvent(self, event):
        super().moveEvent(event)
        if hasattr(self, '_ready'):
            self.save_layout()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if hasattr(self, '_ready'):
            self.save_layout()
