"""Hermetic regression tests for bugsweep 2026-09-28:
- RRULE monthly/yearly recurrence with BYDAY and positional ordinals (e.g. 1MO, -1FR).
- TOML parsing and status update resilience with single quotes and inline comments.
"""
from datetime import datetime, timezone
from pathlib import Path

import pytest
from safe_start_for_codex.cli import (
    int_value,
    load_automations,
    quoted_value,
    rrule_next_after,
    rrule_occurrences_between,
    set_status,
)


def test_rrule_monthly_byday_first_weekday() -> None:
    # Event starting on Monday, June 15, 2026, repeating on the first Monday of every month
    dtstart = datetime(2026, 6, 15, 9, 0, tzinfo=timezone.utc)
    after = datetime(2026, 6, 16, 0, 0, tzinfo=timezone.utc)
    rule = "FREQ=MONTHLY;BYDAY=1MO;BYHOUR=9;BYMINUTE=0"

    nxt = rrule_next_after(rule, after, dtstart=dtstart)
    # July 2026: 1st Monday is July 6
    assert nxt == datetime(2026, 7, 6, 9, 0, tzinfo=timezone.utc)

    # Occurrences across July, August, September 2026
    # July 6, August 3, September 7
    occ = rrule_occurrences_between(
        rule,
        datetime(2026, 7, 1, tzinfo=timezone.utc),
        datetime(2026, 9, 30, tzinfo=timezone.utc),
        dtstart=dtstart,
    )
    assert occ == [
        datetime(2026, 7, 6, 9, 0, tzinfo=timezone.utc),
        datetime(2026, 8, 3, 9, 0, tzinfo=timezone.utc),
        datetime(2026, 9, 7, 9, 0, tzinfo=timezone.utc),
    ]


def test_rrule_monthly_byday_last_weekday() -> None:
    # Last Friday of every month at 17:00
    dtstart = datetime(2026, 6, 1, 17, 0, tzinfo=timezone.utc)
    rule = "RRULE:FREQ=MONTHLY;BYDAY=-1FR;BYHOUR=17;BYMINUTE=0"

    # Next after July 1st -> July 31st (last Friday of July 2026)
    nxt = rrule_next_after(rule, datetime(2026, 7, 1, 0, 0, tzinfo=timezone.utc), dtstart=dtstart)
    assert nxt == datetime(2026, 7, 31, 17, 0, tzinfo=timezone.utc)

    # Occurrences between July 1 and Oct 1: July 31, Aug 28, Sept 25
    occ = rrule_occurrences_between(
        rule,
        datetime(2026, 7, 1, tzinfo=timezone.utc),
        datetime(2026, 10, 1, tzinfo=timezone.utc),
        dtstart=dtstart,
    )
    assert occ == [
        datetime(2026, 7, 31, 17, 0, tzinfo=timezone.utc),
        datetime(2026, 8, 28, 17, 0, tzinfo=timezone.utc),
        datetime(2026, 9, 25, 17, 0, tzinfo=timezone.utc),
    ]


def test_rrule_monthly_byday_all_matching_weekdays() -> None:
    # Every Monday of the month at 10:00 (no ordinal prefix on BYDAY)
    dtstart = datetime(2026, 6, 1, 10, 0, tzinfo=timezone.utc)
    rule = "FREQ=MONTHLY;BYDAY=MO;BYHOUR=10;BYMINUTE=0"

    # July 2026 has 4 Mondays: July 6, 13, 20, 27
    occ = rrule_occurrences_between(
        rule,
        datetime(2026, 7, 1, tzinfo=timezone.utc),
        datetime(2026, 7, 31, 23, 59, tzinfo=timezone.utc),
        dtstart=dtstart,
    )
    assert len(occ) == 4
    assert occ == [
        datetime(2026, 7, 6, 10, 0, tzinfo=timezone.utc),
        datetime(2026, 7, 13, 10, 0, tzinfo=timezone.utc),
        datetime(2026, 7, 20, 10, 0, tzinfo=timezone.utc),
        datetime(2026, 7, 27, 10, 0, tzinfo=timezone.utc),
    ]


def test_rrule_yearly_byday_positional() -> None:
    # 2nd Tuesday of October at 14:00 every year
    dtstart = datetime(2026, 1, 1, 14, 0, tzinfo=timezone.utc)
    rule = "FREQ=YEARLY;BYMONTH=10;BYDAY=2TU;BYHOUR=14;BYMINUTE=0"

    # October 2026: Oct 1 is Thursday -> Tuesdays are Oct 6 (1st) and Oct 13 (2nd)
    nxt = rrule_next_after(rule, datetime(2026, 1, 1, 0, 0, tzinfo=timezone.utc), dtstart=dtstart)
    assert nxt == datetime(2026, 10, 13, 14, 0, tzinfo=timezone.utc)


def test_toml_quoted_value_and_int_value_resilience() -> None:
    text = (
        'id = "sample-job"\n'
        "name = 'Sample Automation' # display label\n"
        "status = 'ACTIVE'   # currently enabled\n"
        "kind = 'cron'\n"
        "rrule = 'FREQ=DAILY;BYHOUR=9;BYMINUTE=0'  # every morning\n"
        "created_at = 1780000000000\n"
        "updated_at = 1790507281442   # last run ms\n"
    )

    assert quoted_value(text, "id") == "sample-job"
    assert quoted_value(text, "name") == "Sample Automation"
    assert quoted_value(text, "status") == "ACTIVE"
    assert quoted_value(text, "kind") == "cron"
    assert quoted_value(text, "rrule") == "FREQ=DAILY;BYHOUR=9;BYMINUTE=0"
    assert int_value(text, "created_at") == 1780000000000
    assert int_value(text, "updated_at") == 1790507281442


def test_load_automations_parses_single_quoted_and_commented_tomls(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    auto_dir = tmp_path / "automations" / "sample-job"
    auto_dir.mkdir(parents=True)
    toml = auto_dir / "automation.toml"
    toml.write_text(
        'id = "sample-job"\n'
        "name = 'Sample Automation' # display label\n"
        "status = 'ACTIVE'   # currently enabled\n"
        "kind = 'cron'\n"
        "rrule = 'FREQ=DAILY;BYHOUR=9;BYMINUTE=0'  # every morning\n"
        "created_at = 1780000000000\n"
        "updated_at = 1790507281442   # last run ms\n",
        encoding="utf-8",
    )
    monkeypatch.setattr("safe_start_for_codex.cli.automations_dir", lambda: tmp_path / "automations")
    items = load_automations()
    assert len(items) == 1
    assert items[0].id == "sample-job"
    assert items[0].name == "Sample Automation"
    assert items[0].status == "ACTIVE"
    assert items[0].original_status == "ACTIVE"
    assert items[0].rrule == "FREQ=DAILY;BYHOUR=9;BYMINUTE=0"
    assert items[0].created_at == 1780000000000
    assert items[0].updated_at == 1790507281442


def test_set_status_with_single_quotes_and_inline_comments(tmp_path: Path) -> None:
    toml_path = tmp_path / "automation.toml"
    initial_content = (
        'id = "test-job"\n'
        "status = 'ACTIVE'  # managed\n"
        "updated_at = 1780000000000  # initial\n"
    )
    toml_path.write_text(initial_content, encoding="utf-8")

    # Set status to PAUSED
    changed = set_status(toml_path, "PAUSED")
    assert changed is True

    updated_content = toml_path.read_text(encoding="utf-8")
    lines = [line.strip() for line in updated_content.splitlines() if line.strip()]

    # Must NOT have duplicate status lines
    status_lines = [line for line in lines if line.startswith("status")]
    assert len(status_lines) == 1
    assert status_lines[0] == 'status = "PAUSED"'

    # updated_at must be updated and single
    updated_at_lines = [line for line in lines if line.startswith("updated_at")]
    assert len(updated_at_lines) == 1
    assert not updated_at_lines[0].startswith("updated_at = 1780000000000")
