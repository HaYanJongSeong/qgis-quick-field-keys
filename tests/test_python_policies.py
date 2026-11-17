"""Python policy edge cases, run through run_python_qgis.py."""
import hashlib
from importlib import import_module
import json
from pathlib import Path
import sys
from types import SimpleNamespace

from qgis.core import NULL, QgsFeature, QgsVariantUtils, QgsVectorLayer
from qgis.gui import QgsMapCanvas
from qgis.PyQt.QtWidgets import QToolButton

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
core, drafts, identity, presets, edits, save, session, store, themes, view, shortcuts = (
    import_module('quick_field_keys.rust_' + name)
    for name in ('core', 'drafts', 'identity', 'presets', 'edits', 'save',
                 'session', 'store', 'themes', 'view', 'shortcuts'))

# Given real selected features, staging must preserve the edit buffer and targets.
layer = QgsVectorLayer('Point?field=status:string', 'Pending values', 'memory')
feature = QgsFeature(layer.fields())
feature.setAttributes(['original'])
assert layer.dataProvider().addFeatures([feature])[0]
fid = next(layer.getFeatures()).id()
layer.selectByIds([fid])
active = [layer]
messages = []
canvas = QgsMapCanvas()
bar = SimpleNamespace(pushWarning=lambda *args: messages.append(args),
                      pushSuccess=lambda *args: messages.append(args))
iface = SimpleNamespace(activeLayer=lambda: active[0], messageBar=lambda: bar,
                        setActiveLayer=lambda value: active.__setitem__(0, value),
                        mapCanvas=lambda: canvas)
plugin_module = import_module('quick_field_keys.plugin')
plugin = plugin_module.QuickFieldKeys(iface)
plugin.immediate = False
plugin.presets = {'1': {'field': 'status', 'null': True},
                  '2': {'field': 'status', 'value': 'second'}}
plugin.apply('1')
plugin.apply('2')
assert plugin.pending_changes == {(fid, 'status'): 'second'}
assert layer.getFeature(fid)['status'] == 'original' and not layer.isEditable()
assert plugin.undo_edit(layer)
assert not plugin.pending_changes and not plugin.pending_targets
assert layer.getFeature(fid)['status'] == 'original'
plugin.apply('1')
other = QgsVectorLayer('Point?field=status:string', 'Other target', 'memory')
feature = QgsFeature(other.fields())
feature.setAttributes(['untouched'])
assert other.dataProvider().addFeatures([feature])[0]
other.selectByIds([next(other.getFeatures()).id()])
active[0] = other
plugin.apply('2')
assert plugin.pending_layer is layer and plugin.pending_changes == {(fid, 'status'): None}
assert next(other.getFeatures())['status'] == 'untouched'
assert plugin.apply_pending()
assert QgsVariantUtils.isNull(layer.getFeature(fid)['status'])
assert next(layer.dataProvider().getFeatures())['status'] == 'original'
assert not plugin.pending_changes and not plugin.pending_undo and plugin.pending_layer is None
layer.rollBack()
plugin.unload()
print('PASS: staged NULL/repeated targets, grouped Undo, foreign-layer rejection, apply without file save', flush=True)

assert core.same_value(NULL, None)
assert core.same_value(0, False)
assert not core.same_value(0, None)
assert core.same_value(2 ** 100, 2 ** 100)
assert not core.same_value(float('nan'), float('nan'))
assert core.navigation_step(-1, -1, 4) == 3
assert core.navigation_step(3, 1, 4) == 0
assert core.navigation_step(0, 1, 0) is None
assert core.locked_names('["status", 1, null]') == {'status'}
assert core.locked_names('{"status": true}') == set()
assert core.locked_names('broken') == set()
print('PASS: NULL, zero, unbounded integers, empty navigation, malformed locks', flush=True)

assert identity.same_text('a\0b', 'a\0b')
assert not identity.same_text('1', 1)
assert identity.source_hash('memory', '한글\0source') == hashlib.sha256('memory\n한글\0source'.encode()).hexdigest()
assert identity.session_key('') == 'quick_field_keys/navigator/sessions/' + hashlib.sha256(b'__unsaved_project__').hexdigest()
capture = store.SessionCapture('id', '한글', 'hash', '', None, True, [9, 4], -1,
                               [4], False, [9, 4, 9], 3, 1000)
state = json.loads(store.serialize(capture))
assert state['feature_id'] is None and state['selection_snapshot'] == [4, 9]
assert state['layer_name'] == '한글' and state['selection'] == [4]
assert session.layer_index([7, 7]) == -1
assert session.restore_index([], (99, 100)) == -1
assert session.restore_index([9, 4], (4, 0)) == 1
assert session.restore_index([9, 4], (99, 100)) == 1
assert session.zoom_mode(0, False) == 3
assert session.scale(10 ** 1000) == 1000
assert view.choose([9, 4], {4}, (9, [4])) == ([4], 0)
assert view.choose([], None, (9, [])) == ([], -1)
assert themes.theme_index(1, -1, []) is None
assert themes.theme_index(-1, -1, [False, False]) == 1
print('PASS: exact identities, Unicode session schema, stale/ambiguous/empty restoration', flush=True)

locked = QToolButton()
locked.setCheckable(True)
locked.setChecked(True)
unlocked = QToolButton()
rows = {'status': (None, unlocked), 'note': (None, locked)}
assert drafts.refresh_fields([1, 2], rows, ({(1, 'status'): 'preset'}, {'status'})) == set()
assert drafts.refresh_fields([1, 2], rows, ({(1, 'status'): 'a', (2, 'status'): 'b'}, {'status'})) == {'status'}
assert drafts.applicable_fields(rows, {'status', 'note'}) == ['status']
assert not drafts.dirty(True, True) and drafts.dirty(False, True)
assert presets.lock(True) is presets.Decision.LOCKED
assert edits.target(None) is edits.Decision.UNAVAILABLE
assert edits.verification(None, NULL) is edits.Decision.PROCEED
assert edits.verification('expected', 'other') is edits.Decision.VERIFY_FAILED
assert not save.save_enabled(0) and not save.save_enabled(24)
assert save.save_enabled(1 | 2) and save.save_enabled(1 | 4)
assert not save.save_enabled(1 | 8) and save.save_enabled(1 | 8 | 16)
with shortcuts.ShortcutGuard() as guard:
    assert guard.check('Alt+1', 'first') is None
    assert guard.check('Alt+1', 'second') == 'first'
    assert guard.check('Alt+1', 'third') == 'first'
with shortcuts.ShortcutGuard() as guard:
    assert guard.check('Alt+1', 'fresh') is None
print('PASS: partial-draft protection, locks, rejection policies, save guards, duplicate shortcut ownership', flush=True)
