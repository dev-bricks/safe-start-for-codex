from __future__ import annotations

import tomllib
from pathlib import Path

import safe_start_for_codex


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_package_version_matches_pyproject_authority() -> None:
    metadata = tomllib.loads((PROJECT_ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    assert safe_start_for_codex.__version__ == metadata["project"]["version"]


def test_required_documentation_files_exist() -> None:
    required_files = [
        "README.md",
        "README_de.md",
        "LICENSE",
        "llms.txt",
        "CHANGELOG.md",
        "SECURITY.md",
        "THIRD_PARTY_LICENSES.txt",
    ]
    for rel_path in required_files:
        file_path = PROJECT_ROOT / rel_path
        assert file_path.is_file(), f"Required file missing: {rel_path}"
        assert file_path.stat().st_size > 0, f"File is empty: {rel_path}"


def test_ecosystem_and_umbrella_markers() -> None:
    readme_en = (PROJECT_ROOT / "README.md").read_text(encoding="utf-8")
    readme_de = (PROJECT_ROOT / "README_de.md").read_text(encoding="utf-8")

    assert "open-bricks" in readme_en
    assert "dev-bricks" in readme_en
    assert "open-bricks" in readme_de
    assert "dev-bricks" in readme_de
    assert "llms.txt" in readme_en
    assert "llms.txt" in readme_de


def test_llms_txt_integrity() -> None:
    llms_text = (PROJECT_ROOT / "llms.txt").read_text(encoding="utf-8")
    assert "https://github.com/dev-bricks/safe-start-for-codex" in llms_text
    assert "dev-bricks" in llms_text
    assert "Last-checked: 2026-08-21" in llms_text
    assert "70 pytest tests passed" in llms_text


def test_text_files_utf8_clean() -> None:
    for ext in ("*.py", "*.md", "*.txt", "*.toml", "*.json"):
        for path in PROJECT_ROOT.glob(ext):
            try:
                path.read_text(encoding="utf-8")
            except UnicodeDecodeError as exc:
                assert False, f"File {path.name} is not valid UTF-8: {exc}"
    for sub in ("src", "tests", "docs"):
        sub_dir = PROJECT_ROOT / sub
        if sub_dir.is_dir():
            for path in sub_dir.rglob("*.py"):
                try:
                    path.read_text(encoding="utf-8")
                except UnicodeDecodeError as exc:
                    assert False, f"File {path} is not valid UTF-8: {exc}"
            for path in sub_dir.rglob("*.md"):
                try:
                    path.read_text(encoding="utf-8")
                except UnicodeDecodeError as exc:
                    assert False, f"File {path} is not valid UTF-8: {exc}"

