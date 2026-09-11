# Codex 작업 지침

이 저장소에서 HWPX 병합·검수 요청을 받으면 다음 순서를 따른다.

## 처음 설치 또는 기본 세팅 요청

사용자가 `docs/08_Codex_기본세팅_프롬프트.md`의 프롬프트를 붙여 넣거나 처음 설치를 요청하면 다음 순서를 따른다.

1. 저장소 루트인지 `README.md`, `AGENTS.md`, `pyproject.toml`, `scripts/`로 확인한다.
2. 운영체제와 Python 3.10 이상 사용 가능 여부를 확인한다.
3. macOS/Linux는 `sh scripts/setup.sh`, Windows는 `powershell -ExecutionPolicy Bypass -File scripts\setup.ps1`을 실행한다.
4. 설치 스크립트가 수행한 전체 자동 테스트의 성공을 확인한다.
5. 운영체제에 맞는 `scripts/run_sample.*`을 실행하고 결과의 모든 `passed`가 `true`인지 확인한다.
6. `사용자작업/목표2/국어 자료 변형 중간모음터/`와 `사용자작업/목표2/국어 자료 PDF 조각/`을 만든다.
7. 빈 사용자작업 폴더의 `doctor` 종료 코드 2는 설치 실패로 보지 않는다. 실제 책 폴더를 넣은 뒤 다시 검사한다.
8. 실제 사용자 파일은 기본 세팅 단계에서 처리하지 않는다.
9. 테스트·샘플·폴더 준비가 모두 확인되었을 때만 `기본 세팅 완료`라고 보고한다.
10. Python 또는 권한처럼 사용자가 직접 해결해야 하는 문제가 있으면 성공으로 보고하지 말고, 필요한 행동을 쉬운 말로 한 단계씩 안내한다.

## 실제 자료 처리 요청

1. `docs/00_총정리_목차.md`와 요청에 해당하는 연결 문서를 읽는다.
2. 설치 후 명령은 macOS/Linux의 `.venv/bin/python`, Windows의 `.venv\Scripts\python.exe`처럼 저장소의 가상환경 Python을 사용한다.
3. `python -m hwp_manage doctor --workspace <작업폴더>`로 폴더와 의존성을 확인한다.
4. 원본 목록 정리가 필요하면 `python -m hwp_manage inventory --workspace <작업폴더> --book <책>`으로 정답 판정과 HWP 변환 대기를 기록한다.
5. 원본 `.hwp`는 수정·삭제·자동 변환하지 않는다. 이 프로그램의 자동 병합 입력은 `.hwpx`다.
6. 입력은 `목표2/국어 자료 변형 중간모음터/{책}/{n}단원/`에 두고 자연 정렬 순서를 확인한다.
7. `python -m hwp_manage pipeline --workspace <작업폴더> --book <책>`을 실행한다. 대응하는 PDF 조각이 있고 사용자가 PDF 결과도 원하면 `--pdf`를 붙인다.
8. `python -m hwp_manage verify --workspace <작업폴더> --book <책>`를 별도로 다시 실행한다.
9. JSON 보고서의 `passed`가 모두 `true`일 때만 완료로 보고한다.
10. 병합 전후 섹션 본문 해시, 섹션별 이미지 해시, BinData 해시, 표·그림·수식 수가 보존되어야 한다.
11. ZIP에는 제출용 폴더의 내용물만 넣고 `.DS_Store`, `_work`, 보고서는 넣지 않는다.
12. 프로그램 수정 후 `python -m pytest`와 샘플 파이프라인을 모두 실행한다.

HWP를 HWPX로 바꾸는 작업은 한컴오피스의 실제 저장 기능을 우선한다. macOS와 Windows의 UI 자동화 방식이 다르므로, 자동화 권한과 한컴 버전이 확인되지 않은 상태에서 화면 매크로를 임의 실행하지 않는다.
