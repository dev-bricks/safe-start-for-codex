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
        "MARKETING-LOG.txt",
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
    assert "Last-checked: 2026-09-09" in llms_text
    assert "87 pytest tests passed" in llms_text


def test_cli_subcommands_registered() -> None:
    from safe_start_for_codex.cli import build_parser

    parser = build_parser()
    subparsers_actions = [
        action for action in parser._actions if isinstance(action, getattr(parser, "_SubParsersAction", type(None))) or hasattr(action, "choices") and action.choices
    ]
    assert subparsers_actions, "No subparsers found in CLI parser"
    choices = subparsers_actions[0].choices
    for expected_cmd in [
        "start",
        "tray",
        "dry-run",
        "status",
        "config-show",
        "config-init",
        "catchup-plan",
        "restore-latest",
        "backup",
    ]:
        assert expected_cmd in choices, f"Missing CLI subcommand: {expected_cmd}"


def test_readme_and_readme_de_parity() -> None:
    readme_en = (PROJECT_ROOT / "README.md").read_text(encoding="utf-8")
    readme_de = (PROJECT_ROOT / "README_de.md").read_text(encoding="utf-8")

    # Both documents must have matching core sections
    for sec_en in ["System Architecture", "Discovery Context", "Development", "Related Tools & Ecosystem", "License"]:
        assert sec_en in readme_en, f"Missing English section {sec_en}"

    for sec_de in ["Systemarchitektur", "Auffindbarkeit", "Entwicklung", "Verwandte Tools & Ökosystem", "Lizenz"]:
        assert sec_de in readme_de, f"Missing German section {sec_de}"

    # Cross links to sister repos
    for sister in ["CareCenter-for-Codex", "CodeBox", "companion-for-agy", "automation-master"]:
        assert sister in readme_en
        assert sister in readme_de


def test_quick_navigation_anchors_parity() -> None:
    readme_en = (PROJECT_ROOT / "README.md").read_text(encoding="utf-8")
    readme_de = (PROJECT_ROOT / "README_de.md").read_text(encoding="utf-8")

    assert "### 🧭 Quick Navigation" in readme_en
    assert "### 🧭 Schnellnavigation" in readme_de

    # Ensure 14 numbered links exist in both
    for i in range(1, 15):
        assert f"{i}. [" in readme_en, f"Missing point {i} in English quick navigation"
        assert f"{i}. [" in readme_de, f"Missing point {i} in German quick navigation"


def test_mermaid_diagrams_parity() -> None:
    readme_en = (PROJECT_ROOT / "README.md").read_text(encoding="utf-8")
    readme_de = (PROJECT_ROOT / "README_de.md").read_text(encoding="utf-8")

    # Flowchart / graph TB check
    assert "graph TB" in readme_en
    assert "graph TB" in readme_de

    # Sequence diagram check
    assert "sequenceDiagram" in readme_en
    assert "sequenceDiagram" in readme_de
    assert "autonumber" in readme_en
    assert "autonumber" in readme_de


def test_governance_invariants_table_parity() -> None:
    readme_en = (PROJECT_ROOT / "README.md").read_text(encoding="utf-8")
    readme_de = (PROJECT_ROOT / "README_de.md").read_text(encoding="utf-8")

    assert "Governance & Runtime Invariants" in readme_en
    assert "Governance- & Laufzeitinvarianten" in readme_de

    # Check that all 10 invariants are present in the table
    for inv_num in range(1, 11):
        assert f"| {inv_num} |" in readme_en, f"Missing invariant {inv_num} in English README"
        assert f"| {inv_num} |" in readme_de, f"Missing invariant {inv_num} in German README"


def test_ecosystem_matrix_parity() -> None:
    readme_en = (PROJECT_ROOT / "README.md").read_text(encoding="utf-8")
    readme_de = (PROJECT_ROOT / "README_de.md").read_text(encoding="utf-8")

    matrix_repos = [
        "CareCenter-for-Codex",
        "CodeBox",
        "companion-for-agy",
        "automation-master",
        "WikiStub-Seed",
        "MethodenAnalyser",
        "lock-master",
        "ticket-master",
        "ellmos-filecommander-mcp",
        "ellmos-codecommander-mcp",
        "ellmos-controlcenter-mcp",
        "open-bricks",
    ]
    for repo in matrix_repos:
        assert repo in readme_en, f"Missing {repo} in English ecosystem matrix"
        assert repo in readme_de, f"Missing {repo} in German ecosystem matrix"


def test_security_sla_and_contacts() -> None:
    sec_text = (PROJECT_ROOT / "SECURITY.md").read_text(encoding="utf-8")

    # SLAs
    assert "48 Stunden" in sec_text
    assert "48 hours" in sec_text
    assert "5 Werktagen" in sec_text
    assert "5 business days" in sec_text

    # Contacts
    assert "security@ellmos.ai" in sec_text
    assert "security@open-bricks.org" in sec_text
    assert "support@lukasgeiger.com" in sec_text
    assert "lukas@open-bricks.org" in sec_text


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
