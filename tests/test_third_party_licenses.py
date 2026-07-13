from __future__ import annotations

import re
import tomllib
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _requirement_name(requirement: str) -> str:
    requirement = requirement.split(";", 1)[0].strip()
    name = re.split(r"[\s<>=!~\[]", requirement, maxsplit=1)[0]
    return name.lower().replace("_", "-")


def _declared_direct_dependencies() -> set[str]:
    data = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    names: set[str] = set()
    for requirement in data["build-system"]["requires"]:
        names.add(_requirement_name(requirement))
    for requirement in data["project"].get("dependencies", []):
        names.add(_requirement_name(requirement))
    for requirements in data["project"].get("optional-dependencies", {}).values():
        for requirement in requirements:
            names.add(_requirement_name(requirement))
    return names


def test_third_party_license_inventory_covers_direct_dependencies() -> None:
    text = (ROOT / "THIRD_PARTY_LICENSES.txt").read_text(encoding="utf-8").lower()

    assert _declared_direct_dependencies() == {
        "hatchling",
        "pillow",
        "pyinstaller",
        "pystray",
        "pytest",
    }
    for package_name in _declared_direct_dependencies():
        assert package_name in text


def test_third_party_license_inventory_documents_scope() -> None:
    text = (ROOT / "THIRD_PARTY_LICENSES.txt").read_text(encoding="utf-8")

    assert "no external runtime dependencies" in text
    assert "not a frozen transitive SBOM" in text
    assert "https://pypi.org/project/" in text
