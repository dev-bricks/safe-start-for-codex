from __future__ import annotations

import sqlite3
from datetime import datetime, timedelta
from pathlib import Path

import pytest

from safe_start_for_codex.cli import (
    SafeStartGate,
    build_catchup_report,
    load_automations,
    read_observed_runs_from_state,
    rrule_next_after,
    split_release_queue,
)


def create_synthetic_automation(
    codex_home: Path,
    automation_id: str,
    name: str,
    status: str,
    rrule: str,
    kind: str = "cron",
    created_at_ms: int = 1718000000000,
) -> Path:
    """Helper to generate a well-formed synthetic automation.toml in CODEX_HOME."""
    job_dir = codex_home / "automations" / automation_id
    job_dir.mkdir(parents=True, exist_ok=True)
    toml_path = job_dir / "automation.toml"
    content = [
        f'id = "{automation_id}"',
        f'name = "{name}"',
        f'kind = "{kind}"',
        f'rrule = "{rrule}"',
        f'status = "{status}"',
        f"created_at = {created_at_ms}",
        f"updated_at = {created_at_ms}",
        "",
    ]
    toml_path.write_text("\n".join(content), encoding="utf-8")
    return toml_path


# ---------------------------------------------------------------------------
# 1. Large Multi-Frequency Synthetic Collection (55 Automations)
# ---------------------------------------------------------------------------

def test_large_multi_schedule_collection_load(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Validate loading and structural integrity of 55 heterogeneous automations."""
    codex_home = tmp_path / ".codex"
    monkeypatch.setenv("CODEX_HOME", str(codex_home))

    schedules = [
        # 10 MINUTELY schedules (5 active, 5 paused)
        *[("minutely-5m", f"RRULE:FREQ=MINUTELY;INTERVAL={interval}", "ACTIVE") for interval in [5, 10, 15, 20, 30]],
        *[("minutely-hi", f"RRULE:FREQ=MINUTELY;INTERVAL={interval}", "PAUSED") for interval in [1, 2, 3, 4, 6]],
        # 10 HOURLY schedules (5 active, 5 paused)
        *[("hourly-reg", f"RRULE:FREQ=HOURLY;INTERVAL={interval};BYMINUTE=15", "ACTIVE") for interval in [1, 2, 4, 6, 12]],
        *[("hourly-offset", f"RRULE:FREQ=HOURLY;INTERVAL={interval};BYMINUTE=45", "PAUSED") for interval in [1, 3, 8, 12, 24]],
        # 15 DAILY schedules (10 active, 5 paused)
        *[("daily-workday", f"RRULE:FREQ=DAILY;BYHOUR={h};BYMINUTE=0", "ACTIVE") for h in [6, 7, 8, 9, 10, 11, 12, 13, 14, 15]],
        *[("daily-evening", f"RRULE:FREQ=DAILY;BYHOUR={h};BYMINUTE=30", "PAUSED") for h in [18, 19, 20, 21, 22]],
        # 10 WEEKLY schedules (5 active, 5 disabled)
        *[("weekly-weekday", f"RRULE:FREQ=WEEKLY;BYDAY={days};BYHOUR=9;BYMINUTE=0", "ACTIVE") for days in ["MO", "TU", "WE", "TH", "FR"]],
        *[("weekly-weekend", f"RRULE:FREQ=WEEKLY;BYDAY={days};BYHOUR=10;BYMINUTE=0", "DISABLED") for days in ["SA", "SU", "SA,SU", "MO,FR", "TU,TH"]],
        # 5 MONTHLY schedules (5 active)
        *[("monthly-check", f"RRULE:FREQ=MONTHLY;BYMONTHDAY={day};BYHOUR=8;BYMINUTE=0", "ACTIVE") for day in [1, 5, 10, 15, 28]],
        # 5 YEARLY schedules (5 active)
        *[("yearly-audit", f"RRULE:FREQ=YEARLY;BYMONTH={m};BYMONTHDAY=1;BYHOUR=0;BYMINUTE=0", "ACTIVE") for m in [1, 3, 6, 9, 12]],
    ]

    assert len(schedules) == 55

    for idx, (prefix, rrule, status) in enumerate(schedules, 1):
        job_id = f"synth-{idx:02d}-{prefix}"
        job_name = f"Synthetic Job #{idx:02d} ({prefix})"
        create_synthetic_automation(codex_home, job_id, job_name, status, rrule)

    loaded = load_automations()
    assert len(loaded) == 55

    active_items = [item for item in loaded if item.status == "ACTIVE"]
    paused_items = [item for item in loaded if item.status == "PAUSED"]
    disabled_items = [item for item in loaded if item.status == "DISABLED"]

    assert len(active_items) == 35
    assert len(paused_items) == 15
    assert len(disabled_items) == 5

    # Confirm unique IDs and valid paths
    all_ids = {item.id for item in loaded}
    assert len(all_ids) == 55
    for item in loaded:
        assert Path(item.path).exists()
        assert item.name.startswith("Synthetic Job #")
        assert item.kind == "cron"


# ---------------------------------------------------------------------------
# 2. Batch Splitting & Pacing Validation
# ---------------------------------------------------------------------------

def test_synthetic_collection_batch_splitting_and_pacing(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Verify that split_release_queue accurately partitions 38 active jobs into future-safe and fallback."""
    codex_home = tmp_path / ".codex"
    monkeypatch.setenv("CODEX_HOME", str(codex_home))

    reference = datetime(2026, 6, 1, 12, 0)
    lead_delta = timedelta(minutes=15)
    threshold = reference + lead_delta  # 12:15

    # Create 15 jobs due within 15 minutes (fallback / immediate)
    for m in range(0, 15):
        job_id = f"near-{m:02d}"
        rrule = f"RRULE:FREQ=DAILY;BYHOUR=12;BYMINUTE={m}"
        create_synthetic_automation(codex_home, job_id, f"Near {m}", "ACTIVE", rrule)

    # And 3 jobs already past their scheduled hour today (due tomorrow)
    for h in [9, 10, 11]:
        job_id = f"past-{h:02d}"
        rrule = f"RRULE:FREQ=DAILY;BYHOUR={h};BYMINUTE=0"
        create_synthetic_automation(codex_home, job_id, f"Past {h}", "ACTIVE", rrule)

    # Create 20 jobs due safely in the future (> 12:15)
    for m in range(20, 40):
        job_id = f"safe-{m:02d}"
        rrule = f"RRULE:FREQ=DAILY;BYHOUR=12;BYMINUTE={m}"
        create_synthetic_automation(codex_home, job_id, f"Safe {m}", "ACTIVE", rrule)

    automations = load_automations()
    assert len(automations) == 38

    future_safe, fallback = split_release_queue(automations, reference, lead_delta)

    # Every future_safe job must have next_at >= threshold
    for item in future_safe:
        assert item.next_at is not None
        next_dt = datetime.fromisoformat(item.next_at)
        assert next_dt >= threshold, f"Job {item.id} next_at {next_dt} is earlier than threshold {threshold}"

    # Every fallback job must have next_at < threshold or None
    for item in fallback:
        if item.next_at is not None:
            next_dt = datetime.fromisoformat(item.next_at)
            assert next_dt < threshold, f"Job {item.id} next_at {next_dt} is >= threshold {threshold}"

    # Verify monotonic ordering in future_safe
    future_timestamps = [datetime.fromisoformat(item.next_at) for item in future_safe]
    assert future_timestamps == sorted(future_timestamps)

    # Complete set parity
    assert len(future_safe) + len(fallback) == len(automations)
    assert set(item.id for item in future_safe) | set(item.id for item in fallback) == set(item.id for item in automations)


# ---------------------------------------------------------------------------
# 3. Full SafeStartGate Lifecycle Simulation (INV-RESTORE-04 & INV-FILE-03)
# ---------------------------------------------------------------------------

def test_safe_start_gate_synthetic_collection_lifecycle(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Validate pause_active, initial release, and selective restoration on a mixed collection."""
    codex_home = tmp_path / ".codex"
    monkeypatch.setenv("CODEX_HOME", str(codex_home))

    # Generate mixed collection: 20 ACTIVE, 6 PAUSED, 4 DISABLED
    for i in range(1, 21):
        create_synthetic_automation(codex_home, f"act-{i:02d}", f"Active {i}", "ACTIVE", "RRULE:FREQ=HOURLY;BYMINUTE=30")
    for i in range(1, 7):
        create_synthetic_automation(codex_home, f"pau-{i:02d}", f"Paused {i}", "PAUSED", "RRULE:FREQ=DAILY;BYHOUR=8;BYMINUTE=0")
    for i in range(1, 5):
        create_synthetic_automation(codex_home, f"dis-{i:02d}", f"Disabled {i}", "DISABLED", "RRULE:FREQ=WEEKLY;BYDAY=MO;BYHOUR=9;BYMINUTE=0")

    gate = SafeStartGate(
        initial_release=5,
        interval_minutes=1,
        startup_delay_seconds=0,
        launch=False,
        cleanup=False,
        catchup_enabled=False,
        dry_run=False,
        quiet=True,
    )

    gate.items = load_automations()
    assert len(gate.items) == 30

    # 1. Pause active automations
    gate.pause_active()

    assert len(gate.tool_paused) == 20
    # Pre-existing PAUSED and DISABLED items must not be marked tool_paused
    for item in gate.items:
        if item.id.startswith("act-"):
            assert item.tool_paused is True
            assert item.status == "PAUSED"
            # Read from disk to confirm atomic write
            disk_text = Path(item.path).read_text(encoding="utf-8")
            assert 'status = "PAUSED"' in disk_text
        elif item.id.startswith("pau-"):
            assert item.tool_paused is False
            assert item.status == "PAUSED"
        elif item.id.startswith("dis-"):
            assert item.tool_paused is False
            assert item.status == "DISABLED"

    # 2. Release initial lead batch of 5 items
    for item in gate.tool_paused[:5]:
        gate.release_item(item)
        assert item.released is True
        disk_text = Path(item.path).read_text(encoding="utf-8")
        assert 'status = "ACTIVE"' in disk_text

    # Status text check
    assert "5/20 released, 15 still gated" in gate.status_text()

    # 3. Simulate emergency restore (e.g. gate shutdown or restore-latest)
    gate.restore(reason="test_emergency_abort")

    # All 20 tool_paused items must now be restored to ACTIVE
    for item in gate.items:
        disk_text = Path(item.path).read_text(encoding="utf-8")
        if item.id.startswith("act-"):
            assert 'status = "ACTIVE"' in disk_text, f"{item.id} should have been restored to ACTIVE"
        elif item.id.startswith("pau-"):
            assert 'status = "PAUSED"' in disk_text, f"{item.id} should have remained PAUSED"
        elif item.id.startswith("dis-"):
            assert 'status = "DISABLED"' in disk_text, f"{item.id} should have remained DISABLED"


# ---------------------------------------------------------------------------
# 4. Catch-Up Report Integration with Synthetic SQLite State DB
# ---------------------------------------------------------------------------

def test_synthetic_catchup_report_with_simulated_sqlite_history(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Verify build_catchup_report with a synthetic SQLite threads database."""
    codex_home = tmp_path / ".codex"
    monkeypatch.setenv("CODEX_HOME", str(codex_home))

    state_db = codex_home / "state.db"
    state_db.parent.mkdir(parents=True, exist_ok=True)

    with sqlite3.connect(state_db) as conn:
        conn.execute("""
            CREATE TABLE threads (
                id TEXT PRIMARY KEY,
                title TEXT,
                created_at_ms INTEGER
            )
        """)
        # Insert a run for weekly-sync 2 days ago
        two_days_ago_ms = int((datetime.now() - timedelta(days=2)).timestamp() * 1000)
        conn.execute(
            "INSERT INTO threads (id, title, created_at_ms) VALUES (?, ?, ?)",
            ("th-01", "Run of weekly-sync-data", two_days_ago_ms),
        )
        # Insert a run for daily-digest 1 hour ago
        one_hour_ago_ms = int((datetime.now() - timedelta(hours=1)).timestamp() * 1000)
        conn.execute(
            "INSERT INTO threads (id, title, created_at_ms) VALUES (?, ?, ?)",
            ("th-02", "Automated daily-digest execution", one_hour_ago_ms),
        )

    # Rare monthly job (period >= 24h) with NO recent run (overdue!)
    create_synthetic_automation(
        codex_home,
        "monthly-backup",
        "Monthly Backup Report",
        "ACTIVE",
        "RRULE:FREQ=MONTHLY;BYMONTHDAY=1;BYHOUR=3;BYMINUTE=0",
    )
    # Rare weekly job (period >= 24h) that DID run 2 days ago
    create_synthetic_automation(
        codex_home,
        "weekly-sync",
        "weekly-sync-data",
        "ACTIVE",
        "RRULE:FREQ=WEEKLY;BYDAY=MO;BYHOUR=4;BYMINUTE=0",
    )
    # Frequent job (hourly, period < 24h, filtered out by min_period_hours=24)
    create_synthetic_automation(
        codex_home,
        "hourly-monitor",
        "Hourly Monitor",
        "ACTIVE",
        "RRULE:FREQ=HOURLY;BYMINUTE=0",
    )

    items = load_automations()
    assert len(items) == 3

    observed, db_path, notes = read_observed_runs_from_state(items, state_db=state_db)
    assert "weekly-sync" in observed
    assert len(observed["weekly-sync"]) == 1
    assert observed["weekly-sync"][0].thread_id == "th-01"

    report = build_catchup_report(
        items,
        state_db=state_db,
        lookback_days=30,
        min_period_hours=24,
        max_per_start=2,
    )

    assert report.history_source == str(state_db)
    # Only items with period > min_period_hours (24) are candidates (monthly-backup, weekly-sync)
    assert len(report.candidates) == 2

    # monthly-backup is rare, missed, and eligible
    monthly_cand = next(c for c in report.candidates if c.automation_id == "monthly-backup")
    assert monthly_cand.eligible is True or monthly_cand.missed is True

    # weekly-sync is also a candidate
    weekly_cand = next(c for c in report.candidates if c.automation_id == "weekly-sync")
    assert weekly_cand.period_hours > 24


# ---------------------------------------------------------------------------
# 5. Degraded & Edge-Case Synthetic Collection Resilience (INV-FAIL-08)
# ---------------------------------------------------------------------------

def test_corrupted_and_edge_case_synthetic_collection_resilience(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Verify safe loading and fallback handling under Unicode names and invalid rrules."""
    codex_home = tmp_path / ".codex"
    monkeypatch.setenv("CODEX_HOME", str(codex_home))

    # 1. Job with German umlauts and international UTF-8 characters
    create_synthetic_automation(
        codex_home,
        "tägliche-prüfung",
        "Tägliche Systemüberprüfung & Wartung",
        "ACTIVE",
        "RRULE:FREQ=DAILY;BYHOUR=7;BYMINUTE=30",
    )

    # 2. Job with malformed / unknown RRULE frequency
    create_synthetic_automation(
        codex_home,
        "invalid-rrule",
        "Invalid Rule Job",
        "ACTIVE",
        "RRULE:FREQ=CUSTOM_BIZARRE;INTERVAL=42",
    )

    # 3. Job with empty RRULE
    create_synthetic_automation(
        codex_home,
        "empty-rrule",
        "Empty Rule Job",
        "ACTIVE",
        "",
    )

    items = load_automations()
    assert len(items) == 3

    umlaut_job = next(item for item in items if item.id == "tägliche-prüfung")
    assert umlaut_job.name == "Tägliche Systemüberprüfung & Wartung"

    # Test rrule_next_after safety on invalid and empty rules
    now = datetime(2026, 6, 1, 8, 0)
    assert rrule_next_after("RRULE:FREQ=CUSTOM_BIZARRE;INTERVAL=42", now) is None
    assert rrule_next_after("", now) is None

    # split_release_queue must place invalid/empty rrules into fallback queue without crashing
    future_safe, fallback = split_release_queue(items, now, timedelta(minutes=15))
    fallback_ids = {item.id for item in fallback}
    assert "invalid-rrule" in fallback_ids
    assert "empty-rrule" in fallback_ids
