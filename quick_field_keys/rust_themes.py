"""SPDX-License-Identifier: GPL-3.0-or-later

Select the next QGIS theme from equality observations.
"""


def theme_index(direction, current, matches):
    if not matches:
        return None
    matching = [i for i, match in enumerate(matches) if match]
    selected = current if current in matching else next(iter(matching), None)
    index = selected if selected is not None else (-1 if direction > 0 else 0)
    return (index + direction) % len(matches)
