# QGIS repository pre-upload checklist

Release reviewed: **1.7.7**, on **2026-10-07**. This release adds QGIS 3.44 LTR / Qt5 compatibility and retains QGIS 4 / Qt6 support.

The authenticated add-version form for plugin **6547** was inspected in the existing
browser session. All six checklist statements were reviewed. The 68 mandatory
security rules and all 61 skippable rules remain enabled; no security rule is bypassed.

| Official checklist item | Review result |
| --- | --- |
| Correct ZIP structure, including metadata.txt and __init__.py in a top-level folder | Verified: a single `quick_field_keys/` folder; required files are present. |
| Non-empty public source repository matching the ZIP, without compiled files | Verified locally by byte comparison; the repository is public. No ZIP or compiled files are committed. |
| Meaningful description written in English | Verified: English comes first in `description` and `about`, followed by Korean. README and button tooltips are bilingual; source comments are English. |
| Public, valid homepage, tracker and repository URLs | Public GitHub README, source repository and enabled issue tracker are configured. |
| This version has been tested with QGIS and works as expected | Both regression scripts and a temporary GeoPackage plugin Save/reopen check passed in standalone QGIS Python on Windows with QGIS 3.44.15 / Qt 5.15.13 / PyQt 5.15.11 and QGIS 4.2.2 / Qt 6.11 / PyQt 6.11. The temporary QGIS 3 runtime was extracted without installation; existing profiles and projects were not changed. Physical keyboard input and Plugin Manager installation remain manual checks. |
| Consent to email contact and ongoing maintenance correspondence | The maintainer supplied `kjs4075@live.com`, previously submitted this plugin and authorized the latest upload. The portal reports Email confirmed. Mailbox delivery has not been tested. |

## Additional publishing requirements

- GPL-3.0-or-later metadata and full GPL v3 license text are included.
- The package is below the 25 MB limit and contains no binaries or external dependencies.
- Navigation design attribution and the original FeatureNavEd MIT license are included.
- Compatibility and restrictions are documented: QGIS 3.44 LTR and QGIS 4.2+ in the 4.x series;
  Windows/QGIS 3.44.15 and 4.2.2 tested; Linux and macOS unverified; earlier QGIS 3 releases unsupported.
- Runtime code does not make network requests or require credentials.
- The official server's scan and manual approval status must be verified after submission; submission is not approval.
- English code comments and a self-contained memory test are provided.
- The plugin currently uses the Plugins menu; the publishing guide recommends
  the domain-specific Vector menu, but this is a recommendation rather than a checklist requirement.

## Manual test before submission

1. Install `quick_field_keys_1.7.7.zip` using **Install from ZIP** and restart QGIS.
2. Use a disposable layer, not production data. Configure all nine presets.
3. Select two features out of three. Try each Alt+1 through Alt+9 shortcut.
4. Confirm only selected features change and QGIS does not save automatically.
5. Undo a change, clear the selection and check that a shortcut makes no changes.
6. Restart QGIS and confirm presets are retained.
7. Confirm the contact mailbox is monitored and accept the maintenance commitment.
8. Test navigator sorting, manual filter refresh, captured selection, zoom and previous-view history.
9. Test inline column editing, locks, the feature-save icon, grouped feature Undo and both shortcut application modes.
10. Test the shortcut-settings gear, remapping and persistence. Disable FeatureNavEd for overlapping navigation keys.
11. Activate another QGIS layer and confirm preset writes still affect only the navigator's designated target.
12. Confirm the disk button saves all target-layer edits, including external edits, and leaves editing enabled. Saved changes must not be restored by feature Undo.
13. Test the bulb button and automatic flashes, including No zoom mode and empty selections.

## Runtime checks completed for 1.7.7 on both QGIS versions

- Selected-feature preset writes, type/NULL conversion and failed-operation rollback.
- Navigator order, wrap-around, previous-view history, CRS zoom and manual-only filter evaluation.
- Inline modified-field tracking, visible columns, persistent locks and save/Undo icon order.
- Grouped feature Undo, focus/flash calls, conflict protection, atomic retry and edit-session/save boundaries.
- Shortcut configuration, duplicate/external conflicts, registration-failure rollback and settings persistence.
- Designated-target behavior independent of active layer or hidden panel state.
- Explicit Save activation for immediate, staged, form and external edits; commit failure retention and saved Undo boundaries.
- Manual multi-selection flash and automatic navigation flash, including No zoom; empty selection and shortcut remapping.

## Packaging checks for 1.7.7

- Check ZIP CRC, metadata, source-file equality and absence of compiled files before uploading.
- Check the README screenshots and identify test fields/bindings as examples.
- Run im-not-ai v2.3.2 text metrics and change-rate checks without installing it globally.

## Sources

- https://plugins.qgis.org/plugins/add/
- https://plugins.qgis.org/docs/publish
- https://plugins.qgis.org/docs/approval
- https://github.com/qgis/QGIS-Plugins-Website/blob/master/qgis-app/plugins/templates/plugins/form_snippet.html
- https://github.com/qgis/QGIS-Plugins-Website/blob/master/qgis-app/plugins/templates/plugins/plugin_upload.html
