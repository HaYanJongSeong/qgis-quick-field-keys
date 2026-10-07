# Quick Field Keys

A QGIS plugin that assigns attribute values to **selected features in the active
vector layer** using configurable **Alt+1 through Alt+9** shortcuts.
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

1. Download `quick_field_keys_1.3.0.zip` from
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
- Use **First / Previous / Next / Last**. Navigation selects one feature and
  activates that layer so Alt+number inputs target the same layer.
- Position, selection count and the current sort value are shown.
- **Auto zoom** supports fitting the feature, keeping the scale or a fixed scale.
- Enter a QGIS expression and click **Apply filter / reload**. The filter affects
  only navigation; it does not change the layer's provider subset or stored data.
- **Selected snapshot only** captures a fixed set of selected IDs. Navigation does
  not collapse that set when it selects one feature. Use **Capture selection** to replace it.
- **Find next** searches for an exact string representation of a field value
  inside the current list. Search is case-sensitive; it is not an expression search.
- **Pick from map** jumps to an eligible feature. Stop picking by unchecking it.
- Reload after external changes to feature membership or the layer schema.
- **Enable Alt+Left/Right/Home/End navigation** is off by default. FeatureNavEd
  must be disabled in Plugin Manager before enabling it. This plugin does not
  disable or change the installed FeatureNavEd plugin itself.
- Navigation shortcuts are disabled when this dock is hidden. No file is saved.

## Chosen-field editor and multi-edit

Select one or more features, then open **Edit chosen fields / pending shortcuts...**
from the plugin menu, or **Edit chosen fields...** from the navigator.

- **Choose visible / editable fields...** determines which field editors appear.
  Other fields cannot be modified through the form. Choices are remembered per layer ID.
- Native QGIS field editor widgets are used without altering the layer form configuration.
- The feature IDs are captured when the editor opens. Later map selections do
  not change this form's targets. Close and reopen to edit a different selection.
- **Change field_name** controls which fields will be applied. A mixed initial
  value is not written unless you explicitly choose to change it.
- **Apply form edits** writes only checked fields to the layer edit buffer.
- **Undo** first resets unapplied form inputs, then staged shortcuts, then the
  layer's latest undo command. The layer command may have been created by another tool.
- Closing a form or changing its visible fields asks before discarding unapplied inputs.
- Use QGIS **Save Layer Edits** separately when you want to persist changes.

## Immediate or staged Alt+number presets

The **Apply Alt+1-9 immediately to layer edits** checkbox is available in the
navigator and the chosen-field editor. The setting is retained across restarts.

- **On:** a shortcut updates selected features in the layer edit buffer immediately.
- **Off:** a shortcut changes only the in-memory pending values. Preview them in
  the editor, then click **Apply pending shortcuts**. This is not a file save.
- Each shortcut captures its current selected feature IDs. Later selection or
  navigation does not retarget pending changes.
- Pending values belong to one layer at a time. Apply or discard them before staging
  values for another layer. A failed Apply retains the pending values.
- Toggling the checkbox does not automatically apply existing pending values.
- **Undo** can revert the last staged shortcut; **Discard pending** clears all pending values.
- Pending values exist only for this plugin session. They are not retained on unload/restart.
- Form-field visibility applies to the form. **Apply pending shortcuts** separately
  applies all configured staged preset fields, including fields hidden from the form.
- The pending preview shows up to 100 entries; all pending changes are retained.
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

1. GitHub Releases에서 `quick_field_keys_1.3.0.zip`을 받습니다.
2. QGIS의 **플러그인 관리 및 설치 > ZIP 파일에서 설치**로 설치하고 QGIS를 재시작합니다.
3. **Plugins > Quick Field Keys > Configure fields and values...**에서
   Alt+1~Alt+9의 필드와 값을 지정합니다. 기존 설정은 유지됩니다.
4. 객체를 선택하고 단축키를 누릅니다. 선택 객체가 없으면 수정하지 않습니다.

### 정렬 탐색

**Feature navigation and editing** 패널에서 레이어, 정렬 필드와 오름·내림차순을 지정합니다.
처음·이전·다음·마지막 이동, 순번·정렬값 표시, 자동 줌, 표현식 필터, 필드값 검색,
지도에서 객체 찍기를 지원합니다. 탐색한 레이어를 활성화하여 Alt+숫자 입력 대상과 일치시킵니다.

**Selected snapshot only**는 체크할 때의 선택 객체 범위를 고정합니다. 하나씩 탐색해도
범위가 줄어들지 않습니다. 범위를 바꾸려면 **Capture selection**을 누릅니다.
정렬·검색은 현재 필터와 선택 범위 안에서 작동합니다. 외부에서 객체나 필드가 바뀌면 목록을 다시 불러오세요.

Alt+좌우/Home/End 단축키는 기본적으로 꺼져 있습니다. 충돌을 피하려면 설치된 FeatureNavEd를
플러그인 관리자에서 비활성화한 뒤 **Enable Alt+Left/Right/Home/End navigation**을 체크하세요.
원본 FeatureNavEd 파일이나 설정을 자동으로 바꾸지 않습니다.

### 원하는 필드만 표시·다중 편집

객체를 하나 이상 선택하고 **Edit chosen fields / pending shortcuts...**를 엽니다.
**Choose visible / editable fields...**에서 표시·편집할 필드를 고릅니다.
창을 열 때의 선택 객체가 대상이며, 창을 열어 둔 채 지도 선택을 바꾸어도 대상은 바뀌지 않습니다.
다른 객체를 편집하려면 창을 닫고 다시 여세요.

**Change 필드명**을 체크한 필드만 **Apply form edits**로 적용합니다.
서로 다른 초기값이 있어도 체크하지 않은 필드는 덮어쓰지 않습니다.
창 안의 **Undo**는 미적용 폼 입력, 대기 중인 단축키 입력, 레이어의 최근 편집 순서로 되돌립니다.
실제 파일 저장은 QGIS의 편집 저장 기능으로 따로 수행합니다.

### Alt+숫자 즉시 적용·수동 적용 전환

**Apply Alt+1-9 immediately to layer edits**를 켜면 레이어 편집 상태에 즉시 적용합니다.
끄면 메모리에 값을 대기시킵니다. 미리보기를 확인한 뒤 **Apply pending shortcuts**로 적용하세요.
이 토글은 실제 파일의 자동 저장 여부가 아닙니다. 어떤 모드에서도 파일은 자동 저장하지 않습니다.

대기값은 단축키를 누른 시점의 선택 객체에 고정됩니다. 이후 선택·탐색을 바꾸어도 대상은 바뀌지 않습니다.
한 번에 한 레이어의 값만 대기시킬 수 있습니다. 토글을 바꾸어도 기존 대기값은 자동 적용되지 않습니다.
**Discard pending**으로 대기값을 지울 수 있으며, QGIS 재시작·플러그인 해제 시에는 대기값이 유지되지 않습니다.

폼의 표시 필드와 단축키 설정은 별개입니다. **Apply pending shortcuts**는 폼에서 숨긴 필드라도
설정된 모든 대기 단축키 값을 적용합니다. **Undo**의 레이어 실행 취소는 다른 도구가 만든 최근 편집도 포함할 수 있습니다.

문의: https://github.com/HaYanJongSeong/qgis-quick-field-keys/issues
