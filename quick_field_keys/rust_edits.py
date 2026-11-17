"""SPDX-License-Identifier: GPL-3.0-or-later

Edit-validation outcomes from QGIS state and values.
"""
from enum import IntEnum
from typing import TypeVar, assert_never

from qgis.core import QgsMapLayer, QgsVariantUtils, QgsVectorLayer


class Phase(IntEnum):
    TARGET = 0
    CHANGES = 1
    FIELD = 2
    VERIFY = 3
    NULL = 4
    CONVERSION = 5


class Decision(IntEnum):
    PROCEED = 0
    UNAVAILABLE = 1
    EMPTY = 2
    LOCKED = 3
    INVALID_TARGET = 4
    VERIFY_FAILED = 5
    INVALID_PHASE = 6
    USE_NULL = 7
    REJECT_CONVERSION = 8


T = TypeVar('T')


def check(phase: Phase, flags: int) -> Decision:
    match phase:
        case Phase.TARGET:
            return Decision.PROCEED if flags & 3 == 3 and flags & 4 == 0 else Decision.UNAVAILABLE
        case Phase.CHANGES:
            return Decision.PROCEED if flags else Decision.EMPTY
        case Phase.FIELD:
            if flags & 1:
                return Decision.LOCKED
            return Decision.PROCEED if flags & 6 == 6 else Decision.INVALID_TARGET
        case Phase.VERIFY:
            agrees = bool(flags & 2) if flags & 1 else not bool(flags & 4)
            return Decision.PROCEED if agrees else Decision.VERIFY_FAILED
        case Phase.NULL:
            return Decision.USE_NULL if flags else Decision.PROCEED
        case Phase.CONVERSION:
            return Decision.REJECT_CONVERSION if flags & 1 and not flags & 2 else Decision.PROCEED
        case unreachable:
            assert_never(unreachable)


def null_mode(value: T) -> Decision:
    return check(Phase.NULL, int(bool(value)))


def conversion(legacy: bool, success: bool) -> Decision:
    return check(Phase.CONVERSION, int(legacy) | (int(success) << 1))


def target(layer: QgsMapLayer | None) -> Decision:
    flags = 0
    try:
        match layer:
            case QgsVectorLayer():
                flags = 1 | (int(layer.isValid()) << 1)
                if flags & 2:
                    flags |= int(layer.readOnly()) << 2
            case QgsMapLayer() | None:
                flags = 0
            case unreachable:
                assert_never(unreachable)
    except RuntimeError:
        flags = 0
    return check(Phase.TARGET, flags)


def lock(locked: bool) -> Decision:
    return check(Phase.FIELD, int(locked) | 6)


def field_access(writable: bool, present: bool) -> Decision:
    return check(Phase.FIELD, (int(writable) << 1) | (int(present) << 2))


def verification(expected: T, actual: T) -> Decision:
    """Preserve QGIS NULL observations and the original non-NULL comparison."""
    null = QgsVariantUtils.isNull(expected)
    flags = int(null)
    if null:
        flags |= int(QgsVariantUtils.isNull(actual)) << 1
    else:
        flags |= int(bool(actual != expected)) << 2
    return check(Phase.VERIFY, flags)
