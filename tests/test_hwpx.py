from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

from hwp_manage.hwpx import inspect_hwpx, merge_hwpx
from hwp_manage.inventory import is_answer_name
from hwp_manage.pdf import merge_pdfs
from hwp_manage.pipeline import run_book, verify_book


ROOT = Path(__file__).resolve().parents[1]
SAMPLE = ROOT / "examples" / "sample_workspace"


def sample_files() -> list[Path]:
    source = SAMPLE / "목표2" / "국어 자료 변형 중간모음터"
    return sorted(source.rglob("*.hwpx"))


def test_samples_are_valid() -> None:
    files = sample_files()
    assert len(files) == 3
    assert all(inspect_hwpx(path)["ok"] for path in files)
    assert any(inspect_hwpx(path)["pictures"] == 1 for path in files)


def test_merge_preserves_text_and_images(tmp_path: Path) -> None:
    inputs = sorted((SAMPLE / "목표2" / "국어 자료 변형 중간모음터" / "샘플 교과서" / "1단원").glob("*.hwpx"))
    output = tmp_path / "merged.hwpx"
    report = merge_hwpx(inputs, output, title="병합 테스트")
    assert report["passed"]
    assert report["after"]["sections"] == 2
    assert report["after"]["pictures"] == 1
    assert report["after"]["missing_references"] == []


def test_full_pipeline_and_zip(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    shutil.copytree(SAMPLE, workspace)
    result = run_book(workspace, "샘플 교과서")
    assert result["passed"]
    checked = verify_book(workspace, "샘플 교과서")
    assert checked["passed"]
    assert checked["zip"]["file_count"] == 3


def test_module_cli_doctor() -> None:
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "hwp_manage",
            "doctor",
            "--workspace",
            str(SAMPLE),
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
    )
    assert result.returncode == 0, result.stderr


def test_pdf_merge(tmp_path: Path) -> None:
    import fitz

    inputs = []
    for index in range(2):
        path = tmp_path / f"{index + 1}.pdf"
        document = fitz.open()
        page = document.new_page()
        page.insert_text((72, 72), f"synthetic page {index + 1}")
        document.save(path)
        document.close()
        inputs.append(path)
    output = tmp_path / "merged.pdf"
    assert merge_pdfs(inputs, output) == 2
    with fitz.open(output) as merged:
        assert merged.page_count == 2


def test_answer_classification() -> None:
    assert is_answer_name("정답과 해설")
    assert is_answer_name("예시 답안")
    assert is_answer_name("예시답안 및 평가 기준")
    assert not is_answer_name("수행 평가")
