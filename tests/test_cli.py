from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path

from safe_start_for_codex.cli import (
    Automation,
    load_automations,
    rrule_next_after,
    set_status,
    split_release_queue,
)


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
