"""Run Python-only regressions with python-qgis.bat tests/run_python_qgis.py."""
import os
import ctypes
from pathlib import Path
import sys
import tempfile


native_attempts: list[str] = []


def guard_qfk_native(event: str, args) -> None:
    if event not in ('import', 'ctypes.dlopen'):
        return
    name = str(args[0]).replace('\\', '/').lower()
    if '_qfk_actions' in name or 'qfk_rust_core' in name:
        native_attempts.append(name)
        raise RuntimeError(f'QFK native loading forbidden: {name}')


# Installed before QGIS or plugin imports, including tests' alias packages.
sys.addaudithook(guard_qfk_native)
original_cdll_init = ctypes.CDLL.__init__


def guarded_cdll_init(self, name, *args, **kwargs) -> None:
    guard_qfk_native('ctypes.dlopen', (name,))
    original_cdll_init(self, name, *args, **kwargs)


# PyDLL inherits this initializer; handle-based reuse emits no dlopen audit event.
ctypes.CDLL.__init__ = guarded_cdll_init
sys.dont_write_bytecode = True
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
with tempfile.TemporaryDirectory(prefix='qfk_python_profile_', ignore_cleanup_errors=True) as profile:
    os.environ['QGIS_CUSTOM_CONFIG_PATH'] = profile
    from qgis.core import Qgis, QgsApplication
    from qgis.PyQt.QtCore import QT_VERSION_STR, PYQT_VERSION_STR
    app = QgsApplication([], True, profile)
    app.initQgis()
    from qgis.gui import QgsGui
    QgsGui.editorWidgetRegistry().initEditors()
    print(f'Runtime: QGIS {Qgis.QGIS_VERSION}; Qt {QT_VERSION_STR}; PyQt {PYQT_VERSION_STR}', flush=True)
    for name in (sys.argv[1:] or ('test_qgis.py', 'test_navigation.py', 'test_optimization.py', 'test_bulk_reads.py')):
        test = Path(__file__).with_name(name)
        namespace = {'__file__': str(test), 'test_persistent_save': True}
        exec(compile(test.read_text(encoding='utf-8'), str(test), 'exec'), namespace)
        app.processEvents()
        print(f'PASS: {name}', flush=True)
    assert not native_attempts, native_attempts
    print('PASS: Python-only QGIS scripts; zero QFK native load attempts', flush=True)
