"""Regressionstests — safe-start-for-codex Desktop-Re-Sweep 2026-06-22 (Bugsweep-Loop-Lauf 20).

cli.py ist importierbar -> echte Unit-Tests wo moeglich; subprocess-timeouts statisch
(WMI/taskkill nicht deterministisch ausloesbar). Red-on-revert: SSF_SRC -> PRE-Backup-src.

  A01 windows_processes/kill_process_tree: subprocess.run ohne timeout -> WMI/taskkill-Hang.
  A02 windows_processes: stilles [] bei Fehler -> sichtbarer stderr-Hinweis.
  A03 set_status/write_snapshot: nicht-atomares write_text -> _atomic_write_text (tmp+os.replace).
  A04 process_age_seconds: nur ValueError gefangen -> auch TypeError (None/aware-Mix).
  B1 read_observed_runs_from_state: `with sqlite3.connect` schliesst nicht -> contextlib.closing.
  B3 command_status/command_restore_latest: json.loads ohne Guard -> try/except (korrupte latest.json).
"""
import argparse
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

_SRC = Path(os.environ.get("SSF_SRC", os.path.join(os.path.dirname(__file__), "..", "src")))
CLI = (_SRC / "safe_start_for_codex" / "cli.py").read_text(encoding="utf-8")


def has(n):
    return n in CLI


# --- echte Unit-Tests ---
def test_a04_process_age_seconds_guards():
    from safe_start_for_codex import cli
    assert cli.process_age_seconds(None) == float("inf")
    assert cli.process_age_seconds("not-a-date") == float("inf")
    # aware-Timestamp (Offset) vs naive now -> frueher TypeError, jetzt inf
    assert cli.process_age_seconds("2020-01-01T00:00:00+05:00") == float("inf")


def test_a03_atomic_write_no_tmp_left(tmp_path):
    from safe_start_for_codex import cli
    f = tmp_path / "x.json"
    cli._atomic_write_text(f, '{"a": 1}')
    assert f.read_text(encoding="utf-8") == '{"a": 1}'
    assert not (tmp_path / "x.json.tmp").exists()


def test_b3_command_status_corrupt_json_no_crash(tmp_path, monkeypatch):
    from safe_start_for_codex import cli
    (tmp_path / "latest.json").write_text("{ broken json", encoding="utf-8")
    monkeypatch.setattr(cli, "state_dir", lambda: tmp_path)
    rc = cli.command_status(argparse.Namespace())
    assert rc == 1  # lesbarer Fehler, kein JSONDecodeError-Crash


def test_b3_command_restore_latest_corrupt_json_no_crash(tmp_path, monkeypatch):
    from safe_start_for_codex import cli
    (tmp_path / "latest.json").write_text("{ broken", encoding="utf-8")
    monkeypatch.setattr(cli, "state_dir", lambda: tmp_path)
    rc = cli.command_restore_latest(argparse.Namespace())
    assert rc == 1


# --- statische Assertions (red-on-revert) ---
def test_a01_subprocess_timeouts():
    assert has("timeout=30") and has("timeout=15"), "A01 subprocess-timeouts fehlen"
    assert has("subprocess.TimeoutExpired"), "A01 TimeoutExpired-Handling fehlt"


def test_a02_windows_processes_visible_error():
    assert has("windows_processes fehlgeschlagen") or has("windows_processes returncode="), \
        "A02 sichtbarer Fehler fehlt"


def test_a03_atomic_helper_present():
    assert has("def _atomic_write_text") and has("os.replace(tmp, path)"), "A03 Helfer fehlt"


def test_a04_typeerror_caught():
    assert has("except (ValueError, TypeError):"), "A04 TypeError-Guard fehlt"


def test_b1_sqlite_closing():
    assert has("contextlib.closing(sqlite3.connect"), "B1 contextlib.closing fehlt"


def test_b3_json_guard_present():
    assert has("except (json.JSONDecodeError, OSError) as exc:"), "B3 json-Guard fehlt"


if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v"])
