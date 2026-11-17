# Quick Field Keys

지정한 QGIS 레이어의 객체를 탐색하고 단축키로 속성값을 반복 입력하는 플러그인입니다. 2.0.0은 Python 단독으로 실행하며 플러그인 자체의 Rust 확장·DLL을 설치하거나 불러오지 않습니다.

[설치 ZIP](https://github.com/HaYanJongSeong/qgis-quick-field-keys/releases/latest) · [변경 이력](CHANGELOG.md) · [오류 제보](https://github.com/HaYanJongSeong/qgis-quick-field-keys/issues) · [English](#english)

## 설치와 검증 범위

QGIS 3.44 LTR과 QGIS 4.2 이상 4.x를 대상으로 합니다. 별도 Python 패키지나 계정은 필요하지 않습니다.

1. Releases에서 `quick_field_keys_2.0.0.zip`을 받습니다. 자동 생성된 Source code ZIP은 설치 파일이 아닙니다.
2. QGIS의 **플러그인 관리 및 설치 → ZIP 파일에서 설치**에서 선택합니다.
3. 업데이트 후 QGIS를 재시작합니다. 기존 프리셋과 단축키 설정은 유지합니다. 재시작하면 미적용 입력·대기값·객체 Undo 이력은 사라지므로 필요한 작업을 먼저 정리하세요.

Python 2.0.0의 회귀·정책·위젯·반복 로드/언로드와 임시 GeoPackage 저장·재열기는 Windows QGIS 4.2.3 / Qt 6.11의 격리된 프로세스에서 검사했습니다. QGIS 3.44, Linux/macOS, 물리 키보드와 Plugin Manager 설치는 이번 버전에서 확인하지 않았습니다. 과거 검증 기록은 CHANGELOG.md에 있습니다.

## 사용

1. 툴바 아이콘으로 패널을 열고 입력할 레이어를 지정합니다.
2. `Shortcuts for value apply to Field`에서 단축키별 필드와 값을 정합니다. 예: Alt+1은 `status = done`, Alt+2는 `status = review`.
3. 지정 레이어에서 객체를 선택하고 단축키를 누릅니다. 여러 객체를 선택하면 모두 적용하고, 선택이 없으면 변경하지 않습니다.
4. 결과를 확인한 뒤 디스크 아이콘으로 저장합니다.

프리셋은 기본으로 편집 버퍼에 즉시 적용합니다. 이전의 비활성 설정은 무시하며 모드를 바꾸는 체크박스는 없습니다. 프리셋·눈·저장·객체 Undo·설정은 한 줄에 있습니다.

**Save는 현재 객체만 저장하지 않습니다. 다른 도구의 편집까지 포함해 지정 레이어의 모든 미저장 편집을 저장합니다. 파일 자동 저장은 없으며, 저장한 변경은 객체 Undo로 되돌릴 수 없습니다.**

저장 전에 미적용 입력과 대기값을 반영합니다. 같은 필드에는 폼 입력이 우선합니다. 저장 후에도 편집 모드를 유지하며, 실패하면 오류를 표시하고 버퍼를 임의로 롤백하지 않습니다.

다른 레이어를 활성화하거나 패널을 숨겨도 입력 대상은 유지합니다. 지정 대상이 삭제되거나 유효하지 않으면 다른 레이어에 대신 쓰지 않습니다. 패널을 한 번도 열지 않았을 때만 활성 레이어를 사용합니다.

## 탐색과 필터

- 정렬 필드와 방향을 지정하고 처음·이전·다음·끝으로 이동합니다. 첫 객체의 이전은 마지막으로, 마지막의 다음은 처음으로 순환합니다.
- 표현식 필터는 새로고침을 눌러 적용합니다. 편집·Undo·정렬은 필터를 다시 평가하지 않습니다. 쓰레기통은 필터 입력만 비우며 새로고침해야 반영합니다. 데이터나 provider 필터는 바꾸지 않습니다.
- Use current selection으로 선택 범위를 캡처하고 Captured selection only로 탐색 범위를 제한합니다.
- 줌은 객체 맞춤·현재 축척 유지·고정 축척·No zoom 중 선택합니다. 이동 시 자동으로 반짝이며 전구는 현재 선택을 다시 반짝입니다. No zoom에서도 반짝이고 선택·축척은 바꾸지 않습니다.
- 카메라와 왼쪽 화살표는 필터와 무관하게 직전 선택·화면을 복원합니다. 화면 이력은 세션당 최근 100개입니다.
- 마지막 레이어·적용 필터·정렬·순번·패널 위치를 기억합니다. 지도 테마 전환은 배경을 포함한 저장된 레이어 표시·스타일 전체를 적용하며, 입력 대상과 미저장 편집은 유지합니다. UI 테마 전환은 아닙니다.

## 필드 편집과 Undo

눈 아이콘으로 편집할 필드를 고릅니다. 바꾼 필드만 반영하며, 다중 선택에서 값이 섞여 있어도 건드리지 않은 필드는 덮어쓰지 않습니다. 필드 잠금은 이 플러그인의 폼·프리셋·대기값·Undo 쓰기를 막지만 다른 QGIS 도구나 기존 편집의 저장은 막지 않습니다. 표시 필드와 잠금은 레이어별로 기억합니다.

직접 입력한 초안은 이동 전에 원래 대상의 편집 버퍼에 반영합니다. 외부 선택·필터 변경은 초안 대상을 바꾸지 않습니다. 잘못된 값·잠금·쓰기 실패는 입력을 보존하고 이동을 막습니다. 프리셋은 실제 반영한 필드만 갱신하며 관계없는 초안을 보존합니다. 같은 필드의 초안은 캡처 대상 전체에 쓰기가 성공했을 때만 대체합니다.

대기값은 입력 당시의 대상에 묶이며 한 번에 한 레이어만 대기시킬 수 있습니다. 파일 저장 없이 적용하거나 버리려면 플러그인 메뉴의 Apply pending shortcuts / Discard pending shortcuts를 사용합니다.

객체 Undo는 마지막 선택 집합에 연속 입력한 플러그인 변경을 묶어 복원하고 대상 객체를 선택·화면 맞춤·반짝임으로 표시합니다. 필터 밖이나 No zoom에서도 복원 대상을 표시합니다. 다른 도구의 편집은 되돌리지 않으며 같은 필드의 외부 변경, 누락 대상이나 복원 실패가 있으면 중단합니다. 최근 200묶음을 세션 메모리에 보관합니다. 저장·롤백·외부 레이어 Undo·삭제·재시작 후에는 해당 이력을 사용할 수 없습니다.

값은 표현식이 아닌 문자 그대로 입력합니다. 빈 문자열과 NULL은 다릅니다. NULL에는 Set NULL을 사용하세요. 잘못된 숫자 입력은 거부하며 기본키·조인·표현식 필드는 제외합니다. 다른 필드의 기본값 재계산은 건너뜁니다. provider 제약으로 저장이 실패할 수 있으며 큰 선택 집합은 처리 중 잠시 멈출 수 있습니다.

## 기본 단축키

| 키 | 동작 |
|---|---|
| Alt+1~9 | 프리셋 적용 |
| Alt+Left / Right | 이전 / 다음 |
| Alt+Home / End | 처음 / 끝 |
| Alt+Up / Down | 이전 / 다음 지도 테마 |
| Alt+Backspace | 직전 화면 |
| Alt+Z | 객체 Undo |

설정에서 키를 바꾸거나 비우며 기본값으로 복원할 수 있습니다. 중복·외부 충돌·일반 문자만 사용하는 키·여러 단계의 키 조합은 받지 않습니다. 다른 QGIS 단축키는 변경하지 않습니다. 저장·반짝임 등 나머지 기능은 기본 키가 없습니다. 탐색과 지도 테마 단축키는 패널이 보일 때만 동작하며 FeatureNavEd와 겹치는 탐색 키는 중지합니다.

## English

Quick Field Keys navigates features and applies repeated attribute values to a designated QGIS layer. Version 2.0.0 runs entirely in Python, with no plugin-owned native binaries or extra dependencies.

Install the release ZIP through **Plugins → Manage and Install Plugins → Install from ZIP**, then restart QGIS after updating. Restarting discards unapplied inputs, pending values and feature Undo history. Targets are QGIS 3.44 LTR and QGIS 4.2+ in the 4.x series. Python 2.0.0 tests use isolated Windows QGIS 4.2.3 / Qt 6.11 processes. QGIS 3.44, Linux/macOS, physical keyboard use and Plugin Manager installation are unverified for this release.

- Choose a layer, configure field/value presets and select features. Alt+1–9 immediately writes to the edit buffer, never automatically to a file. No selection means no changes. Changing the active layer does not retarget writes; invalid designated targets never fall back to another layer.
- The preset, field visibility, Save, feature Undo and settings controls share one row. Immediate-mode checkboxes and the mode-toggle shortcut are removed. Configure or clear keys in settings; duplicate, bare typing, multistroke and conflicting keys are refused without changing other QGIS shortcuts.
- Navigation wraps at both ends. Filters change only on explicit refresh; trash clears the input, not features. Captured selection can restrict navigation. Zoom modes include No zoom; navigation and the bulb can flash features without changing their attributes.
- Drafts keep their captured targets and apply before navigation. Invalid inputs, locks and failed writes preserve drafts and block movement. Successful presets refresh only affected fields; unrelated and partial-target drafts remain intact. Locks affect this plugin, not other tools.
- **Save commits all unsaved edits in the designated layer, including other tools' edits. It applies drafts and pending values first, keeps editing enabled and retains the buffer on failure. Saved changes cannot be restored by feature Undo.**
- Feature Undo groups consecutive edits to the last selection, protects external changes and retains up to 200 groups in the current session. Saving, rollback, external Undo, layer removal and restart invalidate history.
- Alt+Left/Right/Home/End navigates, Alt+Backspace restores the previous view, Alt+Z invokes feature Undo, and Alt+Up/Down cycles whole saved map themes while the panel is visible. Themes retain the editing target and unsaved attributes. They are not UI themes.
- Use Set NULL for NULL. Primary keys, joined and expression fields are excluded. Invalid types and provider constraints can prevent changes or saving; check the reported result.

## Development

Run in the chosen QGIS installation's Python environment, not its live Python console:

```text
python tests/run_python_qgis.py test_python_ui_lifecycle.py test_python_policies.py test_qgis.py test_navigation.py test_optimization.py test_bulk_reads.py
python build_release.py /path/to/output
```

Tests isolate profiles, projects and fixture data; the runner blocks this plugin's native loads before import. They cover policy boundaries, aliases, Qt widgets, lifecycle, preset/Undo failures, captured drafts, themes and temporary GeoPackage Save/reopen. CLI/automated checks do not prove physical keyboard use or manual installation. Historical native tests and Rust development sources are retained separately, not used as the Python release gate.

## License and contact

GPL-3.0-or-later. Maintainer: [HaYanJongSeong](https://github.com/HaYanJongSeong), kjs4075@live.com.

Navigation draws on Irene Jaya's FeatureNavEd 1.0.8; implementation is separate. Its MIT attribution is retained in [LICENSE.FeatureNavEd](LICENSE.FeatureNavEd). [Original repository](https://github.com/irenejaya/feature-navigator-editor).
