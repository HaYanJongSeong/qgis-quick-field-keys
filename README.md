# Quick Field Keys

객체를 하나씩 넘기면서 속성값을 입력하는 QGIS 플러그인입니다.
자주 쓰는 값은 단축키에 등록하고 직접 수정할 필드는 패널 아래에 꺼내 놓고 쓸 수 있습니다.

[설치 파일](https://github.com/HaYanJongSeong/qgis-quick-field-keys/releases/latest) · [오류 제보](https://github.com/HaYanJongSeong/qgis-quick-field-keys/issues) · [English](#english)

## 화면 예시

### 탐색·편집 패널

![Quick Field Keys 탐색·편집 패널 예시](https://raw.githubusercontent.com/HaYanJongSeong/qgis-quick-field-keys/main/docs/images/panel.png)

1.7.5의 테스트 레이어 화면입니다. `status`, `rank`는 예시 필드이며 실제로는 선택한 레이어의 필드가 표시됩니다.
위에서부터 레이어와 정렬, 필터, 객체 이동과 줌, 입력 설정, 필드 편집 순서입니다.

### 단축키 설정

![Quick Field Keys 단축키 설정 예시](https://raw.githubusercontent.com/HaYanJongSeong/qgis-quick-field-keys/main/docs/images/shortcuts.png)

Undo 오른쪽 톱니바퀴로 엽니다. 각 입력칸 옆의 X는 해당 키 지정을 비웁니다. 저장을 눌러야 적용됩니다. 취소하면 기존 설정을 유지합니다.
화면의 `Ctrl+Alt+N`과 해제된 프리셋 9는 테스트용 설정입니다. 기본 단축키는 아래 안내를 참고하세요.

## 설치

QGIS 3.44 LTR과 QGIS 4.2 이상, 4.x에서 사용합니다.
Windows의 QGIS 3.44.15 / Qt 5.15.13과 QGIS 4.2.2 / Qt 6.11에서 테스트했습니다.
3.44보다 오래된 QGIS 3 버전은 지원하지 않습니다. Linux와 macOS에서는 아직 확인하지 않았습니다.
별도 Python 패키지나 계정은 필요하지 않습니다.

1. [Releases](https://github.com/HaYanJongSeong/qgis-quick-field-keys/releases/latest)에서 `quick_field_keys_버전.zip`을 받습니다. 자동 생성된 Source code ZIP은 설치 파일이 아닙니다.
2. QGIS의 플러그인 관리 및 설치 > ZIP 파일에서 설치로 설치합니다.
3. 업데이트한 경우 QGIS를 재시작합니다. 기존 필드·값 프리셋은 유지됩니다.

## 기본 사용법

1. 툴바의 Quick Field Keys 아이콘을 눌러 패널을 엽니다.
2. 패널 맨 위에서 입력할 레이어를 지정합니다.
3. Field value presets...에서 단축키마다 필드와 값을 정합니다. 예를 들어 Alt+1은 `status = done`, Alt+2는 `status = review`로 둡니다.
4. 지정 레이어의 객체를 선택하고 단축키를 누릅니다. 여러 객체를 선택하면 모두 같은 값이 들어갑니다. 선택이 없으면 아무것도 바꾸지 않습니다.
5. 결과를 확인하고 디스크 아이콘으로 저장합니다.

**저장 버튼은 현재 객체만 저장하는 버튼이 아닙니다. 지정 레이어의 모든 미저장 편집을 파일에 저장합니다. 다른 QGIS 도구에서 수정한 내용도 함께 저장됩니다. 저장한 변경은 객체 Undo로 되돌릴 수 없습니다.**

단축키 입력 자체는 파일을 저장하지 않습니다. 즉시 적용을 켜면 편집 버퍼에 반영하고, 끄면 대기값으로 보관합니다.
저장 버튼은 미적용 필드와 대기값을 반영한 뒤 파일에 저장하며 편집 모드는 유지합니다.
파일 저장 없이 대기값만 반영하려면 플러그인 메뉴의 Apply pending shortcuts를 사용하세요.

QGIS 레이어 목록에서 다른 레이어를 눌러도 입력 대상은 패널에서 지정한 레이어입니다. 패널을 숨겨도 유지됩니다.
대상이 삭제되거나 비어 있으면 다른 레이어에 대신 쓰지 않습니다. 패널을 한 번도 열지 않은 경우에만 활성 레이어를 사용합니다.

## 이동과 필터

- Sort by로 정렬 필드를 고르고 Ascending으로 오름·내림차순을 바꿉니다.
- 처음·이전·다음·끝 버튼으로 이동합니다. 첫 객체에서 이전을 누르면 마지막으로, 마지막에서 다음을 누르면 처음으로 돌아갑니다.
- 객체를 이동할 때 자동으로 반짝입니다. 전구 버튼을 누르면 지정 레이어의 현재 선택 객체를 다시 반짝입니다. 선택이나 축척은 바꾸지 않습니다.
- 줌은 객체 맞춤, 현재 축척 유지, 고정 축척, 줌 안 함 중 고릅니다. No zoom에서도 반짝임은 동작합니다.
- 카메라와 왼쪽 화살표 버튼은 직전 선택과 화면으로 돌아갑니다. 필터는 바꾸지 않습니다. 화면 이력은 현재 실행 중 최근 100개입니다.
- 필터는 표현식을 입력한 뒤 새로고침을 눌러 적용합니다. 편집·Undo·정렬 중에는 조건을 다시 평가하지 않습니다. 레이어를 열거나 상태를 복원할 때는 목록을 한 번 생성합니다.
- 쓰레기통은 필터 입력만 비웁니다. 그 변경도 새로고침해야 적용됩니다. 객체를 삭제하지 않습니다.
- Use current selection은 현재 선택 범위를 고정합니다. Captured selection only를 켜면 그 범위 안에서만 이동합니다.

필터는 플러그인의 이동 목록에만 적용됩니다. 레이어의 원본 데이터나 provider 필터는 바꾸지 않습니다.

## 필드 편집과 Undo

눈 아이콘으로 패널 아래에 표시할 필드를 고릅니다. 입력을 바꾼 필드만 반영합니다. 다중 선택에서 값이 섞여 있어도 건드리지 않은 필드는 덮어쓰지 않습니다.

입력칸 오른쪽 Lock은 이 플러그인의 폼·프리셋·대기값 적용·Undo에서 해당 필드에 새 값을 쓰는 것을 막습니다.
다른 QGIS 도구의 편집을 잠그거나, 이미 편집 버퍼에 있는 값의 파일 저장을 막지는 않습니다.
잠금과 표시 필드는 레이어별로 기억합니다.

미적용 입력이 있으면 이동 전에 폐기 여부를 묻습니다. 외부에서 선택을 바꿔도 미적용 입력의 대상은 바뀌지 않습니다.
대기 프리셋도 입력 당시의 선택 객체에 묶입니다. 한 번에 한 레이어만 대기시킬 수 있습니다.
대기값은 재시작 후 남지 않습니다. 플러그인 메뉴의 Discard pending shortcuts로 버릴 수 있습니다.

객체 Undo는 마지막 선택 객체에 연속 입력한 플러그인 변경을 묶어서 되돌립니다. 다중 선택도 한 묶음입니다.
복원한 객체는 선택하고 화면을 맞춘 뒤 반짝입니다. 필터 밖이거나 No zoom이어도 해당 객체로 이동합니다.
다른 도구의 편집은 되돌리지 않으며, 같은 필드에 외부 변경이 생겼으면 복원을 중단합니다.
최근 200묶음을 현재 세션에서 보관합니다. 저장·롤백·외부 레이어 Undo·레이어 삭제·재시작 후에는 해당 이력을 사용할 수 없습니다.

## 기본 단축키

- Alt+1~9: 등록한 필드·값 입력
- Alt+Left / Right: 이전 / 다음
- Alt+Home / End: 처음 / 끝
- Alt+Backspace: 직전 화면
- Alt+Z: 객체 Undo

톱니바퀴 설정에서 바꾸거나 해제할 수 있습니다. 저장·반짝임 등 나머지 기능은 기본 키가 없으므로 필요한 경우 지정하세요.
중복 키, 다른 QGIS 단축키와 충돌하는 키, 일반 문자만 사용하는 키, 여러 단계의 키 조합은 받지 않습니다.
다른 QGIS 단축키는 변경하지 않습니다.

이동 단축키는 패널이 보일 때만 동작합니다. FeatureNavEd가 켜져 있으면 겹치는 이동 단축키를 중지합니다.
마지막 레이어·필터·정렬·순번·패널 위치는 기억합니다. 버튼에 마우스를 올리면 영어와 한국어 설명이 나옵니다.

## 입력 시 참고

값은 표현식이 아닌 문자 그대로 입력합니다. 빈 문자열과 NULL은 다릅니다. NULL을 넣으려면 Set NULL을 선택하세요.
숫자 필드에 맞지 않는 값은 거부합니다. provider 기본키, 조인 필드, 표현식 필드는 입력 대상에서 제외합니다.
다른 필드의 기본값 재계산은 건너뜁니다. 필드 제약이나 데이터 제공자의 규칙 때문에 저장이 실패할 수 있으니 결과를 확인하세요.
실패하면 오류를 표시합니다. 편집 버퍼를 임의로 롤백하지 않습니다. 선택 객체가 많으면 입력 중 QGIS가 잠시 멈출 수 있습니다.

## English

Quick Field Keys is a QGIS plugin for stepping through features and entering repeated attribute values with shortcuts.
Choose the target layer in the panel, configure field/value presets, select features, and press a preset key.
The screenshots above show version 1.7.5 with test fields and example shortcut assignments, not the default bindings.

Download the installation ZIP from [Releases](https://github.com/HaYanJongSeong/qgis-quick-field-keys/releases/latest) and use Plugins > Manage and Install Plugins > Install from ZIP. Restart QGIS after updating.
Supports QGIS 3.44 LTR and QGIS 4.2+ in the 4.x series. Tested on Windows with QGIS 3.44.15 / Qt 5.15.13 and QGIS 4.2.2 / Qt 6.11. Earlier QGIS 3 releases are unsupported; Linux/macOS are untested. No extra packages or accounts are needed.

- Default keys: Alt+1–9 for presets, Alt+Left/Right/Home/End for navigation, Alt+Backspace for the previous view, Alt+Z for feature Undo. The gear dialog changes or clears bindings; Save applies them.
- Changes apply to the panel's designated layer, even when another layer is active or the panel is hidden. No selection means no changes.
- Navigation flashes the destination. The bulb flashes the current selection without changing the view. Both work in No zoom mode.
- Refresh explicitly applies the filter. Trash clears its input only. Editing and Undo do not re-evaluate filter membership.
- Use the eye icon to choose inline fields. Locks block this plugin's new writes, not other tools or persistence of existing edits. Drafts and staged presets keep their original targets.
- **The disk button commits all unsaved edits in the designated layer, including other tools' edits. It applies drafts and pending presets first. Saved changes cannot be restored by feature Undo.** Preset entry does not save automatically.
- Feature Undo groups consecutive plugin changes to the last selection and protects external edits. History is limited to 200 groups in the current session. Save, rollback, external Undo, layer removal and restart invalidate it.
- Use Set NULL for NULL. Primary keys, joined fields and expression fields are excluded. Invalid values or provider constraints may prevent changes or saving; check the reported result.

## 개발 / Development

QGIS Python 콘솔에서 저장소 경로를 바꿔 다음 테스트를 실행하세요.

```python
from pathlib import Path
root = Path('/path/to/qgis-quick-field-keys')
for name in ('test_qgis.py', 'test_navigation.py'):
    test = root / 'tests' / name
    exec(compile(test.read_text(encoding='utf-8'), str(test), 'exec'), {'__file__': str(test)})
```

The tests use an isolated project and canvas with memory layers. They do not edit the current project or its files.
For a standalone run, use the chosen QGIS installation's Python environment to run `tests/run_qgis.py`. It also checks Save by reopening a temporary GeoPackage. The test profile and data are separate from your QGIS profile and project.
They cover presets, navigation, filters, locks, shortcut settings, Save and Undo. Physical keyboard input and installation through Plugin Manager are separate manual checks.

```sh
python build_release.py /path/to/output
```

## 문의와 라이선스

- 관리: [HaYanJongSeong](https://github.com/HaYanJongSeong), kjs4075@live.com
- 오류 제보·기능 요청: [Issues](https://github.com/HaYanJongSeong/qgis-quick-field-keys/issues)
- 라이선스: [GPL-3.0-or-later](LICENSE)

탐색 방식은 Irene Jaya의 FeatureNavEd 1.0.8을 참고했습니다. 구현은 별도이며 원본의 MIT 라이선스를 [LICENSE.FeatureNavEd](LICENSE.FeatureNavEd)에 남겼습니다.
[원본 저장소](https://github.com/irenejaya/feature-navigator-editor)
