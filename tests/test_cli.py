from __future__ import annotations

import argparse
import json
import runpy
import sys
import time
import types
from datetime import datetime, timedelta
from pathlib import Path

import pytest

from safe_start_for_codex.cli import (
    Automation,
    GateSettings,
    ObservedRun,
    SafeStartGate,
    build_catchup_report,
    command_tray,
    command_config_init,
    default_config_path,
    load_automations,
    read_gate_config,
    resolve_gate_settings,
    rrule_effective_period_hours,
    rrule_next_after,
    rrule_occurrences_between,
    set_status,
    split_release_queue,
)
from safe_start_for_codex import tray_app


def write_automation(root: Path, name: str, status: str, rrule: str) -> Path:
    directory = root / ".codex" / "automations" / name
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


def test_load_automations_uses_codex_home(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("CODEX_HOME", str(tmp_path / ".codex"))
    write_automation(tmp_path, "daily-check", "ACTIVE", "RRULE:FREQ=DAILY;BYHOUR=9;BYMINUTE=0")

    items = load_automations()

    assert len(items) == 1
    assert items[0].id == "daily-check"
    assert items[0].status == "ACTIVE"


def test_set_status_rewrites_status_and_updated_at(tmp_path: Path) -> None:
    path = write_automation(tmp_path, "job", "ACTIVE", "RRULE:FREQ=DAILY;BYHOUR=9;BYMINUTE=0")

    changed = set_status(path, "PAUSED")
    text = path.read_text(encoding="utf-8")

    assert changed is True
    assert 'status = "PAUSED"' in text
    assert "updated_at = 1000" not in text


def test_rrule_next_after_daily() -> None:
    after = datetime(2026, 6, 4, 8, 58)
    next_at = rrule_next_after("RRULE:FREQ=DAILY;BYHOUR=9;BYMINUTE=0", after)

    assert next_at == datetime(2026, 6, 4, 9, 0)


def test_rrule_next_after_weekly_byday() -> None:
    after = datetime(2026, 6, 4, 12, 0)  # Thursday
    next_at = rrule_next_after("RRULE:FREQ=WEEKLY;BYDAY=FR;BYHOUR=9;BYMINUTE=30", after)

    assert next_at == datetime(2026, 6, 5, 9, 30)


def test_split_release_queue_keeps_immediate_jobs_for_fallback() -> None:
    reference = datetime(2026, 6, 4, 8, 58)
    future = Automation("future", "future", "future.toml", "ACTIVE", "ACTIVE", "cron", "RRULE:FREQ=DAILY;BYHOUR=9;BYMINUTE=5", 1, 1)
    immediate = Automation("now", "now", "now.toml", "ACTIVE", "ACTIVE", "cron", "RRULE:FREQ=DAILY;BYHOUR=9;BYMINUTE=0", 1, 1)

    safe, fallback = split_release_queue([future, immediate], reference, timedelta(minutes=3))

    assert [item.id for item in safe] == ["future"]
    assert [item.id for item in fallback] == ["now"]


def test_read_gate_config_uses_json_values(tmp_path: Path) -> None:
    config = tmp_path / "config.json"
    config.write_text(
        json.dumps(
            {
                "initial_release": 5,
                "interval_minutes": 12,
                "startup_delay_seconds": 30,
                "min_future_lead_minutes": 8,
                "launch": False,
                "cleanup": False,
                "catchup_enabled": True,
                "catchup_lookback_days": 14,
                "catchup_max_per_start": 2,
                "catchup_min_period_hours": 24,
            }
        ),
        encoding="utf-8",
    )

    settings, path, exists = read_gate_config(config)

    assert exists is True
    assert path == config
    assert settings == GateSettings(
        initial_release=5,
        interval_minutes=12,
        startup_delay_seconds=30,
        min_future_lead_minutes=8,
        launch=False,
        cleanup=False,
        catchup_enabled=True,
        catchup_lookback_days=14,
        catchup_max_per_start=2,
        catchup_min_period_hours=24,
    )


def test_resolve_gate_settings_cli_overrides_config(tmp_path: Path) -> None:
    config = tmp_path / "config.json"
    config.write_text(json.dumps({"initial_release": 5, "interval_minutes": 12}), encoding="utf-8")
    args = argparse.Namespace(
        config=config,
        initial_release=2,
        interval_minutes=None,
        startup_delay_seconds=None,
        min_future_lead_minutes=None,
        launch=True,
        cleanup=None,
        catchup_enabled=None,
        catchup_lookback_days=None,
        catchup_max_per_start=None,
        catchup_min_period_hours=None,
    )

    settings, _, _ = resolve_gate_settings(args)

    assert settings.initial_release == 2
    assert settings.interval_minutes == 12
    assert settings.launch is True


def test_read_gate_config_rejects_unknown_keys(tmp_path: Path) -> None:
    config = tmp_path / "config.json"
    config.write_text(json.dumps({"initial_releases": 5}), encoding="utf-8")

    with pytest.raises(SystemExit):
        read_gate_config(config)


def test_config_init_writes_default_config(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("CODEX_HOME", str(tmp_path / ".codex"))
    args = argparse.Namespace(config=None, force=False)

    assert command_config_init(args) == 0

    config = default_config_path()
    assert config.exists()
    settings, _, exists = read_gate_config(config)
    assert exists is True
    assert settings == GateSettings()


def test_rrule_next_after_hourly_large_interval() -> None:
    after = datetime(2026, 6, 4, 10, 0)
    next_at = rrule_next_after("RRULE:FREQ=HOURLY;INTERVAL=25;BYMINUTE=0", after)
    # 25 hours after 10:00 = 11:00 the next day
    assert next_at == datetime(2026, 6, 5, 11, 0)


def test_rrule_occurrences_between_hourly_large_interval() -> None:
    start = datetime(2026, 6, 1, 0, 0)
    end = datetime(2026, 6, 3, 12, 0)
    occurrences = rrule_occurrences_between("RRULE:FREQ=HOURLY;INTERVAL=25;BYMINUTE=0", start, end)
    # start + 25h = 2026-06-02 01:00, +25h = 2026-06-03 02:00; third would be 2026-06-04 03:00 (out of range)
    assert len(occurrences) == 2
    assert occurrences[0] == datetime(2026, 6, 2, 1, 0)
    assert occurrences[1] == datetime(2026, 6, 3, 2, 0)


def test_rrule_next_after_hourly_interval_23() -> None:
    # 23 is not a divisor of 24 — modulo path would alias to hour 0 only
    after = datetime(2026, 6, 4, 10, 0)
    next_at = rrule_next_after("RRULE:FREQ=HOURLY;INTERVAL=23;BYMINUTE=0", after)
    # 23 hours after 10:00 = 09:00 the next day
    assert next_at == datetime(2026, 6, 5, 9, 0)


def test_rrule_occurrences_between_hourly_interval_23() -> None:
    # 23 is not a divisor of 24 — modulo path would produce wrong anchor
    start = datetime(2026, 6, 1, 0, 0)
    end = datetime(2026, 6, 3, 12, 0)
    occurrences = rrule_occurrences_between("RRULE:FREQ=HOURLY;INTERVAL=23;BYMINUTE=0", start, end)
    # start + 23h = 2026-06-01 23:00, +23h = 2026-06-02 22:00, +23h = 2026-06-03 21:00 (out of range)
    assert len(occurrences) == 2
    assert occurrences[0] == datetime(2026, 6, 1, 23, 0)
    assert occurrences[1] == datetime(2026, 6, 2, 22, 0)


def test_status_text_reports_no_gated_automations_clearly() -> None:
    gate = SafeStartGate()
    gate.last_message = "Found 3 automations; paused 0 active automations."

    assert gate.status_text() == (
        "No automations are currently gated. "
        "Last status: Found 3 automations; paused 0 active automations."
    )


def test_status_text_reports_finished_release_clearly() -> None:
    gate = SafeStartGate()
    gate.last_message = "Release staggering finished. Tray remains available for restore/quit."
    gate.tool_paused = [
        Automation("a", "a", "a.toml", "ACTIVE", "ACTIVE", "cron", "RRULE:FREQ=DAILY", 1, 1, released=True),
        Automation("b", "b", "b.toml", "ACTIVE", "ACTIVE", "cron", "RRULE:FREQ=DAILY", 1, 1, released=True),
    ]

    assert gate.status_text() == (
        "All 2 gated automations have been released. "
        "Last status: Release staggering finished. Tray remains available for restore/quit."
    )


def test_rrule_effective_period_detects_rare_schedules() -> None:
    assert rrule_effective_period_hours("RRULE:FREQ=WEEKLY;BYDAY=FR;BYHOUR=9;BYMINUTE=0") == 168
    assert rrule_effective_period_hours("RRULE:FREQ=DAILY;BYHOUR=9;BYMINUTE=0") == 24
    assert rrule_effective_period_hours("RRULE:FREQ=HOURLY;INTERVAL=25;BYMINUTE=0") == 25


def test_build_catchup_report_flags_missing_rare_automation() -> None:
    now = datetime(2026, 6, 4, 12, 0)
    item = Automation(
        "weekly-review",
        "Weekly Review",
        "weekly.toml",
        "ACTIVE",
        "ACTIVE",
        "cron",
        "RRULE:FREQ=WEEKLY;BYDAY=TH;BYHOUR=9;BYMINUTE=0",
        None,
        None,
    )

    report = build_catchup_report(
        [item],
        now=now,
        lookback_days=10,
        min_period_hours=24,
        max_per_start=1,
        observed_runs={"weekly-review": []},
    )

    assert report.eligible_ids == ["weekly-review"]
    assert report.candidates[0].missed is True
    assert report.candidates[0].eligible is True


def test_build_catchup_report_observed_run_satisfies_latest_due() -> None:
    now = datetime(2026, 6, 4, 12, 0)
    item = Automation(
        "weekly-review",
        "Weekly Review",
        "weekly.toml",
        "ACTIVE",
        "ACTIVE",
        "cron",
        "RRULE:FREQ=WEEKLY;BYDAY=TH;BYHOUR=9;BYMINUTE=0",
        None,
        None,
    )
    observed = ObservedRun(
        automation_id="weekly-review",
        thread_id="thread-1",
        created_at=datetime(2026, 6, 4, 9, 30).isoformat(timespec="seconds"),
        title="Weekly Review",
    )

    report = build_catchup_report(
        [item],
        now=now,
        lookback_days=10,
        min_period_hours=24,
        max_per_start=1,
        observed_runs={"weekly-review": [observed]},
    )

    assert report.eligible_ids == []
    assert report.candidates[0].missed is False


def test_tray_app_runs_tray_command(monkeypatch) -> None:
    calls: list[list[str]] = []

    def fake_main(argv: list[str]) -> int:
        calls.append(argv)
        return 0

    monkeypatch.setattr(tray_app, "main", fake_main)

    assert tray_app.run() == 0
    assert calls == [["tray"]]


def test_tray_app_logs_system_exit_from_windowed_entrypoint(tmp_path: Path, monkeypatch) -> None:
    log_dir = tmp_path / "logs"
    monkeypatch.setenv("SAFE_START_LOG_DIR", str(log_dir))

    def fake_main(_argv: list[str]) -> int:
        raise SystemExit("bad config")

    monkeypatch.setattr(tray_app, "main", fake_main)

    assert tray_app.run() == 1
    logs = list(log_dir.glob("startup-error-*.txt"))
    assert len(logs) == 1
    assert "SystemExit: bad config" in logs[0].read_text(encoding="utf-8")


def test_tray_app_direct_file_import_has_package_fallback() -> None:
    path = Path(__file__).resolve().parents[1] / "src" / "safe_start_for_codex" / "tray_app.py"

    namespace = runpy.run_path(str(path))

    assert callable(namespace["run"])


def test_tray_app_direct_file_execution_reaches_cli(monkeypatch, tmp_path: Path) -> None:
    class FakeIcon:
        def __init__(self, *args, **kwargs) -> None:
            self.title = ""

        def run(self, setup=None) -> None:
            return None

        def notify(self, *args, **kwargs) -> None:
            return None

        def stop(self) -> None:
            return None

    class FakeMenu:
        def __init__(self, *items) -> None:
            self.items = items

    class FakeMenuItem:
        def __init__(self, *args, **kwargs) -> None:
            self.args = args
            self.kwargs = kwargs

    fake_pystray = types.ModuleType("pystray")
    fake_pystray.Icon = FakeIcon
    fake_pystray.Menu = FakeMenu
    fake_pystray.MenuItem = FakeMenuItem
    monkeypatch.setitem(sys.modules, "pystray", fake_pystray)
    monkeypatch.setenv("CODEX_HOME", str(tmp_path / ".codex"))
    path = Path(__file__).resolve().parents[1] / "src" / "safe_start_for_codex" / "tray_app.py"

    with pytest.raises(SystemExit) as exc:
        runpy.run_path(str(path), run_name="__main__")

    assert exc.value.code in {0, 1}


def test_tray_worker_logs_system_exit_when_automations_dir_missing(
    tmp_path: Path,
    monkeypatch,
) -> None:
    class FakeIcon:
        def __init__(self, *args, **kwargs) -> None:
            self.title = ""

        def run(self, setup=None) -> None:
            if setup:
                setup(self)
            deadline = time.time() + 2
            while time.time() < deadline:
                if event_log.exists() and "worker_error" in event_log.read_text(encoding="utf-8"):
                    return None
                time.sleep(0.05)
            return None

        def notify(self, *args, **kwargs) -> None:
            return None

        def stop(self) -> None:
            return None

    class FakeMenu:
        def __init__(self, *items) -> None:
            self.items = items

    class FakeMenuItem:
        def __init__(self, *args, **kwargs) -> None:
            self.args = args
            self.kwargs = kwargs

    codex_home = tmp_path / ".codex"
    config_dir = codex_home / "automation-safe-start"
    config_dir.mkdir(parents=True)
    (config_dir / "config.json").write_text(
        json.dumps({"launch": False, "cleanup": False}),
        encoding="utf-8",
    )
    event_log = config_dir / "events.jsonl"
    fake_pystray = types.ModuleType("pystray")
    fake_pystray.Icon = FakeIcon
    fake_pystray.Menu = FakeMenu
    fake_pystray.MenuItem = FakeMenuItem
    monkeypatch.setitem(sys.modules, "pystray", fake_pystray)
    monkeypatch.setenv("CODEX_HOME", str(codex_home))

    args = argparse.Namespace(
        config=None,
        initial_release=None,
        interval_minutes=None,
        startup_delay_seconds=None,
        min_future_lead_minutes=None,
        catchup_enabled=None,
        catchup_lookback_days=None,
        catchup_max_per_start=None,
        catchup_min_period_hours=None,
        dry_run=True,
        launch=None,
        cleanup=None,
    )

    assert command_tray(args) == 0
    text = event_log.read_text(encoding="utf-8")
    assert "worker_error" in text
    assert "SystemExit: Automations directory not found" in text


def test_rrule_next_after_hourly_interval_zero_no_crash() -> None:
    # INTERVAL=0 is invalid but must not cause ZeroDivisionError
    after = datetime(2026, 6, 4, 10, 0)
    next_at = rrule_next_after("RRULE:FREQ=HOURLY;INTERVAL=0;BYMINUTE=0", after)
    # interval clamped to 1 → next hit is 11:00
    assert next_at == datetime(2026, 6, 4, 11, 0)
