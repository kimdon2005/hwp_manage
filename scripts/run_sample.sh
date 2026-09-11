#!/usr/bin/env sh
set -eu
.venv/bin/python -m hwp_manage pipeline \
  --workspace examples/sample_workspace \
  --book '샘플 교과서'
