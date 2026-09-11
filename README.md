# hwp_manage

HWPX 자료를 단원별·책 전체로 병합하고, 이미지 참조와 본문 보존을 검사한 뒤 제출용 폴더와 ZIP을 만드는 재현 가능한 도구다. macOS와 Windows에서 사용할 수 있다.

## 컴퓨터 초보자 빠른 시작

터미널 명령을 몰라도 된다.

1. 초록색 **Code → Download ZIP**으로 이 저장소를 받는다.
2. 압축을 푼 폴더를 Codex에서 연다.
3. [Codex 기본 세팅 프롬프트](docs/08_Codex_기본세팅_프롬프트.md)를 Codex에 그대로 붙여 넣는다.
4. Codex가 만든 `사용자작업/목표2/국어 자료 변형 중간모음터/`에 HWPX를 넣는다.
5. [사용자 매뉴얼](docs/01_사용자_매뉴얼.md)의 실제 작업 프롬프트를 붙여 넣는다.

전체 설명은 [총정리](docs/00_총정리_목차.md)에서 찾을 수 있다.

## 명령으로 설치하는 방법

```bash
git clone https://github.com/kimdon2005/hwp_manage.git
cd hwp_manage
```

macOS/Linux:

```bash
sh scripts/setup.sh
sh scripts/run_sample.sh
```

Windows PowerShell:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\setup.ps1
powershell -ExecutionPolicy Bypass -File scripts\run_sample.ps1
```

실자료는 `작업폴더/목표2/국어 자료 변형 중간모음터/{책}/{n}단원/*.hwpx`에 넣고 실행한다. 기본 세팅 프롬프트를 사용했다면 `작업폴더`는 저장소 안의 `사용자작업`이다.

```bash
python -m hwp_manage pipeline --workspace "작업폴더" --book "책 이름"
python -m hwp_manage verify --workspace "작업폴더" --book "책 이름"
```

이 저장소의 샘플은 출판사 자료가 아닌 합성 HWPX 3개다. 실제 교재 파일이나 저작권 자료는 포함하지 않는다.
