# Quick Field Keys

A QGIS plugin that assigns attribute values to **selected features in the navigator's designated
vector layer** using configurable shortcuts, defaulting to **Alt+1 through Alt+9**.
Each shortcut has its own field and value or NULL preset. Version 1.3 adds sorted
navigation, chosen-field single/multi-edit forms and optional staged application.

## Requirements and compatibility

- QGIS 4.2 or later in the QGIS 4.x series.
- Tested on Windows with QGIS 4.2.2 and Qt 6.11.
- QGIS 3.x is not supported by this public release.
- Linux and macOS execution has not been verified.
- No external Python packages, accounts or network access are required.
- The interface is English. Documentation is provided in English and Korean below.

## Installation

1. Obtain `quick_field_keys_1.7.3.zip`. Published releases are available from
   [GitHub Releases](https://github.com/HaYanJongSeong/qgis-quick-field-keys/releases).
   GitHub's automatically generated **Source code** ZIP is not the installation package.
2. In QGIS, open **Plugins > Manage and Install Plugins > Install from ZIP**.
3. Select the installation ZIP and enable **Quick Field Keys**.
4. Restart QGIS after an update. Existing field/value presets are retained.

Publication in the official QGIS plugin repository requires a separate submission
and approval. A GitHub release does not by itself register the plugin there.

## Usage

1. Open the navigator and designate the target vector layer using its layer selector.
2. Click **Field value presets...** in the navigator.
3. Assign a field and a value to each desired shortcut. Check **Set NULL** to
   assign NULL instead of a typed value. Leave a preset **Disabled** to avoid assigning a value.
4. Select features in the designated layer on the map or in its attribute table.
5. Press the configured preset shortcut. Changing the active QGIS layer does not change the designated write target, even while the navigator is hidden.
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
- Preset definitions are shared across layers, but writes use the navigator's designated layer, not whichever layer is active in the QGIS panel. Check that designated layer and its selection. If the navigator has never been created, presets fall back to the active layer; once it exists, an invalid/empty designated target stops writes.
- Field constraints or provider rules may reject a final save. Check the save result.
- Updating a large selection may temporarily block the QGIS interface.
- The gear icon beside Undo configures this plugin's shortcuts. Use the clear-assignment button beside a key input to remove that assignment; Save applies the change and Cancel preserves current bindings. Empty means unassigned; defaults are restored only after saving. Duplicate keys, conflicts with QGIS actions and bare typing keys are rejected. Other QGIS bindings are never changed.
- The English action names differ from earlier Korean releases. If you customized
  those shortcuts, check your bindings after updating. Field/value presets are unchanged.

## Tests

The regression test creates its own temporary memory layer and does not modify
the current project or any on-disk data. In the QGIS Python console, adjust the
repository path and run:

```python
from pathlib import Path
root = Path('/path/to/qgis-quick-field-keys')
for name in ('test_qgis.py', 'test_navigation.py'):
    test = root / 'tests' / name
    exec(compile(test.read_text(encoding='utf-8'), str(test), 'exec'), {'__file__': str(test)})
```

Tests cover Alt+1-9 action connections, the settings dialog, preset retention,
selection scope, type validation, NULL, undo, rollback on failure, skipped update
defaults and the absence of automatic saves. Real keyboard events and installation
through QGIS Plugin Manager are not covered by this automated test.
The navigation test uses its own project, map canvas and memory layers. It covers
sorting with NULLs, bounds, active-layer alignment, CRS zoom, filters, selection
snapshots, search, pick lifecycle, chosen-field multi-edit, staging and undo.

## Sorted feature navigation

Open **Plugins > Quick Field Keys > Feature navigation and editing**.

- Choose a layer, a **Sort by** field and **Ascending** or descending order.
- Hover over buttons for their English name and explanation, followed by Korean name and explanation, including relevant shortcut keys and safety limits.
- Use the **First / Previous / Next / Last** arrow icons (hover for shortcut help). Navigation selects one feature and
  activates that layer so Alt+number inputs target the same layer.
- Position, selection count and the current sort value are shown beside the navigation icons. A camera with a left arrow indicates the independent previous-view action.
- Choose **Fit feature / Keep current scale / Fixed scale / No zoom** from one dropdown. The scale input is enabled only for Fixed scale; there is no separate Auto zoom checkbox.
- Enter a QGIS expression and click the **refresh icon** beside the expression builder to apply and reload. The **trash icon** clears only the input; click refresh to apply that change. Edits, Undo and sorting do not re-evaluate filter membership. Initial layer/session loading builds the list once. The filter affects
  only navigation; it does not change the layer's provider subset or stored data.
- **Captured selection only** restricts navigation to a fixed set of selected IDs. Use **Use current selection** to capture and activate the scope.
- Controls are ordered as layer and sorting, filter and scope, navigation and zoom, then edit and apply, without section title rows or group frames. Find and Pick from map are removed.
- Reload after external changes to feature membership or the layer schema.
- Alt+Left/Right/Home/End navigation is automatic while the panel is visible. If FeatureNavEd is loaded, navigation shortcuts are paused. This plugin never changes FeatureNavEd.
- Previous wraps from first to last; Next wraps from last to first. Alt+Left/Right use the same wrap behavior. The camera-and-left-arrow icon or Alt+Backspace restores the previous selection and map extent without changing the filter; history is limited to 100 in-session views.
- Undo defaults to Alt+Z. The last layer, applied filter, sort order, position and panel geometry are remembered. Configure presets with **Field value presets...** and change shortcuts using the gear icon. Use the expression button beside the filter to build an expression using the layer's fields.
- Navigation shortcuts are disabled when this dock is hidden. No file is saved.

## Chosen-field editor and multi-edit

Select a feature by navigation or select one or more features on the layer. The chosen columns and current values appear at the bottom of the navigator; there is no separate editor window.
Use the **eye icon** to choose visible and editable columns. The chooser provides **Select all / Deselect all**; confirmation updates the inline fields and Cancel leaves saved column choices unchanged.
Edit directly; changed fields are detected without Change checkboxes. Use the **disk icon** to apply modified, unlocked fields to the edit buffer; this is not a file commit. Navigation asks before discarding unapplied input. If selection changes outside the panel, unapplied inputs keep their original targets until applied or undone.
The **Undo reverse-arrow icon** is beside immediate application and supports Alt+Z. Apply pending and Discard pending are no longer panel buttons; their plugin-menu actions remain available if immediate application is disabled.

- The **eye icon** determines which field editors appear.
  Other fields cannot be modified through the form. Choices are remembered per layer ID.
- Native QGIS field editor widgets are used without altering the layer form configuration.
- Fields follow the current selection when no unapplied inputs exist. Unapplied inputs keep their captured targets if selection changes externally.
- Untouched fields and mixed values are not written. Returning a single-valued field to its original value clears its draft change.
- Each input ends with a **Lock icon**. Locks are retained per layer and block this plugin's form, shortcuts, staging, pending Apply and Undo writes to that column. Other QGIS tools can still change the field. Locking a modified input asks before discarding its draft.
- The **feature-save disk icon**, immediately left of Undo, writes only modified, unlocked fields to the edit buffer. Actual QGIS file saving remains separate.
- **Feature Undo / Alt+Z** restores all consecutive plugin changes to the last edited feature selection, then selects it, fits its map extent and flashes it, even outside the filter or in No zoom mode. Multiple selected features are treated as one group. Unapplied inline inputs require confirmation before leaving their targets.
- Undo never invokes the general layer Undo stack. Unrelated external fields are preserved; conflicting changes to a recorded value block the whole restoration. Saved edits and edits from other tools are not reverted.
- History retains up to 200 groups in the current session. Commit, rollback, an external layer Undo, layer removal and restart invalidate the relevant history. Failed restoration retains history for retry.
- Navigation or changing visible fields asks before discarding unapplied inputs.
- Use QGIS **Save Layer Edits** separately when you want to persist changes.

## Immediate or staged Alt+number presets

The **Apply presets immediately to layer edits** checkbox is available in the navigator. The setting is retained across restarts.

- **On:** a shortcut updates selected features in the layer edit buffer immediately.
- **Off:** a shortcut changes only the in-memory pending values. Use **Plugins > Quick Field Keys > Apply pending shortcuts** to apply them. This is not a file save.
- Each shortcut captures its current selected feature IDs. Later selection or
  navigation does not retarget pending changes.
- Pending values belong to one layer at a time. Apply or discard them before staging
  values for another layer. A failed Apply retains the pending values.
- Toggling the checkbox does not automatically apply existing pending values.
- **Undo** cancels consecutive staged shortcuts to the same selection together; **Discard pending shortcuts** in the plugin menu clears all pending values.
- Pending values exist only for this plugin session. They are not retained on unload/restart.
- Form-field visibility applies to the form. **Apply pending shortcuts** separately
  applies all configured staged preset fields, including fields hidden from the form.
- The navigator shows the pending change count when pending values exist.
- **Plugins > Quick Field Keys > Discard pending shortcuts** is always available,
  including when a pending target layer was removed. Failed application retains
  pending data until you explicitly discard it.

## Building the installation ZIP

```sh
python build_release.py /path/to/output
```

The archive contains only the plugin source, metadata, icon, README, license
and changelog, plus the third-party attribution license. ZIP files are distributed as GitHub release assets, not committed
to the source repository.

## Support and license

- Maintainer: [HaYanJongSeong](https://github.com/HaYanJongSeong)
- Email: kjs4075@live.com
- Bugs and requests: [GitHub Issues](https://github.com/HaYanJongSeong/qgis-quick-field-keys/issues)
- License: **GPL-3.0-or-later**. See [LICENSE](LICENSE) for the full text.
- Navigation behavior is inspired by **FeatureNavEd 1.0.8** by **Irene Jaya**.
  Our implementation is independent and uses explicit editing instead of implicit
  form saves. The original project's MIT license is retained in
  [LICENSE.FeatureNavEd](LICENSE.FeatureNavEd).
  Upstream: https://github.com/irenejaya/feature-navigator-editor

---

## 한국어 사용 안내

Quick Field Keys는 **정렬된 객체 탐색과 선택한 필드 편집**을 함께 제공하는 플러그인입니다.
화면은 영어이며 QGIS 4.2 이상, 4.x 계열을 지원합니다. Windows의 QGIS 4.2.2에서 테스트했습니다.
Linux와 macOS 실제 실행은 아직 검증하지 않았습니다.

### 설치와 기본 입력

1. 배포된 `quick_field_keys_1.7.3.zip`을 받습니다.
2. QGIS의 **플러그인 관리 및 설치 > ZIP 파일에서 설치**로 설치하고 QGIS를 재시작합니다.
3. 이동 패널에서 반영할 레이어를 지정하고 **Field value presets...**에서
   Alt+1~Alt+9의 필드와 값을 지정합니다. 기존 설정은 유지됩니다.
4. 객체를 선택하고 단축키를 누릅니다. 선택 객체가 없으면 수정하지 않습니다.

### 정렬 탐색

**Feature navigation and editing** 패널에서 레이어, 정렬 필드와 오름·내림차순을 지정합니다.
레이어 선택·정렬, 필터와 선택 범위, 탐색과 줌, 편집과 적용 순서로 제목줄과 그룹 테두리 없이 표시합니다. 처음·이전·다음·마지막은 화살표 아이콘이며, 마우스를 올리면 기능과 단축키를 표시합니다. 순번·정렬값 표시, 자동 줌, 표현식 필터를 지원하며 Find와 Pick from map은 제거했습니다. 탐색한 레이어를 활성화하여 Alt+숫자 입력 대상과 일치시킵니다.

**Use current selection**은 현재 선택 객체 범위를 고정하고 **Captured selection only**를 활성화합니다. 하나씩 탐색해도 범위가 줄어들지 않습니다.
정렬은 현재 필터와 선택 범위 안에서 작동합니다. 외부에서 객체나 필드가 바뀌면 목록을 다시 불러오세요.

Alt+좌우/Home/End는 패널이 보이면 자동 활성화합니다. FeatureNavEd가 켜져 있으면 충돌을 피하기 위해 중지합니다.
원본 FeatureNavEd 파일이나 설정을 자동으로 바꾸지 않습니다.

첫 객체에서 Previous를 누르면 마지막으로 이동합니다. 뒤로 화살표 또는 Alt+Backspace는 필터를 유지한 채 직전 선택과 지도 화면을 복원합니다. 화면 이력은 현재 실행에서 최근 100개만 유지합니다. Undo는 Alt+Z입니다. 마지막 레이어·적용 필터·정렬·순번·패널 위치를 기억합니다. 필터 옆 표현식 버튼으로 필드와 연산자를 선택하여 입력할 수 있습니다.

줌은 **Fit feature / Keep current scale / Fixed scale / No zoom** 중 하나를 선택합니다. 별도 Auto zoom 체크박스는 없으며, 축척 입력은 Fixed scale일 때만 활성화됩니다.

표현식 버튼 옆 **새로고침을 눌러야** 필터를 적용하고 목록을 다시 불러옵니다. 편집·Undo·정렬·표현식 입력 중에는 필터 조건을 다시 평가하지 않습니다. 쓰레기통은 입력칸만 비우며, 그 변경도 새로고침을 눌러야 적용됩니다. 객체 삭제나 고정 선택 범위 초기화는 하지 않습니다. 레이어 선택이나 세션 복원 시 최초 목록 생성은 한 번 수행합니다.

버튼에 마우스를 올리면 영어 이름·설명 아래에 한국어 이름·설명을 표시합니다. 관련 단축키, Undo 범위, 필터 지우기와 대기값 적용의 주의 사항도 함께 안내합니다.

순번·선택 개수·정렬값과 탐색 아이콘을 같은 줄에 표시합니다. 직전 화면 복원은 카메라에 왼쪽 화살표를 합친 아이콘으로 구분합니다.

Next와 Alt+Right는 마지막 객체에서 처음으로 돌아갑니다. Previous와 Alt+Left는 첫 객체에서 마지막으로 이동합니다. 순환 범위는 현재 필터와 고정 선택 범위에 포함된 객체입니다.

### 원하는 필드만 표시·다중 편집

이동 패널의 **눈 아이콘**에서 보일 컬럼을 선택합니다. 현재 선택 객체의 컬럼 이름과 값이 **패널 맨 아래**에 표시되며 바로 편집할 수 있습니다. 별도의 편집창은 열지 않습니다.

컬럼 선택창의 **Select all / Deselect all**로 일괄 선택·해제합니다. 확인하면 패널 하단의 컬럼이 바뀌며, 취소하면 저장된 컬럼 선택을 유지합니다. Change 체크 없이 직접 입력하고 **디스크 아이콘**으로 수정한 컬럼만 편집 버퍼에 반영합니다. 실제 파일 저장은 별도입니다. 미적용 입력은 탐색 전 폐기 여부를 확인하고, 외부 선택 변경으로 적용 대상이 바뀌지 않습니다.

**Undo 역화살표**는 즉시 적용 줄 오른쪽에 있으며 Alt+Z도 지원합니다. Apply pending과 Discard pending 버튼은 패널에서 제거했습니다. 즉시 적용을 끈 경우에는 플러그인 메뉴에서 대기값을 적용·폐기할 수 있습니다.

입력칸 끝의 **Lock 아이콘**은 레이어별로 기억하며 이 플러그인의 폼·단축키·대기값 적용·Undo에서 해당 컬럼 변경을 차단합니다. 다른 QGIS 도구에는 적용되지 않습니다. 수정한 입력을 잠글 때는 폐기 여부를 확인합니다. 수정하지 않은 필드나 다중 선택의 혼합값은 덮어쓰지 않습니다.
**객체 Undo / Alt+Z**는 마지막 선택 객체에 연속 입력한 플러그인 변경을 모두 함께 복원한 뒤 해당 객체를 선택·화면 맞춤·반짝임으로 표시합니다. 필터 밖이거나 No zoom이어도 대상 화면으로 이동합니다. 다중 선택 입력은 선택 객체들을 한 묶음으로 되돌립니다. 미적용 필드 입력이 있으면 먼저 폐기 여부를 확인합니다.

다른 도구의 변경이나 이미 저장한 편집은 되돌리지 않습니다. 플러그인이 바꾼 필드에 외부 변경이 있으면 덮어쓰지 않고 복원을 차단합니다. 이력은 현재 편집 세션의 최근 200묶음이며 저장·롤백·외부 레이어 Undo·레이어 삭제·재시작으로 무효화됩니다. 복원 쓰기 실패 시 이력은 재시도할 수 있도록 유지합니다.
실제 파일 저장은 QGIS의 편집 저장 기능으로 따로 수행합니다.

### Alt+숫자 즉시 적용·수동 적용 전환

**Apply presets immediately to layer edits**를 켜면 지정한 프리셋 단축키를 레이어 편집 버퍼에 즉시 적용합니다.
끄면 메모리에 값을 대기시킵니다. 플러그인 메뉴의 **Apply pending shortcuts**로 적용하세요.
이 토글은 실제 파일의 자동 저장 여부가 아닙니다. 어떤 모드에서도 파일은 자동 저장하지 않습니다.

대기값은 단축키를 누른 시점의 선택 객체에 고정됩니다. 이후 선택·탐색을 바꾸어도 대상은 바뀌지 않습니다.
한 번에 한 레이어의 값만 대기시킬 수 있습니다. 토글을 바꾸어도 기존 대기값은 자동 적용되지 않습니다.
플러그인 메뉴의 **Discard pending shortcuts**로 대기값을 지울 수 있으며, QGIS 재시작·플러그인 해제 시에는 대기값이 유지되지 않습니다.

폼의 표시 필드와 단축키 설정은 별개입니다. **Apply pending shortcuts**는 폼에서 숨긴 필드라도
설정된 모든 대기 단축키 값을 적용합니다. **Undo**는 이 플러그인의 객체 이력만 사용하며 다른 도구의 레이어 편집을 취소하지 않습니다.

문의: https://github.com/HaYanJongSeong/qgis-quick-field-keys/issues

### 단축키 설정과 반영 대상

Undo 오른쪽 **톱니바퀴**에서 기능별 단축키를 변경·지정합니다. 입력칸을 비우면 미지정이며 기본값 복원도 저장해야 적용됩니다. 프리셋, 탐색, 필터, 선택 범위, 피처 저장, 포커스 필드 잠금 등을 설정합니다. 중복·QGIS 충돌·입력 중 오작동할 수 있는 일반 문자 키는 거부하고 기존 QGIS 단축키는 바꾸지 않습니다.

각 단축키 입력칸 옆의 **지정 해제 버튼**으로 해당 기능의 키 지정을 취소합니다. **저장**을 눌러야 반영되며, 창의 **취소**는 기존 지정을 유지합니다.

즉시 적용 줄 오른쪽 아이콘은 **피처 저장·Undo·설정** 순서입니다. 맨 아래의 별도 저장 줄은 제거했습니다.

반영 대상은 이동 패널에서 지정한 레이어입니다. QGIS 레이어 패널에서 다른 레이어를 활성화하거나 이동 패널을 숨겨도 그 지정 레이어의 선택 객체에 반영합니다. 대상 레이어가 없거나 삭제되면 다른 레이어로 임의 전환하지 않고 입력을 중단합니다. 이동 패널을 한 번도 열지 않은 경우에만 기존 방식대로 활성 레이어를 사용합니다.
