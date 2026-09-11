#!/usr/bin/env sh
set -eu
python3 -m venv .venv
.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install -e '.[all]'
.venv/bin/python -m pytest
printf '%s\n' '설치와 자동 테스트가 완료되었습니다.'
