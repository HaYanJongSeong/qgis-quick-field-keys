"""SPDX-License-Identifier: GPL-3.0-or-later

Layer identity hashes and exact saved-name comparison.
"""
import hashlib
from typing import TypeAlias, assert_never


SavedValue: TypeAlias = str | int | float | bool | None | list['SavedValue'] | dict[str, 'SavedValue']


def session_key(normalized_path: str) -> str:
    """Build the persisted key from a normalized absolute path or empty observation."""
    identity = normalized_path or '__unsaved_project__'
    return 'quick_field_keys/navigator/sessions/' + hashlib.sha256(identity.encode('utf-8')).hexdigest()


def source_hash(provider: str, source: str) -> str:
    """Preserve SHA-256(provider + newline + source), with strict UTF-8."""
    return hashlib.sha256((provider + '\n' + source).encode('utf-8')).hexdigest()


def same_text(actual: str, saved: SavedValue) -> bool:
    """Keep Python string equality semantics; other saved JSON types never match."""
    match saved:
        case str():
            expected = saved
        case None | int() | float() | list() | dict():
            return False
        case unreachable:
            assert_never(unreachable)
    return actual == expected
