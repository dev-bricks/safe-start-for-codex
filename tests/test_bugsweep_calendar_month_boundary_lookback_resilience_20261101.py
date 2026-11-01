from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from safe_start_for_codex.cli import (
    Automation,
    ObservedRun,
    build_catchup_report,
)


def test_monthly_automation_lookback_window_boundary_on_31_day_months(tmp_path: Path) -> None:
    """Verify that rare monthly automations are correctly identified across 31-day months.

    When running just after midnight on day 1 of a month following a 31-day month
    (e.g., 2026-11-01 00:15 following October's 31 days), the previous run occurred
    31 days ago (Oct 1 03:00). A rigid 30-day lookback window would miss this occurrence.
    The scheduler's catchup logic dynamically extends the lookback window for monthly+
    schedules so overdue tasks are not silently skipped.
    """
    now = datetime(2026, 11, 1, 0, 15, tzinfo=timezone.utc)
    item = Automation(
        id="monthly-database-audit",
        name="Monthly Database Audit",
        path="monthly-database-audit.toml",
        original_status="ACTIVE",
        status="ACTIVE",
        kind="cron",
        rrule="RRULE:FREQ=MONTHLY;BYMONTHDAY=1;BYHOUR=3;BYMINUTE=0",
        created_at=int(datetime(2026, 8, 1, 0, 0, tzinfo=timezone.utc).timestamp() * 1000),
        updated_at=None,
    )

    report = build_catchup_report(
        [item],
        now=now,
        lookback_days=30,
        min_period_hours=24,
        max_per_start=1,
        observed_runs={"monthly-database-audit": []},
    )

    assert len(report.candidates) == 1
    candidate = report.candidates[0]
    assert candidate.automation_id == "monthly-database-audit"
    assert candidate.missed is True
    assert candidate.eligible is True
    assert "2026-10-01" in str(candidate.last_due_at)


def test_monthly_automation_satisfied_by_observed_run_in_previous_month(tmp_path: Path) -> None:
    """Verify that observed runs within the previous 31-day month correctly satisfy the schedule."""
    now = datetime(2026, 11, 1, 0, 15, tzinfo=timezone.utc)
    item = Automation(
        id="monthly-healthcheck",
        name="Monthly Healthcheck",
        path="monthly-healthcheck.toml",
        original_status="ACTIVE",
        status="ACTIVE",
        kind="cron",
        rrule="RRULE:FREQ=MONTHLY;BYMONTHDAY=1;BYHOUR=3;BYMINUTE=0",
        created_at=int(datetime(2026, 8, 1, 0, 0, tzinfo=timezone.utc).timestamp() * 1000),
        updated_at=None,
    )

    observed_runs = {
        "monthly-healthcheck": [
            ObservedRun(
                automation_id="monthly-healthcheck",
                thread_id="th-monthly-oct",
                created_at="2026-10-01T03:05:00+00:00",
                title="Run of Monthly Healthcheck",
            )
        ]
    }

    report = build_catchup_report(
        [item],
        now=now,
        lookback_days=30,
        min_period_hours=24,
        max_per_start=1,
        observed_runs=observed_runs,
    )

    assert len(report.candidates) == 1
    candidate = report.candidates[0]
    assert candidate.missed is False
    assert candidate.eligible is False
    assert candidate.reason == "observed after latest due time"
