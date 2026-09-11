# HWPX 무결성 및 장애 대응

## 이미지가 뒤쪽에서 깨진 원인

구형 병합기는 이미지 ID를 문자열 `str.replace()`로 여러 번 순차 치환했다. 예를 들어 `img1 → img33`을 적용한 뒤, 새로 생긴 `img33` 일부가 다음 규칙의 입력으로 다시 잡히면서 존재하지 않는 `img82064` 같은 ID가 생성됐다. 문서 앞부분은 정상이어도 뒤쪽 섹션의 사진이 깨질 수 있었다.

현재 프로그램은 XML을 파싱하고 각 속성의 원래 값이 매핑 키와 정확히 같을 때 한 번만 새 ID로 바꾼다. 치환 결과를 같은 패스에서 다시 치환하지 않는다.

## 마스터페이지 누락

섹션의 `masterPage idRef`만 남고 다음 중 하나가 빠지면 마스터페이지 그림이 깨진다.

- `Contents/masterpageN.xml`
- `content.hpf` manifest 항목
- 섹션의 새 `idRef`
- 마스터페이지 내부 BinData ID
- 실제 `BinData/*` 파일

병합기는 위 다섯 요소를 함께 재매핑하고 `inspect`에서 끝까지 참조를 따라간다.

## 필수 검사 기준

- 섹션 수 = 모든 입력 섹션 수 합계
- 출력의 섹션별 본문 SHA-256 목록 = 입력 순서대로 이어 붙인 목록
- 출력의 섹션별 참조 이미지 SHA-256 목록 = 입력 순서대로 이어 붙인 목록
- 출력의 전체 BinData SHA-256 다중집합 = 입력 전체 다중집합
- 표·그림·수식 수 보존
- 존재하지 않는 이미지·마스터페이지 참조 0개
- XML 오류와 ZIP CRC 오류 0개

## 명령

```bash
python -m hwp_manage inspect "의심파일.hwpx"
python -m hwp_manage verify --workspace "작업폴더" --book "책 이름"
```

`errors`가 비어 있고 `ok=true`, 최종 검증의 `passed=true`여야 한다.

## 오류별 대응

### `not_a_zip`, `crc_error`

원본을 다시 복사하거나 한컴에서 새 이름으로 저장한다. 깨진 파일 위에 덮어쓰지 말고 정상 파일을 확보한 뒤 병합을 재실행한다.

### `mimetype_not_first`, `mimetype_not_stored`

HWPX 패키징 규칙 위반이다. 프로그램으로 다시 병합하면 `mimetype`을 첫 항목·무압축으로 쓴다.

### `missing_member`

`content.hpf`, `header.xml`, 섹션 등 필수 파트가 빠졌다. 원본 HWPX를 한컴에서 다시 저장한다.

### `missing_reference`, `missing_masterpage`

이미지나 마스터페이지 관계가 끊겼다. 손상 전체본을 부분 수정하지 말고 검증된 단원본에서 전체본을 다시 병합한다.

### 본문 또는 그림 해시 불일치

입력 순서가 바뀌었거나 병합기에서 내용이 소실된 것이다. 최종 파일은 교체되지 않아야 한다. 파일명 번호와 JSON 보고서의 `before`, `conservation`을 확인한다.

### 한컴에서는 깨지지만 자동 검사는 통과

자동 검사는 참조와 구조 보존을 확인하지만 실제 조판을 완전히 대신하지 않는다.

1. 한컴에서 원본 단원본이 정상인지 확인한다.
2. 전체본의 첫 페이지, 단원 경계, 그림이 많은 뒤쪽, 마지막 페이지를 본다.
3. Windows 한컴 환경에서는 실제 열림 자동 검사를 추가한다.
4. 글꼴·개체·OLE·차트처럼 이식이 어려운 요소는 해당 한컴 버전에서 다시 저장해 확인한다.

## PDF 번호 중첩

이미 번호를 넣은 단원 PDF를 전체 PDF의 입력으로 쓰면 번호가 겹친다. 단원·전체 모두 항상 원본 PDF 조각에서 각각 직접 만든다.

## 수정 후 회귀 검사

```bash
python -m pytest
python -m hwp_manage pipeline --workspace examples/sample_workspace --book "샘플 교과서"
python -m hwp_manage verify --workspace examples/sample_workspace --book "샘플 교과서"
```
