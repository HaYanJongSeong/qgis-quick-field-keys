# Quick Field Keys

A QGIS plugin that assigns attribute values to **selected features in the active
vector layer** using configurable **Alt+1 through Alt+9** shortcuts.
Each shortcut has its own field and value or NULL preset.

## Requirements and compatibility

- QGIS 4.2 or later in the QGIS 4.x series.
- Tested on Windows with QGIS 4.2.2 and Qt 6.11.
- QGIS 3.x is not supported by this public release.
- Linux and macOS execution has not been verified.
- No external Python packages, accounts or network access are required.
- The plugin interface and documentation are in English.

## Installation

1. Download `quick_field_keys_1.2.1.zip` from
   [GitHub Releases](https://github.com/HaYanJongSeong/qgis-quick-field-keys/releases).
   GitHub's automatically generated **Source code** ZIP is not the installation package.
2. In QGIS, open **Plugins > Manage and Install Plugins > Install from ZIP**.
3. Select the installation ZIP and enable **Quick Field Keys**.
4. Restart QGIS after an update. Existing field/value presets are retained.

Publication in the official QGIS plugin repository requires a separate submission
and approval. A GitHub release does not by itself register the plugin there.

## Usage

1. Activate the target vector layer.
2. Open **Plugins > Quick Field Keys > Configure fields and values...**.
3. Assign a field and a value to each desired shortcut. Check **Set NULL** to
   assign NULL instead of a typed value. Leave a preset **Disabled** to avoid assigning a value.
4. Select features on the map or in the attribute table.
5. Press the configured **Alt+number** shortcut.
6. Inspect the results, then use QGIS **Save Layer Edits** to save them.

For example, configure Alt+1 to set `status` to `done`, and Alt+2 to set it to `review`.
Text values are entered literally, without quotation marks or expression syntax.

## Safety and limitations

- No selection means no changes.
- Existing values are overwritten. Changes are **never saved automatically**.
- Editing starts automatically when necessary.
- Each operation is one undo command. A failed operation reverts only its own changes.
- Provider primary keys, joined fields and expression fields are excluded.
- Values are converted to the target field type. Invalid numeric values are rejected.
- An empty string is not NULL. Use the explicit **Set NULL** checkbox for NULL.
- Update defaults on other fields are skipped.
- Presets are stored in the QGIS profile and survive restarts.
- Presets are shared across layers, not tied to a layer ID. They also apply to
  another active layer with the same field name. Always check the active layer and selection.
- Field constraints or provider rules may reject a final save. Check the save result.
- Updating a large selection may temporarily block the QGIS interface.
- Shortcut conflicts can be resolved in **Settings > Keyboard Shortcuts** by
  searching for **Quick Field Keys: Alt+number**.
- The English action names differ from earlier Korean releases. If you customized
  those shortcuts, check your bindings after updating. Field/value presets are unchanged.

## Tests

The regression test creates its own temporary memory layer and does not modify
the current project or any on-disk data. In the QGIS Python console, adjust the
repository path and run:

```python
from pathlib import Path
test = Path('/path/to/qgis-quick-field-keys/tests/test_qgis.py')
exec(compile(test.read_text(encoding='utf-8'), str(test), 'exec'), {'__file__': str(test)})
```

Tests cover Alt+1-9 action connections, the settings dialog, preset retention,
selection scope, type validation, NULL, undo, rollback on failure, skipped update
defaults and the absence of automatic saves. Real keyboard events and installation
through QGIS Plugin Manager are not covered by this automated test.

## Building the installation ZIP

```sh
python build_release.py /path/to/output
```

The archive contains only the plugin source, metadata, icon, README, license
and changelog. ZIP files are distributed as GitHub release assets, not committed
to the source repository.

## Support and license

- Maintainer: [HaYanJongSeong](https://github.com/HaYanJongSeong)
- Email: kjs4075@live.com
- Bugs and requests: [GitHub Issues](https://github.com/HaYanJongSeong/qgis-quick-field-keys/issues)
- License: **GPL-3.0-or-later**. See [LICENSE](LICENSE) for the full text.
