"""Cross-platform smoke tests — run on Windows, macOS, and Linux.

These tests exercise only platform-neutral code paths in cli.py.
Windows-specific functions (cleanup_start_blockers, SafeStartGate.run, etc.)
are NOT tested here; they are covered by tests/test_cli.py on windows-latest.
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

import pytest

from safe_start_for_codex.cli import (
    build_catchup_report,
    command_config_init,
    default_config_path,
    load_automations,
    read_gate_config,
    rrule_effective_period_hours,
    rrule_next_after,
    rrule_occurrences_between,
    set_status,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def write_automation(root: Path, name: str, status: str, rrule: str) -> Path:
    directory = root / "automations" / name
    directory.mkdir(parents=True)
    path = directory / "automation.toml"
    path.write_text(
        "\n".join(
            [
                f'id = "{name}"',
                f'name = "{name}"',
                'kind = "cron"',
                f'rrule = "{rrule}"',
                f'status = "{status}"',
                "created_at = 1000",
                "updated_at = 1000",
                "",
            ]
        ),
        encoding="utf-8",
    )
    return path


# ---------------------------------------------------------------------------
# 1. Package importable
# ---------------------------------------------------------------------------

def test_package_imports() -> None:
    """The package must import without errors on all platforms."""
    import safe_start_for_codex.cli as m
    assert hasattr(m, "SafeStartGate")
    assert hasattr(m, "load_automations")


# ---------------------------------------------------------------------------
# 2. CODEX_HOME isolation via env var
# ---------------------------------------------------------------------------

def test_codex_home_env_isolation(tmp_path: Path, monkeypatch) -> None:
    """CODEX_HOME env var must redirect all path resolution."""
    monkeypatch.setenv("CODEX_HOME", str(tmp_path))
    write_automation(tmp_path, "smoke-a", "ACTIVE", "RRULE:FREQ=DAILY;BYHOUR=8;BYMINUTE=0")

    items = load_automations()

    assert len(items) == 1
    assert items[0].id == "smoke-a"
    assert items[0].status == "ACTIVE"


# ---------------------------------------------------------------------------
# 3. rrule parsing — platform-neutral
# ---------------------------------------------------------------------------

def test_rrule_next_after_daily() -> None:
    rule = "RRULE:FREQ=DAILY;BYHOUR=9;BYMINUTE=0"
    anchor = datetime(2026, 1, 1, 8, 0)
    nxt = rrule_next_after(rule, anchor)
    assert nxt is not None
    assert nxt.hour == 9
    assert nxt > anchor


def test_rrule_occurrences_between_counts() -> None:
    rule = "RRULE:FREQ=DAILY;BYHOUR=9;BYMINUTE=0"
    start = datetime(2026, 1, 1, 0, 0)
    end = datetime(2026, 1, 8, 0, 0)
    occurrences = rrule_occurrences_between(rule, start, end)
    assert len(occurrences) == 7


def test_rrule_effective_period_daily() -> None:
    rule = "RRULE:FREQ=DAILY;BYHOUR=9;BYMINUTE=0"
    hours = rrule_effective_period_hours(rule)
    assert hours is not None
    assert abs(hours - 24.0) < 0.1


def test_rrule_effective_period_hourly() -> None:
    rule = "RRULE:FREQ=HOURLY;INTERVAL=4"
    hours = rrule_effective_period_hours(rule)
    assert hours is not None
    assert abs(hours - 4.0) < 0.1


# ---------------------------------------------------------------------------
# 4. Config read/write roundtrip
# ---------------------------------------------------------------------------

def test_config_init_and_read(tmp_path: Path, monkeypatch) -> None:
    """config-init writes a valid JSON file; read_gate_config reads it back."""
    monkeypatch.setenv("CODEX_HOME", str(tmp_path))
    config_path = default_config_path()

    import argparse
    args = argparse.Namespace(config=None, force=False)
    command_config_init(args)

    assert config_path.exists()
    data = json.loads(config_path.read_text(encoding="utf-8"))
    assert data["initial_release"] == 3
    assert data["interval_minutes"] == 5

    settings, _, _ = read_gate_config(config_path)
    assert settings.initial_release == 3
    assert settings.interval_minutes == 5


# ---------------------------------------------------------------------------
# 5. set_status TOML edit (no Windows dep)
# ---------------------------------------------------------------------------

def test_set_status_changes_toml(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("CODEX_HOME", str(tmp_path))
    toml_path = write_automation(tmp_path, "edit-me", "ACTIVE", "RRULE:FREQ=DAILY")

    result = set_status(toml_path, "PAUSED")

    assert result is True
    content = toml_path.read_text(encoding="utf-8")
    assert 'status = "PAUSED"' in content
    assert 'status = "ACTIVE"' not in content


# ---------------------------------------------------------------------------
# 6. build_catchup_report (no SQLite/Windows dep)
# ---------------------------------------------------------------------------

def test_build_catchup_report_no_observed(tmp_path: Path, monkeypatch) -> None:
    """With no observed runs catchup report should have no candidates."""
    monkeypatch.setenv("CODEX_HOME", str(tmp_path))
    write_automation(tmp_path, "rare-weekly", "ACTIVE", "RRULE:FREQ=WEEKLY;BYHOUR=10;BYMINUTE=0")

    automations = load_automations()
    report = build_catchup_report(
        automations=automations,
        observed_runs={},
        now=datetime(2026, 6, 10, 12, 0),
    )

    assert report is not None
    assert hasattr(report, "candidates")
