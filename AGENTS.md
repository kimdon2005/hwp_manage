# Codex 작업 지침

이 저장소에서 HWPX 병합·검수 요청을 받으면 다음 순서를 따른다.

1. `docs/00_총정리_목차.md`와 요청에 해당하는 연결 문서를 읽는다.
2. `python -m hwp_manage doctor --workspace <작업폴더>`로 폴더와 의존성을 확인한다.
3. 원본 목록 정리가 필요하면 `python -m hwp_manage inventory --workspace <작업폴더> --book <책>`으로 정답 판정과 HWP 변환 대기를 기록한다.
4. 원본 `.hwp`는 수정·삭제·자동 변환하지 않는다. 이 프로그램의 자동 병합 입력은 `.hwpx`다.
5. 입력은 `목표2/국어 자료 변형 중간모음터/{책}/{n}단원/`에 두고 자연 정렬 순서를 확인한다.
6. `python -m hwp_manage pipeline --workspace <작업폴더> --book <책>`을 실행한다.
7. `python -m hwp_manage verify --workspace <작업폴더> --book <책>`를 별도로 다시 실행한다.
8. JSON 보고서의 `passed`가 모두 `true`일 때만 완료로 보고한다.
9. 병합 전후 섹션 본문 해시, 섹션별 이미지 해시, BinData 해시, 표·그림·수식 수가 보존되어야 한다.
10. ZIP에는 제출용 폴더의 내용물만 넣고 `.DS_Store`, `_work`, 보고서는 넣지 않는다.
11. 프로그램 수정 후 `python -m pytest`와 샘플 파이프라인을 모두 실행한다.

HWP를 HWPX로 바꾸는 작업은 한컴오피스의 실제 저장 기능을 우선한다. macOS와 Windows의 UI 자동화 방식이 다르므로, 자동화 권한과 한컴 버전이 확인되지 않은 상태에서 화면 매크로를 임의 실행하지 않는다.
