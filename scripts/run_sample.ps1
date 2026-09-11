$ErrorActionPreference = "Stop"
& .venv\Scripts\python.exe -m hwp_manage pipeline `
  --workspace examples\sample_workspace `
  --book "샘플 교과서"
