# Changelog

## 1.7.3

- Replace legacy field-origin and vector-layer filter enum aliases with explicit scoped enums required by the official Qt6 compatibility checker. Runtime behavior is unchanged.
- Re-run both isolated QGIS regression scripts before publishing.

## 1.7.2

- Add a clear-assignment button next to each shortcut input, with English/Korean help.
- Clear only the chosen action's assignment; Save applies the change and Cancel keeps current bindings.
- Verify clearing, deferred application and saved unassigned state in the shortcut dialog regression test.

## 1.7.1

- Move the feature-save disk icon immediately left of Undo. Keep Save / Undo / Settings on the immediate-application row and remove the bottom save row.
- Share the save control with the current inline editor, preserving enabled state, column locks and assigned shortcuts across layer changes.
- Verify the icon order and existing save/Undo behavior in isolated QGIS tests.

## 1.7.0

- Remove Change checkboxes and detect modified fields automatically. Returning a single-valued field to its original value cancels its draft change; untouched mixed values are never applied.
- Add persistent right-side Lock icons. Lock guards cover this plugin's form, presets, staging, pending Apply and grouped Undo; unrelated QGIS tools are unaffected. Ask before discarding a draft when locking its field.
- Replace Apply field edits with a disk icon that applies modified, unlocked feature inputs to the edit buffer; it does not commit the data file.
- Add a gear icon to the right of Undo and native key-sequence settings for preset, navigation, filter, selection, save, lock and settings actions. Support disabling keys, restoring defaults, duplicate/conflict validation, live rebinding and settings persistence.
- Reject bare typing keys and multi-stroke sequences. Check other QGIS bindings without changing them; restore prior preset bindings if registration fails.
- Keep the navigator's designated layer as the preset write target even when another layer is active or the panel is hidden. Invalid/missing designated targets never fall back to another layer.
- Verify column locks, automatic draft tracking, feature-save icon, shortcut remapping/failure rollback and pinned-target safety in isolated QGIS tests.

## 1.6.0

- Group consecutive Quick Field Keys edits to the same feature selection; Undo restores all recorded columns in the last group and returns to, selects, zooms and flashes those features.
- Keep feature Undo separate from QGIS's general Undo stack. Preserve unrelated external changes; block restoration if a recorded value was changed elsewhere, a target is missing or restoration fails.
- Retain failed restoration history for retry. Invalidate history after an external layer Undo, commit, rollback or layer deletion. Retain up to 200 groups in memory for the current editing session.
- Undo multiple selected features as one group. Consecutive staged shortcuts to the same selection are also cancelled together.
- Freeze filter membership between explicit refreshes. Edits, Undo, sorting and draft expression changes no longer re-evaluate the filter. Clear empties only the input; refresh applies it. Initial layer/session loading still builds the list once.
- Verify grouped multi-field restoration, focus/flash calls, filter independence, conflicts, atomic retry, save boundaries and manual filter refresh using isolated memory layers.
- Hide detached inline editors and row widgets before Qt deferred deletion to avoid stale controls overlapping the panel.

## 1.5.0

- Replace separate editor and column-choice text buttons with an eye icon.
- Display chosen column names and current selected-feature values at the navigator bottom, using native editable field widgets instead of another editor window.
- Keep explicit Change / Apply field edits and ask before discarding unapplied input on navigation. External selection changes cannot silently retarget unapplied values.
- Remove Apply pending and Discard pending buttons from the panel; keep their plugin-menu actions for non-immediate mode.
- Place a reverse-arrow Undo icon at the right of the immediate-application row, retaining Alt+Z and local input Undo.
- Verify embedded widgets, current values, inline apply/Undo, cancellation safety, eye-column selection and navigation behavior in isolated QGIS tests.

## 1.4.7

- Add Select all and Deselect all to the column chooser, with bilingual explanations.
- Show only the chooser while selecting columns; reveal the editor after confirmation instead of opening two windows together.
- Keep Cancel from saving column choices; hide and restore an existing editor during its chooser.
- Verify bulk selection and hidden-editor behavior in isolated QGIS tests.

## 1.4.6

- Wrap Next from the last eligible feature to the first, matching Previous's reverse wrap.
- Apply the same behavior to the Next icon and Alt+Right; keep filter and captured selection restrictions unchanged.
- Update English/Korean tooltips and verify both button and shortcut wrap behavior in isolated QGIS tests.

## 1.4.5

- Place the feature navigation icons on the position and selected-count row.
- Replace the previous-view arrow with a camera-and-left-arrow SVG icon.
- Preserve navigation behavior, independent view history and bilingual tooltips.
- Verify same-row layout, icon loading and navigation behavior in isolated QGIS tests.

## 1.4.4

- Add English names and explanations followed by Korean names and explanations to navigator and editor button tooltips.
- Include the native expression button, toolbar action, field-selection confirmation buttons and preset confirmation buttons.
- Explain shortcut keys, captured targets, filter-only clearing and Undo limitations without changing editing behavior.
- Verify English and Korean tooltip coverage for navigator and editor buttons in isolated QGIS tests.

## 1.4.3

- Place refresh and trash icons immediately after the expression builder on the filter input row.
- Refresh applies the expression filter and reloads the navigation list.
- Trash clears the expression filter and reloads; it never deletes features or changes the captured selection scope.
- Remove the separate text-button row and verify both icon actions and panel rendering.

## 1.4.2

- Remove section title rows and group frames; reduce margins and spacing.
- Hide empty pending status, unrestricted scope status and normal shortcut status; retain shortcut help in tooltips and show conflict warnings.
- Replace First/Previous/Next/Last text buttons with native arrow icons, accessible names and shortcut tooltips.
- Replace the Auto zoom checkbox with one choice: Fit feature, Keep current scale, Fixed scale or No zoom. Enable the scale input only for Fixed scale and migrate the old saved checkbox state.
- Keep the independent previous-view icon separated from feature navigation.
- Verify all navigation icon clicks, compact section order and the rendered panel in isolated QGIS tests.

## 1.4.1

- Order controls as layer and sorting, filter and selection scope, navigation and zoom, then edit and apply.
- Remove Find and Pick from map, including their runtime handlers and saved search state.
- Expose Choose visible / editable columns directly in the navigator; open the selected layer's editor and column chooser together.
- Preserve cancellation of unapplied edits and verify the layout and direct column chooser in isolated tests.

## 1.4.0

- Use one toolbar icon and group navigation, filtering, search and editing controls.
- Move Alt+number preset configuration into the navigator and add the native expression builder.
- Enable navigation shortcuts automatically while the panel is visible, with FeatureNavEd conflict protection.
- Remember the last layer, applied filter, sort order, position and panel geometry.
- Bind Undo to Alt+Z in the navigator and chosen-field editor.
- Wrap Previous from the first feature to the last.
- Add a previous-view arrow button and Alt+Backspace, restoring selection and map extent without changing the filter. Keep up to 100 in-session views.
- Verify the new controls, filter-independent history and remembered state in isolated QGIS tests.

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
