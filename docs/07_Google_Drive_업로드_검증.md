# Google Drive 업로드 및 검증

## 대상

로컬 `국어 자료 최종본 모음` 아래의 다음 항목만 배포한다.

- `2. * 제출용` 폴더 내부 파일
- 책별 ZIP

작업용 폴더, 백업, 보고서, `.DS_Store`는 올리지 않는다.

## Codex Google Drive 플러그인 방식

1. 사용자가 제공한 정확한 Drive 폴더 URL 또는 ID를 먼저 조회한다.
2. 현재 원격 폴더의 책별 제출용 폴더와 ZIP의 파일 ID를 기록한다.
3. 로컬 `python -m hwp_manage verify`가 통과했는지 확인한다.
4. 기존 원격 파일이 있으면 Drive `files.update` 방식으로 바이트만 교체해 파일 ID와 공유 설정을 유지한다.
5. 없는 파일만 정확한 부모 폴더에 새로 업로드한다.
6. 이름 중복이 생기지 않았는지 폴더를 다시 조회한다.
7. 원격 파일 크기·수정 시각을 확인한다.
8. 가능하면 원격 파일을 다시 내려받아 SHA-256를 비교한다.

플러그인이 `USER_NOT_LOGGED_IN` 또는 `not connected`를 반환하면 업로드는 이루어지지 않은 것이다. Google Drive 연결을 다시 승인한 뒤 첫 폴더 조회부터 재실행한다.

## 다운로드 기반 독립 검증

기존 작업공간에는 `목표2/etc/verify_google_drive_uploads.py`가 있으며, `gdown`으로 원격 파일을 하나씩 임시 다운로드해 비교한다. GitHub 저장소는 인증 방식과 대상 Drive가 사용자별로 달라 이 스크립트를 핵심 패키지에 묶지 않고 절차만 보존한다.

macOS/Linux 예시:

```bash
python3 -m venv .drive-verify-venv
.drive-verify-venv/bin/pip install gdown
.drive-verify-venv/bin/python verify_google_drive_uploads.py \
  "GOOGLE_DRIVE_FOLDER_URL" \
  "목표2/국어 자료 최종본 모음" \
  --gdown ".drive-verify-venv/bin/gdown" \
  --json-report "검증결과.json" \
  --md-report "검증결과.md"
```

Windows에서는 `.drive-verify-venv\Scripts\python.exe`와 `.drive-verify-venv\Scripts\gdown.exe`를 사용한다.

## 비교 항목

- 원격·로컬 상대 경로 집합
- 전체 파일 크기와 SHA-256
- HWPX ZIP 내부 항목 경로와 항목별 SHA-256
- HWPX BinData 이미지 경로와 이미지별 SHA-256
- 책 ZIP CRC와 내부 파일별 SHA-256
- 원격에만 있거나 로컬에만 있는 항목

## 판정

- `exact`: 파일 전체 바이트 동일
- `different`: 동일 경로지만 해시 다름
- `remote_only`: Drive에만 있음
- `local_only`: 로컬에만 있음
- `download_error`: 내려받지 못해 판정 불가

`different`, `local_only`, `download_error`가 하나라도 있으면 완료가 아니다. `.DS_Store`도 완전한 집합 비교에서는 `remote_only`로 보고 정확한 원격 파일 ID를 확인한 뒤 제거한다.

## 현재 작업의 주의점

2026-08-31 검증은 당시 로컬 68개와 원격을 대조한 기록이다. 이후 해냄 최종본과 전체 HWPX 3개가 수정됐으므로 이 과거 결과를 최신 업로드 증거로 사용하면 안 된다. 최신 로컬본을 업로드한 뒤 새 날짜의 보고서를 만들어야 한다.

상세 현재 상태는 [04 작업 이력과 현재 상태](04_작업이력_및_현재상태.md)를 본다.
