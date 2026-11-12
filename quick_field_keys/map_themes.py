"""Cycle saved map themes while retaining the designated editing layer."""
from typing import TYPE_CHECKING

from qgis.core import QgsMapThemeCollection

if TYPE_CHECKING:
    from .navigation import QuickFieldNavigator


class MapThemeSwitcher:
    def __init__(self, navigator: 'QuickFieldNavigator') -> None:
        self.navigator = navigator
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
        matches = [name for name in names if themes.mapThemeState(name) == state]
        current = self.current_name if self.current_name in matches else next(iter(matches), None)
        index = names.index(current) if current is not None else (-1 if direction > 0 else 0)
        name = names[(index + direction) % len(names)]
        themes.applyTheme(name, root, model)
        self.current_name = name
        nav.iface.mapCanvas().refresh()
        nav.iface.messageBar().pushSuccess('Quick Field Keys', f'Map theme / 지도 테마: {name}')
