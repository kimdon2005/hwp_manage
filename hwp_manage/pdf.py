from __future__ import annotations

import os
import uuid
from pathlib import Path

from .common import natural_key


def merge_pdfs(inputs: list[Path], output: Path) -> int:
    try:
        import fitz
    except ImportError as exc:
        raise RuntimeError("PDF 기능은 'pip install -e .[pdf]'가 필요합니다.") from exc
    inputs = sorted((path.resolve() for path in inputs), key=natural_key)
    if not inputs:
        raise ValueError("병합할 PDF가 없습니다.")
    result = fitz.open()
    try:
        for path in inputs:
            with fitz.open(path) as source:
                if source.page_count < 1:
                    raise ValueError(f"빈 PDF: {path}")
                result.insert_pdf(source)
        for number, page in enumerate(result, 1):
            mask = fitz.Rect(
                page.rect.width / 2 - 35,
                page.rect.height - 47,
                page.rect.width / 2 + 35,
                page.rect.height - 10,
            )
            page.draw_rect(mask, color=None, fill=(1, 1, 1), overlay=True)
            label = str(number)
            width = fitz.get_text_length(label, fontname="helv", fontsize=8)
            page.insert_text(
                fitz.Point(page.rect.width / 2 - width / 2, page.rect.height - 12),
                label,
                fontsize=8,
                fontname="helv",
                color=(0, 0, 0),
                overlay=True,
            )
        output.parent.mkdir(parents=True, exist_ok=True)
        temporary = output.with_name(f".{output.name}.{uuid.uuid4().hex}.tmp.pdf")
        result.save(temporary, garbage=4, deflate=True)
        os.replace(temporary, output)
        return result.page_count
    finally:
        result.close()
