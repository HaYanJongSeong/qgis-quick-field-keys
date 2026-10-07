# QGIS repository pre-upload checklist

Release reviewed: **1.7.3**, on **2026-10-07**.

The authenticated add-version form for plugin **6547** was inspected in the existing
browser session. All six checklist statements were reviewed. The 68 mandatory
security rules and all 61 skippable rules remain enabled; no security rule is bypassed.

| Official checklist item | Review result |
| --- | --- |
| Correct ZIP structure, including metadata.txt and __init__.py in a top-level folder | Verified: a single `quick_field_keys/` folder; required files are present. |
| Non-empty public source repository matching the ZIP, without compiled files | Verified locally by byte comparison; the repository is public. No ZIP or compiled files are committed. |
| Meaningful description written in English | Verified: English comes first in `description` and `about`, followed by Korean. README and button tooltips are bilingual; source comments are English. |
| Public, valid homepage, tracker and repository URLs | Public GitHub README, source repository and enabled issue tracker are configured. |
| This version has been tested with QGIS and works as expected | Both regression scripts passed in QGIS 4.2.2 on isolated memory layers. Native dialog controls, key binding state, editing, Undo and rollback were exercised. Physical keyboard input and installation of this ZIP through Plugin Manager remain separate manual tests. |
| Consent to email contact and ongoing maintenance correspondence | The maintainer supplied `kjs4075@live.com`, previously submitted this plugin and authorized the latest upload. The portal reports Email confirmed. Mailbox delivery has not been tested. |

## Additional publishing requirements

- GPL-3.0-or-later metadata and full GPL v3 license text are included.
- The package is below the 25 MB limit and contains no binaries or external dependencies.
- Navigation design attribution and the original FeatureNavEd MIT license are included.
- Compatibility and restrictions are documented: QGIS 4.2+ in the 4.x series;
  Windows/QGIS 4.2.2 tested; Linux and macOS unverified; QGIS 3.x unsupported.
- Runtime code does not make network requests or require credentials.
- The official server's scan and manual approval status must be verified after submission; submission is not approval.
- English code comments and a self-contained memory test are provided.
- The plugin currently uses the Plugins menu; the publishing guide recommends
  the domain-specific Vector menu, but this is a recommendation rather than a checklist requirement.

## Manual test before submission

1. Install `quick_field_keys_1.7.3.zip` using **Install from ZIP** and restart QGIS.
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

## Automated checks completed for 1.7.3

- Selected-feature preset writes, type/NULL conversion and failed-operation rollback.
- Navigator order, wrap-around, previous-view history, CRS zoom and manual-only filter evaluation.
- Inline modified-field tracking, visible columns, persistent locks and save/Undo icon order.
- Grouped feature Undo, focus/flash calls, conflict protection, atomic retry and edit-session/save boundaries.
- Shortcut configuration, duplicate/external conflicts, registration-failure rollback and settings persistence.
- Designated-target behavior independent of active layer or hidden panel state.
- ZIP CRC, metadata, source-file equality and absence of compiled files.

## Sources

- https://plugins.qgis.org/plugins/add/
- https://plugins.qgis.org/docs/publish
- https://plugins.qgis.org/docs/approval
- https://github.com/qgis/QGIS-Plugins-Website/blob/master/qgis-app/plugins/templates/plugins/form_snippet.html
- https://github.com/qgis/QGIS-Plugins-Website/blob/master/qgis-app/plugins/templates/plugins/plugin_upload.html
