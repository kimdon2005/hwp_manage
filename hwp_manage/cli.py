from __future__ import annotations

import argparse
import json
import platform
import sys
from pathlib import Path

from lxml import etree

from . import __version__
from .hwpx import inspect_hwpx, merge_hwpx
from .inventory import inventory_book
from .pipeline import discover_books, run_book, verify_book, workspace_paths


def _print(value: object) -> None:
    print(json.dumps(value, ensure_ascii=False, indent=2))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="hwp-manage",
        description="HWPX 단원/전체 병합, 이미지 무결성 검사, 제출용 ZIP 생성",
    )
    parser.add_argument("--version", action="version", version=__version__)
    sub = parser.add_subparsers(dest="command", required=True)

    doctor = sub.add_parser("doctor", help="실행 환경과 폴더 구조 확인")
    doctor.add_argument("--workspace", type=Path, default=Path.cwd())

    inspect = sub.add_parser("inspect", help="HWPX 구조·이미지 참조 검사")
    inspect.add_argument("files", nargs="+", type=Path)

    merge = sub.add_parser("merge", help="지정한 HWPX를 순서대로 병합")
    merge.add_argument("--input", nargs="+", type=Path, required=True)
    merge.add_argument("--output", type=Path, required=True)
    merge.add_argument("--title", required=True)
    merge.add_argument("--report", type=Path)

    inventory = sub.add_parser("inventory", help="중간모음터 파일·정답·변환 대기 목록 작성")
    inventory.add_argument("--workspace", type=Path, default=Path.cwd())
    inventory.add_argument("--book", required=True)
    inventory.add_argument("--report", type=Path)

    pipeline = sub.add_parser("pipeline", help="책 단원·전체 병합과 제출용 ZIP 생성")
    pipeline.add_argument("--workspace", type=Path, default=Path.cwd())
    pipeline.add_argument("--book", action="append")
    pipeline.add_argument("--pdf", action="store_true", help="PDF 조각도 함께 병합")

    verify = sub.add_parser("verify", help="제출용/전체모음/ZIP 최종 대조")
    verify.add_argument("--workspace", type=Path, default=Path.cwd())
    verify.add_argument("--book", action="append")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command == "doctor":
        paths = workspace_paths(args.workspace)
        books = discover_books(args.workspace)
        result = {
            "python": sys.version.split()[0],
            "platform": platform.platform(),
            "lxml": etree.LXML_VERSION,
            "workspace": str(paths["workspace"]),
            "variant_exists": paths["variant"].is_dir(),
            "final_exists": paths["final"].is_dir(),
            "books": books,
            "ready": paths["variant"].is_dir() and bool(books),
        }
        _print(result)
        return 0 if result["ready"] else 2
    if args.command == "inspect":
        results = [inspect_hwpx(path) for path in args.files]
        _print(results)
        return 0 if all(item["ok"] for item in results) else 2
    if args.command == "merge":
        _print(
            merge_hwpx(
                args.input,
                args.output,
                title=args.title,
                report_path=args.report,
            )
        )
        return 0
    if args.command == "inventory":
        _print(inventory_book(args.workspace, args.book, args.report))
        return 0
    if args.command in {"pipeline", "verify"}:
        books = args.book or discover_books(args.workspace)
        if not books:
            raise SystemExit("처리할 책이 없습니다. --book 또는 변형 중간모음터를 확인하세요.")
        results = []
        for book in books:
            if args.command == "pipeline":
                results.append(run_book(args.workspace, book, include_pdf=args.pdf))
            else:
                results.append(verify_book(args.workspace, book))
        _print(results)
        return 0 if all(item.get("passed") for item in results) else 2
    return 2
