"""SPDX-License-Identifier: GPL-3.0-or-later

Serialize the saved navigator session without changing its settings schema.
"""
from dataclasses import dataclass
import json


@dataclass(frozen=True, slots=True)
class SessionCapture:
    layer_id: str
    layer_name: str
    source_hash: str
    filter: str
    sort_field: str | None
    ascending: bool
    ids: list[int]
    index: int
    selection: list[int]
    selected_only: bool
    selection_snapshot: list[int]
    zoom_mode: int
    scale: float


def serialize(capture: SessionCapture) -> str:
    """Return the saved settings JSON; leave settings I/O to QGIS."""
    current = capture.ids[capture.index] if 0 <= capture.index < len(capture.ids) else None
    state = {
        'layer_id': capture.layer_id, 'layer_name': capture.layer_name,
        'source_hash': capture.source_hash, 'filter': capture.filter,
        'sort_field': capture.sort_field, 'ascending': capture.ascending,
        'feature_id': current, 'index': capture.index, 'selection': capture.selection,
        'selected_only': capture.selected_only,
        'selection_snapshot': sorted(set(capture.selection_snapshot)),
        'zoom_mode': capture.zoom_mode, 'scale': capture.scale,
    }
    return json.dumps(state, ensure_ascii=False)
