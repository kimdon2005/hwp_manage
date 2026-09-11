# 개발자 및 Codex 수정 매뉴얼

## 구성

```text
hwp_manage/
├── AGENTS.md                 # Codex가 자동으로 따라야 할 저장소 규칙
├── hwp_manage/
│   ├── cli.py               # 명령행 진입점
│   ├── common.py            # 정규화·해시·원자적 JSON 기록
│   ├── hwpx.py              # 검사·ID 재매핑·병합·보존 검증
│   ├── inventory.py         # 원본 종류·정답·HWP 변환 대기 분류
│   ├── pdf.py               # PDF 조각 병합·번호 처리
│   └── pipeline.py          # 책 단위 시퀀스·제출용·ZIP·검증
├── scripts/
│   ├── generate_samples.py  # 저작권 없는 합성 HWPX 생성
│   ├── setup.sh/.ps1
│   └── run_sample.sh/.ps1
├── examples/sample_workspace/
├── tests/
└── docs/
```

## 개발 환경

```bash
python -m venv .venv
python -m pip install -e ".[all]"
python -m pytest
```

Windows에서는 `python` 대신 `.venv\Scripts\python.exe`, macOS에서는 `.venv/bin/python`을 사용할 수 있다.

## 수정 안전 수칙

1. 파일명 비교 전에 NFC 정규화를 유지한다.
2. 번호 정렬에 단순 문자열 정렬을 쓰지 말고 `natural_key`를 사용한다.
3. 이미지 ID 변경에 반복 `str.replace()`를 사용하지 않는다.
4. XML을 문자열로 새로 조립할 때는 반드시 이스케이프한다.
5. 입력 HWPX는 쓰기 모드로 열지 않는다.
6. 출력은 같은 폴더의 임시 파일에 만들고 검사 후 `os.replace`한다.
7. HWPX의 `mimetype`은 첫 ZIP 항목이며 `ZIP_STORED`여야 한다.
8. 입력 섹션을 한 섹션에 이어 붙이지 말고 독립 섹션으로 보존한다.
9. 마스터페이지와 BinData manifest를 함께 갱신한다.
10. 검증 항목을 완화했다면 이유와 회귀 테스트를 문서화한다.

## 테스트 추가법

- 정상 파일: `inspect_hwpx(...)["ok"]`가 참인지 확인한다.
- 깨진 참조: manifest ID 또는 BinData를 의도적으로 누락해 실패를 확인한다.
- 병합: 섹션 본문 해시와 이미지 해시 목록이 입력 순서대로 보존되는지 확인한다.
- 패키지: ZIP 내부 매니페스트가 제출용 폴더와 완전히 같은지 확인한다.
- PDF: 두 개 이상의 합성 PDF를 만들고 페이지 수와 출력 열림을 확인한다.

샘플 재생성:

```bash
python scripts/generate_samples.py --root examples/sample_workspace
```

실제 출판사 HWPX를 테스트 fixture로 커밋하지 않는다.

## 코드 변경 후 필수 시퀀스

```bash
python -m pytest
python -m hwp_manage doctor --workspace examples/sample_workspace
python -m hwp_manage pipeline --workspace examples/sample_workspace --book "샘플 교과서"
python -m hwp_manage verify --workspace examples/sample_workspace --book "샘플 교과서"
git diff --check
git status --short
```

그 다음 새 임시 위치에 저장소를 다시 복제해 설치와 샘플 실행을 반복한다. 작업 중인 원본 폴더에서만 성공한 것은 배포 검증으로 보지 않는다.

## Codex 동작 수정

Codex의 기본 순서를 바꾸려면 `AGENTS.md`를 수정한다. 사용자용 설명은 `docs/01_사용자_매뉴얼.md`, 실제 재현 순서는 `docs/02_전체_재현_절차.md`, 실패 기준은 `docs/03_HWPX_무결성_및_장애대응.md`를 함께 갱신한다.

규칙과 코드가 다르면 코드를 수정하거나 문서에 제한을 명시한다. Codex에게만 숨은 지식을 두지 않는다.

## 새 기능 예시

### 새로운 제출 구조

`pipeline.py`의 `workspace_paths`, `run_book`, `verify_book`을 함께 변경하고 기존 구조와 새 구조 테스트를 모두 둔다.

### 새로운 이미지 형식

`hwpx.py`의 MIME 매핑을 추가하고 해당 확장자를 가진 BinData fixture로 병합 전후 해시 보존을 검사한다.

### Windows 한컴 자동화

별도 모듈로 구현하고 다음 조건을 둔다.

- 한컴 설치·버전·COM 등록 사전 검사
- 한 파일 제한 시험
- 입력 HWP 원본 불변 해시 확인
- 출력 HWPX `inspect` 통과 후 다음 파일 진행
- 실패 시 재개 가능한 로그

핵심 병합기와 UI 자동화를 결합하지 않는다.

## GitHub 배포

```bash
git add .
git commit -m "Add reproducible cross-platform HWPX pipeline"
git push origin main
```

원격 반영 후 새 디렉터리에 다시 `git clone`하고 `scripts/setup.*`, `scripts/run_sample.*`을 실행한다. GitHub Actions는 Ubuntu, macOS, Windows에서 Python 3.10과 3.12 조합을 검사한다.

비밀키, Google 인증 정보, 개인 경로, 실제 교재 파일, 대용량 최종본은 커밋하지 않는다.
