"""SPDX-License-Identifier: GPL-3.0-or-later

Python value logic; native dispatch remains disabled.
"""
import json

from qgis.core import QgsFields, QgsVariantUtils

_ORIGIN_PROVIDER = QgsFields.FieldOrigin.OriginProvider
_ORIGIN_EDIT = QgsFields.FieldOrigin.OriginEdit




def navigation_step(index, direction, count):
    if count == 0:
        return None
    target = (0 if direction > 0 else count - 1) if index < 0 else index + direction
    return target % count


def shortcut_safe(function_key, modifiers, safe_bits):
    return function_key or bool(modifiers & safe_bits)


def history_compatible(previous, context, before):
    layer, targets = context
    present = previous is not None
    same_layer = present and previous['layer'] is layer
    same_targets = present and previous['targets'] == targets
    return (present and same_layer and same_targets
            and all(same_value(before[key] if key in before
                               else layer.getFeature(key[0])[key[1]], expected)
                    for key, expected in previous['after'].items()))


def same_value(left, right):
    return _python_same_value(left, right)


def _python_same_value(left, right):
    return (QgsVariantUtils.isNull(left) and QgsVariantUtils.isNull(right)) or left == right


def writable_indices(fields, primary):
    return _python_writable_indices(fields, primary)


def _python_writable_indices(fields, primary):
    primary = set(primary)
    return [i for i in range(len(fields))
            if fields.fieldOrigin(i) in (_ORIGIN_PROVIDER, _ORIGIN_EDIT)
            and not (fields.fieldOrigin(i) == _ORIGIN_PROVIDER
                      and fields.fieldOriginIndex(i) in primary)]


def locked_names(raw):
    return _python_locked_names(raw)


def _python_locked_names(raw):
    try:
        names = json.loads(raw)
        return set(name for name in names if isinstance(name, str)) if isinstance(names, list) else set()
    except (TypeError, ValueError):
        return set()
