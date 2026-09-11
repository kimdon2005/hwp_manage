from __future__ import annotations

import hashlib
import os
import re
import shutil
import tempfile
from pathlib import Path
from typing import Any
from zipfile import ZIP_DEFLATED, ZipFile

from .common import natural_key, nfc, sha256_file, timestamp, write_json_atomic
from .hwpx import inspect_hwpx, merge_hwpx
from .pdf import merge_pdfs


def workspace_paths(workspace: Path) -> dict[str, Path]:
    root = workspace.expanduser().resolve()
    target = root / "목표2"
    return {
        "workspace": root,
        "target": target,
        "variant": target / "국어 자료 변형 중간모음터",
        "final": target / "국어 자료 최종본 모음",
        "pdf_parts": target / "국어 자료 PDF 조각",
    }


def discover_books(workspace: Path) -> list[str]:
    variant = workspace_paths(workspace)["variant"]
    if not variant.is_dir():
        return []
    return sorted(
        (nfc(path.name) for path in variant.iterdir() if path.is_dir()),
        key=str.casefold,
    )


def _unit_number(path: Path) -> int:
    match = re.search(r"(\d+)단원", nfc(path.name))
    if not match:
        raise ValueError(f"단원 번호를 찾을 수 없습니다: {path}")
    return int(match.group(1))


def _unit_directories(book_root: Path) -> list[Path]:
    units = [
        path
        for path in book_root.iterdir()
        if path.is_dir() and re.search(r"\d+단원", nfc(path.name))
    ]
    return sorted(units, key=_unit_number)


def _atomic_copy(source: Path, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_name(f".{destination.name}.tmp")
    shutil.copy2(source, temporary)
    os.replace(temporary, destination)
    if sha256_file(source) != sha256_file(destination):
        raise RuntimeError(f"복사 해시 불일치: {source} -> {destination}")


def _submission_manifest(root: Path) -> dict[str, str]:
    return {
        nfc(path.relative_to(root).as_posix()): sha256_file(path)
        for path in root.rglob("*")
        if path.is_file() and path.name != ".DS_Store"
    }


def build_zip(submission: Path, output: Path) -> dict[str, Any]:
    files = sorted(
        (
            path
            for path in submission.rglob("*")
            if path.is_file() and path.name != ".DS_Store"
        ),
        key=lambda path: natural_key(path.relative_to(submission)),
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        prefix=f".{output.stem}.", suffix=".zip", dir=output.parent, delete=False
    ) as handle:
        temporary = Path(handle.name)
    try:
        with ZipFile(temporary, "w", ZIP_DEFLATED, compresslevel=6) as archive:
            for path in files:
                archive.write(path, nfc(path.relative_to(submission).as_posix()))
        with ZipFile(temporary) as archive:
            bad = archive.testzip()
            archive_manifest = {
                nfc(name): hashlib.sha256(archive.read(name)).hexdigest()
                for name in archive.namelist()
                if not name.endswith("/")
            }
        source_manifest = _submission_manifest(submission)
        if bad or archive_manifest != source_manifest:
            raise RuntimeError(
                f"ZIP 검사 실패: bad={bad}, source={len(source_manifest)}, zip={len(archive_manifest)}"
            )
        os.replace(temporary, output)
    finally:
        if temporary.exists():
            temporary.unlink()
    return {"path": str(output), "files": len(files), "sha256": sha256_file(output)}


def verify_book(workspace: Path, book: str) -> dict[str, Any]:
    paths = workspace_paths(workspace)
    final_root = paths["final"]
    submission = final_root / f"2. {book} 제출용"
    errors: list[str] = []
    hwpx_results = []
    if not submission.is_dir():
        errors.append(f"제출용 폴더 없음: {submission}")
    else:
        for path in sorted(submission.glob("*.hwpx"), key=natural_key):
            item = inspect_hwpx(path)
            hwpx_results.append(item)
            if not item["ok"]:
                errors.append(f"HWPX 검사 실패: {path.name}: {item['errors']}")
    whole_hwpx = submission / f"{book}_전체.hwpx"
    collection_hwpx = final_root / "0. 전체 파일 모음" / f"{book}_전체.hwpx"
    if whole_hwpx.is_file():
        if not collection_hwpx.is_file() or sha256_file(whole_hwpx) != sha256_file(collection_hwpx):
            errors.append("전체 파일 모음 HWPX 해시 불일치")
    else:
        errors.append(f"전체 HWPX 없음: {whole_hwpx}")
    whole_pdf = submission / "pdf" / f"{book}_전체.pdf"
    if whole_pdf.is_file():
        collection_pdf = final_root / "0. 전체 파일 모음" / "pdf" / whole_pdf.name
        if not collection_pdf.is_file() or sha256_file(whole_pdf) != sha256_file(collection_pdf):
            errors.append("전체 파일 모음 PDF 해시 불일치")

    archive_path = final_root / f"{book}.zip"
    if not archive_path.is_file():
        errors.append(f"ZIP 없음: {archive_path}")
        zip_check: dict[str, Any] = {"exists": False}
    else:
        with ZipFile(archive_path) as archive:
            bad = archive.testzip()
            archived = {
                nfc(name): hashlib.sha256(archive.read(name)).hexdigest()
                for name in archive.namelist()
                if not name.endswith("/")
            }
        source = _submission_manifest(submission)
        zip_check = {
            "exists": True,
            "crc_error": bad,
            "file_count": len(archived),
            "matches_submission": archived == source,
        }
        if bad or archived != source:
            errors.append("ZIP이 제출용 폴더와 일치하지 않음")
    return {
        "book": book,
        "checked_at": timestamp(),
        "submission": str(submission),
        "hwpx": hwpx_results,
        "zip": zip_check,
        "errors": errors,
        "passed": not errors,
    }


def run_book(
    workspace: Path,
    book: str,
    *,
    include_pdf: bool = False,
) -> dict[str, Any]:
    paths = workspace_paths(workspace)
    variant_book = paths["variant"] / book
    if not variant_book.is_dir():
        raise FileNotFoundError(f"변형 중간모음터 책 폴더 없음: {variant_book}")
    unit_directories = _unit_directories(variant_book)
    if not unit_directories:
        raise FileNotFoundError(f"단원 폴더 없음: {variant_book}")

    final_root = paths["final"]
    submission = final_root / f"2. {book} 제출용"
    work = final_root / f"1. {book} 작업용"
    reports = work / "_reports"
    submission.mkdir(parents=True, exist_ok=True)
    reports.mkdir(parents=True, exist_ok=True)
    unit_outputs: list[Path] = []
    unit_reports: list[dict[str, Any]] = []
    all_pdf_parts: list[Path] = []

    for unit_directory in unit_directories:
        unit = _unit_number(unit_directory)
        inputs = sorted(unit_directory.glob("*.hwpx"), key=natural_key)
        if not inputs:
            raise FileNotFoundError(f"HWPX 입력 없음: {unit_directory}")
        output = submission / f"{unit}단원.hwpx"
        report_path = reports / f"{unit}단원.json"
        report = merge_hwpx(
            inputs, output, title=f"{book} {unit}단원", report_path=report_path
        )
        unit_outputs.append(output)
        unit_reports.append(report)

        if include_pdf:
            part_directory = paths["pdf_parts"] / book / f"{unit}단원"
            parts = sorted(part_directory.glob("*.pdf"), key=natural_key)
            if not parts:
                raise FileNotFoundError(f"PDF 조각 없음: {part_directory}")
            merge_pdfs(parts, submission / "pdf" / f"{unit}단원.pdf")
            all_pdf_parts.extend(parts)

    whole = submission / f"{book}_전체.hwpx"
    whole_report = merge_hwpx(
        unit_outputs,
        whole,
        title=f"{book} 전체",
        report_path=reports / "책_통합.json",
    )
    _atomic_copy(whole, final_root / "0. 전체 파일 모음" / whole.name)
    if include_pdf:
        whole_pdf = submission / "pdf" / f"{book}_전체.pdf"
        merge_pdfs(all_pdf_parts, whole_pdf)
        _atomic_copy(
            whole_pdf, final_root / "0. 전체 파일 모음" / "pdf" / whole_pdf.name
        )
    archive = build_zip(submission, final_root / f"{book}.zip")
    verification = verify_book(workspace, book)
    result = {
        "book": book,
        "created_at": timestamp(),
        "units": len(unit_outputs),
        "unit_reports": unit_reports,
        "whole_report": whole_report,
        "archive": archive,
        "verification": verification,
        "passed": verification["passed"],
    }
    write_json_atomic(reports / "실행_요약.json", result)
    if not result["passed"]:
        raise RuntimeError(f"최종 검증 실패: {verification['errors']}")
    return result
