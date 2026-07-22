from __future__ import annotations

import tomllib
from pathlib import Path

import safe_start_for_codex


def test_package_version_matches_pyproject_authority() -> None:
    project_root = Path(__file__).resolve().parents[1]
    metadata = tomllib.loads((project_root / "pyproject.toml").read_text(encoding="utf-8"))

    assert safe_start_for_codex.__version__ == metadata["project"]["version"]
