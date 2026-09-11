from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from .common import natural_key, nfc, timestamp, write_json_atomic


ANSWER_MARKERS = (
    "정답",
    "정답과해설",
    "예시답안",
    "예시답안및평가기준",
)


def compact_name(value: str) -> str:
    return re.sub(r"[\s_\-]+", "", nfc(value)).casefold()


def is_answer_name(value: str) -> bool:
    compact = compact_name(value)
    return any(marker in compact for marker in ANSWER_MARKERS)


def inventory_book(
    workspace: Path, book: str, report_path: Path | None = None
) -> dict[str, Any]:
    source = (
        workspace.expanduser().resolve()
        / "목표2"
        / "국어 자료 중간모음터"
        / book
    )
    if not source.is_dir():
        raise FileNotFoundError(f"중간모음터 책 폴더 없음: {source}")
    records = []
    for path in sorted((item for item in source.rglob("*") if item.is_file()), key=natural_key):
        suffix = path.suffix.lower()
        kind = (
            "document"
            if suffix in {".hwp", ".hwpx"}
            else "pdf"
            if suffix == ".pdf"
            else "presentation"
            if suffix in {".ppt", ".pptx"}
            else "other"
        )
        records.append(
            {
                "relative_path": nfc(path.relative_to(source).as_posix()),
                "suffix": suffix,
                "kind": kind,
                "answer": kind == "document" and is_answer_name(path.stem),
                "size": path.stat().st_size,
            }
        )
    result = {
        "created_at": timestamp(),
        "book": book,
        "source": str(source),
        "total": len(records),
        "documents": sum(item["kind"] == "document" for item in records),
        "answers": sum(item["answer"] for item in records),
        "pending_hwp_conversion": sum(item["suffix"] == ".hwp" for item in records),
        "records": records,
    }
    if report_path:
        write_json_atomic(report_path, result)
    return result
