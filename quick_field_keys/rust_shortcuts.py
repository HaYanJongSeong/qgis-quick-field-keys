"""SPDX-License-Identifier: GPL-3.0-or-later

Track duplicate canonical shortcut strings during one normalization.
"""


class ShortcutGuard:
    def __init__(self):
        self.used = {}

    def __enter__(self):
        return self

    def check(self, key, name):
        previous = self.used.get(key)
        self.used.setdefault(key, name)
        return previous

    def __exit__(self, exc_type, exc, tb):
        return None
