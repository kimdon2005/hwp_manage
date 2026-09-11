$ErrorActionPreference = "Stop"
py -3 -m venv .venv
& .venv\Scripts\python.exe -m pip install --upgrade pip
& .venv\Scripts\python.exe -m pip install -e ".[all]"
& .venv\Scripts\python.exe -m pytest
Write-Host "설치와 자동 테스트가 완료되었습니다."
