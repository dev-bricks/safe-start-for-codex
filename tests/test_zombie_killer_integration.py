from __future__ import annotations

import json
import subprocess
from pathlib import Path
from types import SimpleNamespace

from safe_start_for_codex.zombie_killer_integration import (
    ZOMBIE_KILLER_PACKAGE_SPEC,
    ZOMBIE_KILLER_SOURCE_ENV,
    build_zombie_killer_status,
    install_zombie_killer_package,
    launch_zombie_killer_watch,
    zombie_killer_install_target,
    zombie_killer_state_dir,
)


def test_state_dir_is_under_codex_home(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("CODEX_HOME", str(tmp_path / ".codex"))
    state_dir = zombie_killer_state_dir()
    assert state_dir == tmp_path / ".codex" / "zombie-killer-tray"
    assert state_dir.is_dir(), "must create the directory"


def test_install_target_falls_back_to_pinned_github_spec_without_local_source(
    monkeypatch,
) -> None:
    monkeypatch.delenv(ZOMBIE_KILLER_SOURCE_ENV, raising=False)
    monkeypatch.setattr(
        "safe_start_for_codex.zombie_killer_integration._local_zombie_killer_source",
        lambda: None,
    )
    assert zombie_killer_install_target() == ZOMBIE_KILLER_PACKAGE_SPEC


def test_install_target_prefers_local_source_env_override(tmp_path: Path, monkeypatch) -> None:
    local = tmp_path / "local-zkt"
    local.mkdir()
    (local / "pyproject.toml").write_text("[project]\nname='x'\n", encoding="utf-8")
    monkeypatch.setenv(ZOMBIE_KILLER_SOURCE_ENV, str(local))
    assert zombie_killer_install_target() == str(local)


def test_install_zombie_killer_package_reports_ok_on_zero_exit() -> None:
    calls: list[list[str]] = []

    def fake_runner(command: list[str]) -> subprocess.CompletedProcess[str]:
        calls.append(command)
        return subprocess.CompletedProcess(command, returncode=0, stdout="installed", stderr="")

    result = install_zombie_killer_package(target="some-target", runner=fake_runner)

    assert result.status == "ok"
    assert calls[0][-3:] == ["install", "--upgrade", "some-target"]


def test_install_zombie_killer_package_reports_failed_on_nonzero_exit() -> None:
    def fake_runner(command: list[str]) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(command, returncode=1, stdout="", stderr="boom")

    result = install_zombie_killer_package(target="some-target", runner=fake_runner)

    assert result.status == "failed"
    assert "boom" in result.stderr


def test_launch_refuses_cleanly_on_non_windows(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("CODEX_HOME", str(tmp_path / ".codex"))
    monkeypatch.setattr(
        "safe_start_for_codex.zombie_killer_integration._is_windows", lambda: False
    )

    called = False

    def fake_popen(command, **kwargs):
        nonlocal called
        called = True
        return SimpleNamespace(pid=1)

    result = launch_zombie_killer_watch(popen=fake_popen)

    assert result.status == "unsupported-platform"
    assert called is False, "must never attempt to spawn on a non-Windows platform"


def test_launch_invokes_module_with_expected_args_on_windows(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("CODEX_HOME", str(tmp_path / ".codex"))
    captured: dict[str, object] = {}

    def fake_popen(command, **kwargs):
        captured["command"] = command
        captured["cwd"] = kwargs.get("cwd")
        return SimpleNamespace(pid=4242)

    result = launch_zombie_killer_watch(interval_seconds=42, min_age_seconds=99, popen=fake_popen)

    assert result.status == "ok"
    assert result.pid == 4242
    command = captured["command"]
    assert "-m" in command
    assert "zombie_killer_tray" in command
    assert "watch" in command
    assert "--interval" in command and "42" in command
    assert "--min-age" in command and "99" in command
    assert "--parent-pid" in command
    assert "--yes" in command
    assert captured["cwd"] == str(tmp_path / ".codex" / "zombie-killer-tray")


def test_launch_reports_failure_when_no_python_found(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("CODEX_HOME", str(tmp_path / ".codex"))

    def failing_popen(command, **kwargs):
        raise OSError("no interpreter")

    result = launch_zombie_killer_watch(popen=failing_popen)

    assert result.status == "failed"
    assert "no interpreter" in result.message


def test_build_status_reads_last_cycle_from_events_log(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("CODEX_HOME", str(tmp_path / ".codex"))
    state_dir = zombie_killer_state_dir()
    events = state_dir / "zombie_events.jsonl"
    with events.open("w", encoding="utf-8") as handle:
        handle.write(json.dumps({"cycle_at": 111.0, "apply": False, "count": 0}) + "\n")
        handle.write(json.dumps({"cycle_at": 222.0, "apply": True, "count": 3}) + "\n")
        handle.write(json.dumps({"event": "broker-superseded-idle", "root_pid": 5}) + "\n")

    status = build_zombie_killer_status()

    assert status.last_cycle_at == 222.0
    assert status.last_cycle_count == 3
    assert status.state_dir == str(state_dir)


def test_build_status_handles_missing_log(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("CODEX_HOME", str(tmp_path / ".codex"))

    status = build_zombie_killer_status()

    assert status.last_cycle_at is None
    assert status.last_cycle_count is None


def test_build_status_marks_non_windows_as_unsupported(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("CODEX_HOME", str(tmp_path / ".codex"))
    monkeypatch.setattr(
        "safe_start_for_codex.zombie_killer_integration._is_windows", lambda: False
    )

    status = build_zombie_killer_status()

    assert status.supported_platform is False
    assert status.available is False
    assert any("Windows-only" in note for note in status.notes)
