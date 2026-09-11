from pathlib import Path
import re


ROOT = Path(__file__).resolve().parents[1]


def test_beginner_manual_and_codex_prompt_are_linked() -> None:
    index = (ROOT / "docs" / "00_총정리_목차.md").read_text(encoding="utf-8")
    manual = (ROOT / "docs" / "01_사용자_매뉴얼.md").read_text(encoding="utf-8")
    prompt = (ROOT / "docs" / "08_Codex_기본세팅_프롬프트.md").read_text(
        encoding="utf-8"
    )

    assert "08_Codex_기본세팅_프롬프트.md" in index
    assert "08_Codex_기본세팅_프롬프트.md" in manual
    assert "sh scripts/setup.sh" in prompt
    assert "scripts\\setup.ps1" in prompt
    assert "sh scripts/run_sample.sh" in prompt
    assert "scripts\\run_sample.ps1" in prompt
    assert "사용자작업/목표2/국어 자료 변형 중간모음터" in prompt
    assert "모든 검사가 통과했을 때만" in prompt


def test_user_workspace_is_ignored_by_git() -> None:
    gitignore = (ROOT / ".gitignore").read_text(encoding="utf-8").splitlines()
    assert "사용자작업/" in gitignore


def test_local_markdown_links_exist() -> None:
    markdown_files = [ROOT / "README.md", *(ROOT / "docs").glob("*.md")]
    for source in markdown_files:
        text = source.read_text(encoding="utf-8")
        for target in re.findall(r"\[[^]]+\]\(([^)]+)\)", text):
            target = target.split("#", 1)[0]
            if not target or "://" in target:
                continue
            assert (source.parent / target).exists(), f"broken link: {source} -> {target}"
