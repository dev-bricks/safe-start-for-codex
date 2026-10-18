"""Hermetic regression tests for Safe Start Bugsweep iteration 2026-10-18.

Focus area:
CLI commands, snapshot lifecycle, status restoration, TOML parsing & backup resilience.
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch


from safe_start_for_codex.cli import (
    command_backup,
    command_restore_latest,
    command_status,
    int_value,
    quoted_value,
    rrule_next_after,
    set_status,
)
from safe_start_for_codex.dashboard import get_dashboard_data


def test_quoted_value_and_int_value_support_indented_toml() -> None:
    toml_text = """
    # Formatted TOML with leading whitespace
    id = "indent-1"
      name = "Indented Automation"
      status = "ACTIVE"
      updated_at = 987654321
      rrule = "FREQ=DAILY;INTERVAL=1"
    """
    assert quoted_value(toml_text, "id") == "indent-1"
    assert quoted_value(toml_text, "name") == "Indented Automation"
    assert quoted_value(toml_text, "status") == "ACTIVE"
    assert quoted_value(toml_text, "rrule") == "FREQ=DAILY;INTERVAL=1"
    assert int_value(toml_text, "updated_at") == 987654321


def test_set_status_in_place_without_duplicate_keys_on_indented_toml(tmp_path: Path) -> None:
    toml_file = tmp_path / "automation.toml"
    toml_file.write_text(
        '  id = "indent-test"\n  status = "ACTIVE"\n  updated_at = 111111\n',
        encoding="utf-8",
    )

    # First update: ACTIVE -> PAUSED
    changed = set_status(toml_file, "PAUSED")
    assert changed is True
    content = toml_file.read_text(encoding="utf-8")
    assert quoted_value(content, "status") == "PAUSED"
    # Must not contain duplicate status declarations
    assert content.count("status") == 1
    assert content.count("updated_at") == 1

    # Second update: PAUSED -> PAUSED (idempotent, no change)
    assert set_status(toml_file, "PAUSED") is False


def test_command_restore_latest_updates_snapshot_and_audit_log(tmp_path: Path) -> None:
    codex_home = tmp_path / ".codex"
    state_dir = codex_home / "automation-safe-start"
    state_dir.mkdir(parents=True)
    auto_dir = codex_home / "automations" / "auto-1"
    auto_dir.mkdir(parents=True)
    auto_toml = auto_dir / "automation.toml"
    auto_toml.write_text('id = "auto-1"\nstatus = "PAUSED"\n', encoding="utf-8")

    latest_file = state_dir / "latest.json"
    snapshot = {
        "run_id": "test-run-101",
        "phase": "paused",
        "created_at": "2026-10-18T07:00:00",
        "tool_paused_ids": ["auto-1"],
        "released_ids": [],
        "items": [
            {
                "id": "auto-1",
                "name": "Auto One",
                "path": str(auto_toml),
                "original_status": "ACTIVE",
                "status": "PAUSED",
                "tool_paused": True,
                "released": False,
            }
        ],
    }
    latest_file.write_text(json.dumps(snapshot, indent=2), encoding="utf-8")

    with patch("safe_start_for_codex.cli.codex_home", return_value=codex_home):
        args = argparse.Namespace(dry_run=False)
        rc = command_restore_latest(args)
        assert rc == 0

        # File on disk restored to ACTIVE
        assert quoted_value(auto_toml.read_text(encoding="utf-8"), "status") == "ACTIVE"

        # latest.json updated to restored phase
        updated_latest = json.loads(latest_file.read_text(encoding="utf-8"))
        assert updated_latest["phase"] == "restored"
        assert "auto-1" in updated_latest["released_ids"]
        item = updated_latest["items"][0]
        assert item["status"] == "ACTIVE"
        assert item["tool_paused"] is False
        assert item["released"] is True

        # Audit log written to events.jsonl
        events_file = state_dir / "events.jsonl"
        assert events_file.exists()
        events = [json.loads(line) for line in events_file.read_text(encoding="utf-8").splitlines() if line.strip()]
        assert any(e.get("event") == "restore_latest" for e in events)

        # Second run is cleanly idempotent (0 restored)
        rc2 = command_restore_latest(args)
        assert rc2 == 0


def test_command_status_and_restore_resilient_to_corrupt_data(tmp_path: Path) -> None:
    codex_home = tmp_path / ".codex"
    state_dir = codex_home / "automation-safe-start"
    state_dir.mkdir(parents=True)
    latest_file = state_dir / "latest.json"
    # Malformed snapshot fields
    latest_file.write_text(
        json.dumps(
            {
                "run_id": "corrupt-1",
                "phase": "paused",
                "tool_paused_ids": 12345,  # not a list
                "released_ids": None,       # null
                "items": [None, "invalid", 42],  # non-dict items
            }
        ),
        encoding="utf-8",
    )

    with patch("safe_start_for_codex.cli.codex_home", return_value=codex_home):
        # command_status should not raise TypeError
        rc_status = command_status(argparse.Namespace())
        assert rc_status in (0, 1)

        # command_restore_latest should not crash
        rc_restore = command_restore_latest(argparse.Namespace(dry_run=True))
        assert rc_restore in (0, 1)


def test_command_backup_creates_backup_and_handles_collisions(tmp_path: Path) -> None:
    codex_home = tmp_path / ".codex"
    auto_dir = codex_home / "automations" / "my-job"
    auto_dir.mkdir(parents=True)
    (auto_dir / "automation.toml").write_text('id = "my-job"\nstatus = "ACTIVE"\n', encoding="utf-8")

    with patch("safe_start_for_codex.cli.codex_home", return_value=codex_home):
        args = argparse.Namespace()
        # First backup
        rc1 = command_backup(args)
        assert rc1 == 0

        # Rapid consecutive backup within same second must not raise FileExistsError
        rc2 = command_backup(args)
        assert rc2 == 0


def test_rrule_yearly_negative_bymonthday_resolution() -> None:
    # YEARLY rule targeting the last day of December (BYMONTH=12, BYMONTHDAY=-1)
    rule = "FREQ=YEARLY;BYMONTH=12;BYMONTHDAY=-1;BYHOUR=14;BYMINUTE=30"
    dtstart = datetime(2026, 1, 1, 0, 0, tzinfo=timezone.utc)
    after = datetime(2026, 12, 1, 0, 0, tzinfo=timezone.utc)

    next_run = rrule_next_after(rule, after, dtstart=dtstart)
    assert next_run is not None
    assert next_run == datetime(2026, 12, 31, 14, 30, tzinfo=timezone.utc)


def test_dashboard_data_still_gated_calculation_resilience() -> None:
    state_dir = Path("dummy_dir")
    snapshot = {
        "run_id": "test",
        "phase": "paused",
        "tool_paused_ids": ["job-a", "job-b"],
        "released_ids": ["job-a", "job-a", "unrelated-c"],  # contains duplicate and foreign id
        "items": [],
    }

    with patch("pathlib.Path.exists", return_value=True), \
         patch("pathlib.Path.read_text", return_value=json.dumps(snapshot)), \
         patch("safe_start_for_codex.cli.load_automations", return_value=[]):
        data = get_dashboard_data(state_dir)
        # still_gated must be exactly 1 ("job-b" is not released)
        assert data["counts"]["still_gated"] == 1
