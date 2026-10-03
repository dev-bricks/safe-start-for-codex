from __future__ import annotations

import json
import threading
import urllib.error
import urllib.request
from pathlib import Path

import pytest

from safe_start_for_codex.dashboard import (
    DashboardRequestHandler,
    create_dashboard_server,
    get_dashboard_data,
)
from safe_start_for_codex.zombie_killer_integration import (
    _read_watch_pid_file,
    _verify_watch_process,
    build_zombie_killer_status,
)


def test_dashboard_data_null_items_in_snapshot(tmp_path: Path, monkeypatch) -> None:
    """Snapshot with 'items': None must not raise TypeError."""
    monkeypatch.setattr("safe_start_for_codex.cli.load_automations", lambda: [])
    latest = {
        "run_id": "20261003-01",
        "phase": "gated",
        "items": None,
        "tool_paused_ids": None,
        "released_ids": None,
    }
    (tmp_path / "latest.json").write_text(json.dumps(latest), encoding="utf-8")
    data = get_dashboard_data(state_dir_path=tmp_path)
    assert data["items"] == []
    assert data["tool_paused_ids"] == []
    assert data["released_ids"] == []
    assert data["counts"]["total"] == 0


def test_dashboard_data_null_catchup_fields(tmp_path: Path) -> None:
    """Catchup file with 'candidates': None and 'eligible_ids': None must not raise TypeError."""
    catchup = {
        "run_id": "20261003-01",
        "candidates": None,
        "eligible_ids": None,
    }
    (tmp_path / "latest-catchup-plan.json").write_text(json.dumps(catchup), encoding="utf-8")
    data = get_dashboard_data(state_dir_path=tmp_path)
    assert data["catchup"]["candidates_count"] == 0
    assert data["catchup"]["candidates"] == []
    assert data["catchup"]["eligible_ids"] == []


def test_dashboard_data_corrupt_config_file_system_exit(tmp_path: Path, monkeypatch) -> None:
    """Corrupted safe-start-gate.json must not raise SystemExit, killing the server."""
    bad_config = tmp_path / "safe-start-gate.json"
    bad_config.write_text("{\"invalid_key_xyz\": 123}", encoding="utf-8")
    monkeypatch.setattr("safe_start_for_codex.cli.default_config_path", lambda: bad_config)

    data = get_dashboard_data(state_dir_path=tmp_path)
    assert isinstance(data, dict)
    assert "config" in data
    assert data["config"]["exists"] is False or "error" in data["config"]


def test_dashboard_server_queue_and_automations_null_fields(tmp_path: Path, monkeypatch) -> None:
    """Queue and automations endpoints must handle None/malformed data gracefully."""
    server = create_dashboard_server(host="127.0.0.1", port=0, state_dir_path=tmp_path)
    port = server.server_port
    base_url = f"http://127.0.0.1:{port}"

    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()

    try:
        # Mock get_dashboard_data returning None for items/counts/tool_paused_ids
        monkeypatch.setattr(
            "safe_start_for_codex.dashboard.get_dashboard_data",
            lambda *args, **kwargs: {
                "phase": "gated",
                "run_id": "mock-run",
                "counts": None,
                "tool_paused_ids": None,
                "released_ids": None,
                "items": None,
            },
        )

        with urllib.request.urlopen(f"{base_url}/api/queue", timeout=5) as resp:
            assert resp.status == 200
            q_data = json.loads(resp.read().decode("utf-8"))
            assert q_data["items"] == []

        with urllib.request.urlopen(f"{base_url}/api/automations", timeout=5) as resp:
            assert resp.status == 200
            a_data = json.loads(resp.read().decode("utf-8"))
            assert a_data["total"] == 0
            assert a_data["items"] == []
    finally:
        server.shutdown()
        server.server_close()


def test_dashboard_server_head_vs_get_endpoint_parity_rfc9110(tmp_path: Path) -> None:
    """HEAD /api/unknown must return 404, matching GET /api/unknown."""
    server = create_dashboard_server(host="127.0.0.1", port=0, state_dir_path=tmp_path)
    port = server.server_port
    base_url = f"http://127.0.0.1:{port}"

    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()

    try:
        req_head = urllib.request.Request(f"{base_url}/api/nonexistent_endpoint", method="HEAD")
        with pytest.raises(urllib.error.HTTPError) as exc_head:
            urllib.request.urlopen(req_head, timeout=5)
        assert exc_head.value.code == 404

        with pytest.raises(urllib.error.HTTPError) as exc_get:
            urllib.request.urlopen(f"{base_url}/api/nonexistent_endpoint", timeout=5)
        assert exc_get.value.code == 404
    finally:
        server.shutdown()
        server.server_close()


def test_dashboard_server_trailing_slash_resilience(tmp_path: Path) -> None:
    """Endpoints with trailing slash (/api/status/) must resolve seamlessly."""
    server = create_dashboard_server(host="127.0.0.1", port=0, state_dir_path=tmp_path)
    port = server.server_port
    base_url = f"http://127.0.0.1:{port}"

    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()

    try:
        for ep in ["status", "queue", "automations", "catchup", "config"]:
            with urllib.request.urlopen(f"{base_url}/api/{ep}/", timeout=5) as resp:
                assert resp.status == 200
                assert "application/json" in resp.headers.get("Content-Type", "")
    finally:
        server.shutdown()
        server.server_close()


def test_dashboard_handler_with_generic_httpserver(tmp_path: Path) -> None:
    """Handler must not crash with AttributeError when server lacks state_dir_path."""
    import http.server

    generic_server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), DashboardRequestHandler)
    port = generic_server.server_port
    base_url = f"http://127.0.0.1:{port}"

    thread = threading.Thread(target=generic_server.serve_forever, daemon=True)
    thread.start()

    try:
        with urllib.request.urlopen(f"{base_url}/api/status", timeout=5) as resp:
            assert resp.status == 200
    finally:
        generic_server.shutdown()
        generic_server.server_close()


def test_zombie_killer_status_malformed_cycle_event(tmp_path: Path, monkeypatch) -> None:
    """Non-numeric or null cycle_at / count in audit log must not raise TypeError/ValueError."""
    monkeypatch.setenv("CODEX_HOME", str(tmp_path / ".codex"))
    s_dir = tmp_path / ".codex" / "zombie-killer-tray"
    s_dir.mkdir(parents=True, exist_ok=True)
    events_file = s_dir / "zombie_events.jsonl"

    # Write events with null and string values
    events_file.write_text(
        json.dumps({"cycle_at": None, "count": None}) + "\n"
        + json.dumps({"cycle_at": "not-a-float", "count": "not-an-int"}) + "\n",
        encoding="utf-8",
    )

    status = build_zombie_killer_status()
    assert status.last_cycle_at is None
    assert status.last_cycle_count is None


def test_read_watch_pid_file_non_dict_json(tmp_path: Path) -> None:
    """watch.pid with JSON string, list or integer must not raise AttributeError."""
    pid_file = tmp_path / "watch.pid"
    pid_file.write_text(json.dumps("string-not-dict"), encoding="utf-8")
    assert _read_watch_pid_file(tmp_path) is None

    pid_file.write_text(json.dumps([123, 456]), encoding="utf-8")
    assert _read_watch_pid_file(tmp_path) is None


def test_verify_watch_process_non_positive_pid() -> None:
    """Non-positive PID (-1 or 0) must return False, not raise ValueError."""
    assert _verify_watch_process(-1, None) is False
