"""SPDX-License-Identifier: GPL-3.0-or-later

Save-button eligibility from QGIS observations.
Bits: valid writable target, draft, pending, editable, modified.
"""


def save_enabled(flags: int) -> bool:
    """Combine QGIS observations without touching the edit buffer."""
    return bool(flags & 1 and (flags & 6 or flags & 24 == 24))
