# hwp_manage

HWPX 자료를 단원별·책 전체로 병합하고, 이미지 참조와 본문 보존을 검사한 뒤 제출용 폴더와 ZIP을 만드는 재현 가능한 도구다. macOS와 Windows에서 같은 Python 명령을 사용한다.

빠른 시작은 [총정리](docs/00_총정리_목차.md)와 [사용자 매뉴얼](docs/01_사용자_매뉴얼.md)을 따른다.

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

실자료는 `작업폴더/목표2/국어 자료 변형 중간모음터/{책}/{n}단원/*.hwpx`에 넣고 실행한다.

```bash
python -m hwp_manage pipeline --workspace "작업폴더" --book "책 이름"
python -m hwp_manage verify --workspace "작업폴더" --book "책 이름"
```

이 저장소의 샘플은 출판사 자료가 아닌 합성 HWPX 3개다. 실제 교재 파일이나 저작권 자료는 포함하지 않는다.
