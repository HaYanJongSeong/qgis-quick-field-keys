"""SPDX-License-Identifier: GPL-3.0-or-later

Preset validation decisions and priority.
"""
from enum import IntEnum
from typing import assert_never

from .rust_identity import SavedValue


class Phase(IntEnum):
    SELECTION = 0
    CONFIGURATION = 1
    FIELD = 2


class Decision(IntEnum):
    PROCEED = 0
    NO_SELECTION = 1
    CONFIGURE = 2
    LOCKED = 3
    UNWRITABLE = 4
    INVALID_PHASE = 5


def check(phase: Phase, observations: int) -> Decision:
    match phase:
        case Phase.SELECTION:
            return Decision.PROCEED if observations else Decision.NO_SELECTION
        case Phase.CONFIGURATION:
            return Decision.PROCEED if observations & 3 == 3 else Decision.CONFIGURE
        case Phase.FIELD:
            if observations & 1:
                return Decision.LOCKED
            return Decision.PROCEED if observations & 6 == 6 else Decision.UNWRITABLE
        case unreachable:
            assert_never(unreachable)


def configuration(preset: SavedValue) -> Decision:
    """Observe JSON shape and field truth without selecting the resulting action."""
    match preset:
        case dict():
            flags = 1 | (int(bool(preset.get('field'))) << 1)
        case None | str() | int() | float() | list():
            flags = 0
        case unreachable:
            assert_never(unreachable)
    return check(Phase.CONFIGURATION, flags)


def lock(locked: bool) -> Decision:
    """Check the lock before querying field editability, as the original did."""
    return check(Phase.FIELD, int(locked) | 6)


def field_access(exists: bool, writable: bool) -> Decision:
    return check(Phase.FIELD, (int(exists) << 1) | (int(writable) << 2))
