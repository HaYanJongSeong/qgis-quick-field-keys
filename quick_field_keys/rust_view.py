"""SPDX-License-Identifier: GPL-3.0-or-later

Choose a navigation view while preserving the previous or selected feature.
"""
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class InvalidFeatureId(ValueError):
    def __str__(self) -> str:
        return 'QGIS feature ID outside signed 64-bit range'


def choose(ids, scope, focus):
    previous, selected = focus
    ids = [fid for fid in ids if fid in scope] if scope is not None else ids
    current = previous if previous in ids else next((fid for fid in selected if fid in ids), None)
    return ids, ids.index(current) if current is not None else -1
