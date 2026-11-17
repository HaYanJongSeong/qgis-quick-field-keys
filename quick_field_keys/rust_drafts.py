"""SPDX-License-Identifier: GPL-3.0-or-later

Select modified, unlocked fields and preserve unrelated captured drafts.
"""


def dirty(uniform, equal):
    return not (uniform and equal)


def refresh_fields(captured, rows, observations):
    changes, changed_fields = observations
    captured = set(captured)
    names = {name for fid, name in changes if fid in captured and name in rows}
    return {name for name in names if name not in changed_fields
            or all((fid, name) in changes for fid in captured)}


def applicable_fields(rows, changed_fields):
    return [name for name, (wrapper, lock) in rows.items()
            if name in changed_fields and not lock.isChecked()]
