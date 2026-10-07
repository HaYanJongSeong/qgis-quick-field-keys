# QGIS repository pre-upload checklist

Release reviewed: **1.3.0**, on **2026-10-07**.

The authenticated upload page is not accessible to this review session. The exact
six checklist statements were read from the official website's public
`form_snippet.html` template, together with its publishing and approval guidelines.

| Official checklist item | Review result |
| --- | --- |
| Correct ZIP structure, including metadata.txt and __init__.py in a top-level folder | Verified: a single `quick_field_keys/` folder; required files are present. |
| Non-empty public source repository matching the ZIP, without compiled files | Verified locally by byte comparison; the repository is public. No ZIP or compiled files are committed. |
| Meaningful description written in English | Verified: English comes first in `description` and `about`, followed by Korean. README is bilingual; interface and code comments are English. |
| Public, valid homepage, tracker and repository URLs | Public GitHub README, source repository and enabled issue tracker are configured. |
| This version has been tested with QGIS and works as expected | Memory-layer regression tests passed in QGIS 4.2.2 on Windows. Real keyboard events and Plugin Manager installation are not part of this automated test. Test those manually before confirming this statement. |
| Consent to email contact and ongoing maintenance correspondence | **The uploader must confirm this personally.** Metadata uses the maintainer-provided email `kjs4075@live.com`, not a GitHub noreply address. Mailbox delivery has not been tested. |

## Additional publishing requirements

- GPL-3.0-or-later metadata and full GPL v3 license text are included.
- The package is below the 25 MB limit and contains no binaries or external dependencies.
- Navigation design attribution and the original FeatureNavEd MIT license are included.
- Compatibility and restrictions are documented: QGIS 4.2+ in the 4.x series;
  Windows/QGIS 4.2.2 tested; Linux and macOS unverified; QGIS 3.x unsupported.
- Runtime code does not make network requests or require credentials.
- The official server's security scan and manual approval are **not yet performed**.
- English code comments and a self-contained memory test are provided.
- The plugin currently uses the Plugins menu; the publishing guide recommends
  the domain-specific Vector menu, but this is a recommendation rather than a checklist requirement.

## Manual test before submission

1. Install `quick_field_keys_1.3.0.zip` using **Install from ZIP** and restart QGIS.
2. Use a disposable layer, not production data. Configure all nine presets.
3. Select two features out of three. Try each Alt+1 through Alt+9 shortcut.
4. Confirm only selected features change and QGIS does not save automatically.
5. Undo a change, clear the selection and check that a shortcut makes no changes.
6. Restart QGIS and confirm presets are retained.
7. Confirm the contact mailbox is monitored and accept the maintenance commitment.
8. Test navigator sorting, filtering, captured selection, search, picking and zoom.
9. Test chosen-field multi-edit, the in-window Undo and both shortcut application modes.
10. Disable FeatureNavEd before enabling overlapping navigation shortcuts.

## Sources

- https://plugins.qgis.org/plugins/add/
- https://plugins.qgis.org/docs/publish
- https://plugins.qgis.org/docs/approval
- https://github.com/qgis/QGIS-Plugins-Website/blob/master/qgis-app/plugins/templates/plugins/form_snippet.html
- https://github.com/qgis/QGIS-Plugins-Website/blob/master/qgis-app/plugins/templates/plugins/plugin_upload.html
