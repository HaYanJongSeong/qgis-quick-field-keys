# Changelog

## 1.3.0

- Add sorted feature navigation, previous/next/first/last, position and sort-value display.
- Add optional Alt+Left/Right/Home/End shortcuts with FeatureNavEd conflict protection.
- Add auto zoom with CRS transformation, expression filtering, captured selection scope,
  exact-value search and map picking with cleanup.
- Keep the navigator target aligned with the active layer used by quick presets.
- Add a chosen-field editor using native QGIS field widgets without changing layer form metadata.
- Add explicit single/multi-feature Apply, a fixed editor selection and in-window Undo.
- Add immediate edit-buffer application or in-memory staged Alt+number presets,
  pending preview, captured targets, manual Apply, pending Undo and discard.
- Keep all data-file saves manual; retain pending values on failed application.
- Include bilingual English/Korean documentation and FeatureNavEd design attribution.
- Add an isolated-project/canvas regression test for the new workflows.

## 1.2.1

- Translate the interface, documentation, tests and source comments into English.
- Provide a maintainer email for official repository correspondence.
- Preserve existing field/value presets and document shortcut-name changes.

## 1.2.0

- Prepare public source, documentation, license, icon and support links.
- Limit the supported range to QGIS 4.2+; untested QGIS 3.x is excluded.
- Prevent unrelated fields from changing through update defaults.
- Add an isolated memory-layer regression test and a reproducible ZIP builder.

## 1.1.0

- Extend configuration to Alt+1 through Alt+9.
- Use one compact settings row per shortcut.

## 1.0.0

- Assign field values to selected features using Alt+1 and Alt+2.
- Support NULL, type validation, undo and rollback on failure.
- Never save edits automatically.
