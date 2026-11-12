# Changelog

## 1.7.9

### 달라진 점

Alt+Up / Down으로 레이어 패널에 저장한 지도 테마를 앞뒤로 전환합니다. 처음과 끝에서는 순환합니다. UI 테마가 아니라 배경을 포함한 레이어 표시·스타일 묶음 전체를 적용합니다. 속성 입력 대상은 패널에서 지정한 레이어로 유지하며 테마 전환은 파일을 저장하지 않습니다. 패널이 보일 때 동작하고 톱니바퀴 설정에서 단축키를 바꾸거나 해제할 수 있습니다.

Alt+1~9로 값을 넣었는데 패널에 이전 값이 남던 문제를 고쳤습니다. 다른 컬럼에 미적용 입력이 있어도 실제로 적용한 컬럼은 바로 갱신합니다. 다른 컬럼의 초안과 원래 입력 대상은 유지합니다. 같은 컬럼의 초안은 캡처한 모든 객체에 프리셋이 적용된 경우에만 새 값으로 대체하므로 나중에 이동할 때 오래된 입력으로 다시 덮어쓰지 않습니다. 다른 객체나 일부 객체에만 적용한 경우에는 기존 초안을 임의로 버리지 않습니다. 대기 프리셋은 실제로 적용하기 전까지 입력값처럼 표시하지 않으며 잠금이나 쓰기 실패가 있으면 입력을 유지합니다.

연속 편집의 Undo 이력을 묶을 때 이미 가진 값을 다시 조회하던 처리를 없앴습니다. 폼을 만들 때 반복하던 쓰기 가능 필드와 위젯 레지스트리 조회도 한 번으로 줄였습니다. 설치 ZIP에서 지도 테마 모듈이 빠지던 문제를 고쳤습니다.

### 저장할 때 주의할 점

단축키 입력은 편집 버퍼에 반영할 뿐 파일을 자동 저장하지 않습니다. Save는 다른 QGIS 도구의 편집까지 포함해 지정 레이어의 모든 미저장 편집을 파일에 저장합니다. 저장한 변경은 객체 Undo로 되돌릴 수 없습니다.

### 확인한 환경

Windows의 QGIS 4.2.3 / Qt 6.11에서 회귀 스크립트 3개와 집중 검사 9개를 실행했습니다. 실제 Qt 키 이벤트로 Alt+Up / Down 테마 전환과 Alt+1 직후의 패널 갱신을 확인했고 임시 GeoPackage의 저장·재열기도 검사했습니다. 테스트 반환 후에는 별도 래퍼로 프로세스를 종료했으며 정상 teardown 완료를 확인한 것은 아닙니다.

QGIS 3.44 LTR 지원은 유지하지만 1.7.9에서는 재시험하지 않았습니다. QGIS 3.44.15 / Qt 5.15.13 검증은 1.7.7 기준입니다. Linux/macOS 실행과 Plugin Manager를 통한 설치는 이번에 확인하지 않았습니다.

### 설치

quick_field_keys_1.7.9.zip을 내려받아 QGIS의 플러그인 관리 및 설치 > ZIP에서 설치에서 선택하세요. 업데이트 후 QGIS를 다시 실행하면 적용됩니다. 재시작하면 미적용 입력·대기 프리셋·객체 Undo 이력은 유지되지 않으므로 필요한 작업을 먼저 정리하세요.

### English

- Cycle whole saved map themes with Alt+Up/Down, including background-layer visibility and styles. Keep the designated editing layer and unsaved attribute edits. Bindings can be changed or cleared; shortcuts work while the panel is visible.
- Refresh successfully applied preset fields in both editors, even when another column has a draft. Preserve unrelated drafts and captured targets. Supersede a same-field draft only after a write covers every captured target; preserve partial-target drafts, staging, locks and failure handling.
- Avoid redundant feature reads when merging Undo history and reuse writable-field and widget-registry lookups while building a form. Include `map_themes.py` in installation ZIPs.
- Keep all file saves manual. Save commits all unsaved edits in the designated layer, including other tools' edits; saved changes cannot be restored by feature Undo.
- Verify three regression scripts, nine focused tests, actual Qt Alt+Up/Down and Alt+1 key events, and temporary GeoPackage save/reopen on Windows with QGIS 4.2.3 / Qt 6.11. Normal teardown, QGIS 3.44 retesting, Linux/macOS and Plugin Manager installation are not verified for this release. QGIS 3.44 LTR support is retained.
- Restart QGIS after updating. Unapplied inputs, staged presets and feature Undo history do not survive restart.

## 1.7.8

- 값을 입력한 뒤 Alt+Right 등으로 객체를 이동하면 폐기 확인창 없이 원래 선택 대상의 편집 버퍼에 반영합니다. 여러 객체를 편집한 뒤 디스크 Save 버튼으로 한 번에 저장할 수 있습니다. 이동 중에는 파일을 저장하지 않습니다.
- 잘못된 값, Lock 또는 쓰기 실패로 반영하지 못하면 입력을 유지하고 이동을 막습니다. 외부 선택·필터 변경으로 입력 대상이 바뀌지 않습니다.
- Save는 다른 도구의 편집을 포함해 지정 레이어의 모든 미저장 편집을 저장합니다. 저장한 변경은 객체 Undo로 복원할 수 없습니다.
- Windows의 QGIS 4.2.2 / Qt 6.11에서 회귀 스크립트 2개와 임시 GeoPackage 저장·재열기를 확인했습니다. QGIS 3.44 LTR 지원은 유지하지만 1.7.8에서는 재시험하지 않았습니다.

- Apply direct field inputs to their captured selection in the edit buffer before navigation, instead of asking to discard them. Never commit during navigation; the disk Save button still saves all edits in the designated layer.
- Keep inputs and block movement when validation, locks or writes fail. External selection and filter changes cannot retarget drafts.
- Verified shortcut navigation, failure retention, captured multi-feature targets and temporary GeoPackage navigation/Save/reopening on Windows with QGIS 4.2.2 / Qt 6.11. QGIS 3.44 LTR support is retained but was not retested for 1.7.8. Saved edits cannot be restored by feature Undo.

## 1.7.7

- Support QGIS 3.44 LTR / Qt5 alongside QGIS 4 / Qt6; older QGIS 3 releases are not supported.
- Handle the Qt5 location of QShortcut and the different key-sequence and enum representations.
- Preserve dock layout settings across both Qt versions.
- Run both regression scripts on Windows with QGIS 3.44.15 / Qt 5.15.13 and QGIS 4.2.2 / Qt 6.11. Verify actual Save by reopening a temporary GeoPackage on both runtimes.

## 1.7.6

- Add example panel and shortcut-settings screenshots to the README.
- Rewrite the GitHub and QGIS descriptions, keeping the installation steps, compatibility limits and Save/Undo warnings.
- Use im-not-ai v2.3.2 to review the Korean wording. No runtime changes from 1.7.5.

## 1.7.5

- Add a bulb icon beside previous-view restoration to flash all currently selected features in the designated layer without changing selection, extent or the active layer. Disable it when there is no selection.
- Automatically flash the destination on First/Previous/Next/Last and previous-view restoration, including No zoom mode.
- Add Flash selected features to shortcut settings, initially unassigned.
- Verify manual multi-selection flash, designated-target safety and automatic navigation flash in isolated QGIS regression tests.

## 1.7.4

- Change the disk button, by maintainer request, from draft-only application to explicit saving of all unsaved edits in the designated layer.
- Enable Save for immediate presets, drafts, staged presets and external edits. Apply drafts and staged presets before committing; form input takes precedence when both target the same field.
- Keep editing enabled after Save. Clear saved feature Undo history; report commit errors without rolling back failed edits. Never commit an unrelated active layer.
- Verify activation, commit, staged/form values, locks, failure retention and saved Undo boundaries in regression tests. Verify an isolated GeoPackage by reopening it through a fresh provider.

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
