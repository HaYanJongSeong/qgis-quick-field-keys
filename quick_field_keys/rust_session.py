"""SPDX-License-Identifier: GPL-3.0-or-later

Restoration policies for saved navigator settings.
"""
from enum import IntFlag



class OpenAction(IntFlag):
    NONE = 0
    MULTI = 1
    GO = 2
    ZOOM = 4


def open_action(count: int, focused: bool, zoom_mode: int) -> OpenAction:
    """Use the raw selection count, before filtering stale or invalid IDs."""
    if count > 1:
        return OpenAction.MULTI | (OpenAction.ZOOM if focused and zoom_mode != 3 else OpenAction.NONE)
    return OpenAction.GO if focused else OpenAction.NONE


def selection_candidate(integer: bool, present: bool) -> bool:
    return integer and present


def direct_layer(flags: int) -> bool:
    """Accept a direct ID only when it identifies the original vector source."""
    return flags & 3 == 3


def layer_index(observations: list[int]) -> int:
    """Choose a unique name/source match, never an arbitrary duplicate."""
    matches = [index for index, flags in enumerate(observations) if flags & 7 == 7]
    return matches[0] if len(matches) == 1 else -1


def zoom_mode(mode, legacy_auto_zoom):
    if legacy_auto_zoom is False:
        return 3
    return mode if isinstance(mode, int) and 0 <= mode <= 3 else 0


def scale(value):
    numeric = isinstance(value, (int, float))
    return value if numeric and 1 <= value <= 100000000 else 1000


def restore_index(ids, saved):
    fid, index = saved
    try:
        preferred = ids.index(fid)
    except ValueError:
        preferred = -1
    if preferred >= 0:
        return preferred
    return min(index, len(ids) - 1) if isinstance(index, int) and index >= 0 and ids else -1
