from __future__ import annotations

import re
import tomllib
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_dependency_versions_no_vulnerable_floors() -> None:
    data = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    opt_deps = data["project"].get("optional-dependencies", {})

    # Dev dependencies must enforce safe pytest >= 9.1.1 (guards against GHSA-6w46-j5rx-g56g / CVE-2025-7117)
    dev_deps = opt_deps.get("dev", [])
    assert any("pytest>=9.1" in dep for dep in dev_deps), f"Vulnerable pytest floor in {dev_deps}"

    # Tray dependencies must enforce safe Pillow >= 12.2.0 and pystray >= 0.19.5
    tray_deps = opt_deps.get("tray", [])
    assert any("pillow>=12.2" in dep for dep in tray_deps), f"Vulnerable pillow floor in {tray_deps}"
    assert any("pystray>=0.19" in dep for dep in tray_deps), f"Missing pystray in {tray_deps}"


def test_third_party_license_inventory_metadata() -> None:
    text = (ROOT / "THIRD_PARTY_LICENSES.txt").read_text(encoding="utf-8")
    assert "Last checked: 2026-08-23" in text
    assert "Safe Start for Codex is licensed under the MIT License" in text
    assert "Transitive Build & Test Inventory" in text
    for pkg in [
        "hatchling",
        "pillow",
        "pystray",
        "pytest",
        "pyinstaller",
        "altgraph",
        "pluggy",
        "iniconfig",
        "packaging",
        "colorama",
    ]:
        assert pkg in text.lower(), f"Missing license entry for {pkg}"


def test_security_policy_bilingual_and_contacts() -> None:
    text = (ROOT / "SECURITY.md").read_text(encoding="utf-8")
    assert "## Deutsch" in text
    assert "## English" in text
    assert "security@ellmos.ai" in text
    assert "support@lukasgeiger.com" in text
    assert "Local-First & Zero-Egress" in text
    assert "Non-Elevation" in text or "Unprivilegierter User-Mode" in text
    assert "Non-Destructive File Safety" in text or "Nicht-destruktive Dateioperationen" in text


def test_repo_hygiene_and_gitignore_rules() -> None:
    gitignore = (ROOT / ".gitignore").read_text(encoding="utf-8")
    assert ".env" in gitignore
    assert "credentials.json" in gitignore
    assert "token.json" in gitignore
    assert "*.sqlite" in gitignore
    assert "LOCK*.txt" in gitignore
    assert "*-WORKSTATION-LG*" in gitignore
    assert "*.conflict" in gitignore


def test_no_hardcoded_user_paths_or_plaintext_secrets() -> None:
    secret_regex = re.compile(r"(?i)(api[_-]?key|secret|password|token|bearer)\s*[:=]\s*['\"][^'\"]{12,}")
    path_regex = re.compile(r"[a-zA-Z]:\\Users\\(lukas|User)", re.IGNORECASE)

    for sub in ("src", "tests", "docs"):
        sub_dir = ROOT / sub
        if not sub_dir.is_dir():
            continue
        for py_path in sub_dir.rglob("*.py"):
            content = py_path.read_text(encoding="utf-8", errors="ignore")
            assert not path_regex.search(content), f"Hardcoded user path in {py_path}"
            if "test" not in py_path.name:
                assert not secret_regex.search(content), f"Secret suspect in {py_path}"


def test_pyproject_pep621_classifiers_and_urls() -> None:
    data = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    project = data.get("project", {})

    classifiers = project.get("classifiers", [])
    assert "License :: OSI Approved :: MIT License" in classifiers
    assert "Operating System :: Microsoft :: Windows" in classifiers
    assert "Programming Language :: Python :: 3.11" in classifiers
    assert "Programming Language :: Python :: 3.12" in classifiers

    urls = project.get("urls", {})
    assert "Homepage" in urls
    assert "Documentation" in urls
    assert "Repository" in urls
    assert "Issues" in urls
    assert "Changelog" in urls
    assert "Security" in urls
