"""Run isolated regression tests with the selected QGIS Python environment."""
import os
from pathlib import Path
import tempfile

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
with tempfile.TemporaryDirectory(prefix='qfk_test_profile_', ignore_cleanup_errors=True) as profile:
    os.environ['QGIS_CUSTOM_CONFIG_PATH'] = profile
    from qgis.core import Qgis, QgsApplication
    from qgis.PyQt.QtCore import QT_VERSION_STR, PYQT_VERSION_STR
    app = QgsApplication([], True, profile)
    app.initQgis()
    from qgis.gui import QgsGui
    QgsGui.editorWidgetRegistry().initEditors()
    print(f'Runtime: QGIS {Qgis.QGIS_VERSION}; Qt {QT_VERSION_STR}; PyQt {PYQT_VERSION_STR}', flush=True)
    for name in ('test_qgis.py', 'test_navigation.py'):
        test = Path(__file__).with_name(name)
        namespace = {'__file__': str(test), 'test_persistent_save': True}
        exec(compile(test.read_text(encoding='utf-8'), str(test), 'exec'), namespace)
        app.processEvents()
    print('PASS: both isolated QGIS regression scripts', flush=True)
