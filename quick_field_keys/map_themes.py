"""Cycle saved map themes while retaining the designated editing layer."""
from typing import TYPE_CHECKING
import sys
from .rust_themes import theme_index

from qgis.core import QgsMapThemeCollection

if TYPE_CHECKING:
    from .navigation import QuickFieldNavigator


class MapThemeSwitcher:
    def __init__(self, navigator: 'QuickFieldNavigator') -> None:
        self.navigator = navigator
        self._theme_module = sys.modules[__name__]
        self.current_name: str | None = None

    def step(self, direction: int) -> None:
        nav = self.navigator
        if nav.layer is None or not nav.layer.isValid():
            nav.plugin.warn('Choose a target layer first. / 먼저 대상 레이어를 지정하세요.')
            return
        themes = nav.project.mapThemeCollection()
        names = themes.mapThemes()
        if not names:
            nav.plugin.warn('No map themes. Add one in the Layers panel. / 레이어 패널에서 지도 테마를 먼저 추가하세요.')
            return
        root = nav.project.layerTreeRoot()
        model = nav.iface.layerTreeView().layerTreeModel()
        state = QgsMapThemeCollection.createThemeFromCurrentState(root, model)
        matches = [themes.mapThemeState(name) == state for name in names]
        current = names.index(self.current_name) if self.current_name in names else -1
        name = names[theme_index(direction, current, matches)]
        themes.applyTheme(name, root, model)
        self.current_name = name
        nav.iface.mapCanvas().refresh()
        nav.iface.messageBar().pushSuccess('Quick Field Keys', f'Map theme / 지도 테마: {name}')
