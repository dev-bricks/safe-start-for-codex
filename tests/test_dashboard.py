from __future__ import annotations

import json
import threading
import urllib.error
import urllib.request
from pathlib import Path

import pytest

from safe_start_for_codex.cli import build_parser
from safe_start_for_codex.dashboard import (
    create_dashboard_server,
    get_dashboard_data,
    get_dashboard_html,
)


def test_dashboard_data_empty_state(tmp_path: Path) -> None:
    data = get_dashboard_data(state_dir_path=tmp_path)
    assert isinstance(data, dict)
    assert data["snapshot_exists"] is False
    assert data["snapshot_corrupt"] is False
    assert data["phase"] == "no-snapshot"
    assert data["tool_paused_ids"] == []
    assert data["released_ids"] == []
    assert "counts" in data
    assert "config" in data


def test_dashboard_data_with_snapshot(tmp_path: Path) -> None:
    latest = {
        "run_id": "20260930-120000",
        "phase": "gated",
        "created_at": "2026-09-30T12:00:00+02:00",
        "tool_paused_ids": ["auto-1", "auto-2"],
        "released_ids": ["auto-1"],
        "items": [
            {"id": "auto-1", "name": "Auto One", "status": "ACTIVE", "tool_paused": True, "released": True},
            {"id": "auto-2", "name": "Auto Two", "status": "PAUSED", "tool_paused": True, "released": False},
        ],
    }
    (tmp_path / "latest.json").write_text(json.dumps(latest), encoding="utf-8")

    catchup = {
        "run_id": "20260930-120000",
        "eligible_ids": ["auto-rare"],
        "candidates": [
            {
                "automation_id": "auto-rare",
                "name": "Rare Task",
                "period_hours": 168.0,
                "missed": True,
                "eligible": True,
                "reason": "eligible for early release",
            }
        ],
    }
    (tmp_path / "latest-catchup-plan.json").write_text(json.dumps(catchup), encoding="utf-8")

    data = get_dashboard_data(state_dir_path=tmp_path)
    assert data["snapshot_exists"] is True
    assert data["snapshot_corrupt"] is False
    assert data["phase"] == "gated"
    assert data["run_id"] == "20260930-120000"
    assert data["tool_paused_ids"] == ["auto-1", "auto-2"]
    assert data["released_ids"] == ["auto-1"]
    assert data["counts"]["tool_paused"] == 2
    assert data["counts"]["released"] == 1
    assert data["counts"]["still_gated"] == 1
    assert data["catchup"]["eligible_ids"] == ["auto-rare"]
    assert data["catchup"]["candidates_count"] == 1


def test_dashboard_data_corrupt_snapshot(tmp_path: Path) -> None:
    (tmp_path / "latest.json").write_text("{broken json string...", encoding="utf-8")
    data = get_dashboard_data(state_dir_path=tmp_path)
    assert data["snapshot_exists"] is True
    assert data["snapshot_corrupt"] is True
    assert data["snapshot_error"] != ""
    assert data["phase"] == "idle"


def test_dashboard_html_rendering() -> None:
    html = get_dashboard_html()
    assert "<!DOCTYPE html>" in html
    assert "Safe Start for Codex" in html
    assert "Release Queue" in html
    assert "/api/status" in html

    # Zero-Egress isolation invariant: No external script or stylesheet CDNs allowed
    assert "<script src=" not in html
    assert '<link rel="stylesheet" href="http' not in html
    assert "https://" not in html


def test_dashboard_server_endpoints(tmp_path: Path) -> None:
    latest = {
        "run_id": "20260930-150000",
        "phase": "released",
        "created_at": "2026-09-30T15:00:00+02:00",
        "tool_paused_ids": ["test-task"],
        "released_ids": ["test-task"],
        "items": [
            {"id": "test-task", "name": "Test Task", "status": "ACTIVE", "tool_paused": True, "released": True}
        ],
    }
    (tmp_path / "latest.json").write_text(json.dumps(latest), encoding="utf-8")

    server = create_dashboard_server(host="127.0.0.1", port=0, state_dir_path=tmp_path)
    port = server.server_port
    base_url = f"http://127.0.0.1:{port}"

    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()

    try:
        # 1. GET / (HTML Dashboard)
        with urllib.request.urlopen(f"{base_url}/", timeout=5) as resp:
            assert resp.status == 200
            assert "text/html" in resp.headers.get("Content-Type", "")
            assert resp.headers.get("X-Content-Type-Options") == "nosniff"
            assert resp.headers.get("X-Frame-Options") == "DENY"
            body = resp.read().decode("utf-8")
            assert "Safe Start for Codex" in body

        # 2. HEAD /
        req_head = urllib.request.Request(f"{base_url}/", method="HEAD")
        with urllib.request.urlopen(req_head, timeout=5) as resp:
            assert resp.status == 200
            assert "text/html" in resp.headers.get("Content-Type", "")

        # 3. GET /api/status (JSON API)
        with urllib.request.urlopen(f"{base_url}/api/status", timeout=5) as resp:
            assert resp.status == 200
            assert "application/json" in resp.headers.get("Content-Type", "")
            data = json.loads(resp.read().decode("utf-8"))
            assert data["phase"] == "released"
            assert data["run_id"] == "20260930-150000"
            assert data["counts"]["tool_paused"] == 1
            assert data["counts"]["released"] == 1

        # 4. GET /api/queue
        with urllib.request.urlopen(f"{base_url}/api/queue", timeout=5) as resp:
            assert resp.status == 200
            q_data = json.loads(resp.read().decode("utf-8"))
            assert q_data["tool_paused_ids"] == ["test-task"]
            assert len(q_data["items"]) == 1

        # 5. GET /api/automations
        with urllib.request.urlopen(f"{base_url}/api/automations", timeout=5) as resp:
            assert resp.status == 200
            a_data = json.loads(resp.read().decode("utf-8"))
            assert "items" in a_data

        # 6. GET /api/catchup
        with urllib.request.urlopen(f"{base_url}/api/catchup", timeout=5) as resp:
            assert resp.status == 200
            c_data = json.loads(resp.read().decode("utf-8"))
            assert "eligible_ids" in c_data

        # 7. GET /api/config
        with urllib.request.urlopen(f"{base_url}/api/config", timeout=5) as resp:
            assert resp.status == 200
            cfg_data = json.loads(resp.read().decode("utf-8"))
            assert "settings" in cfg_data

        # 8. GET /favicon.ico
        with urllib.request.urlopen(f"{base_url}/favicon.ico", timeout=5) as resp:
            assert resp.status == 200
            assert "image/svg+xml" in resp.headers.get("Content-Type", "")

        # 9. GET 404 for unknown endpoints
        with pytest.raises(urllib.error.HTTPError) as exc_info:
            urllib.request.urlopen(f"{base_url}/nonexistent-route", timeout=5)
        assert exc_info.value.code == 404
        assert exc_info.value.headers.get("X-Content-Type-Options") == "nosniff"

    finally:
        server.shutdown()
        server.server_close()


def test_cli_dashboard_subcommand_registered() -> None:
    parser = build_parser()
    args = parser.parse_args(["dashboard", "--host", "127.0.0.1", "--port", "9999", "--open-browser"])
    assert args.command == "dashboard"
    assert args.host == "127.0.0.1"
    assert args.port == 9999
    assert args.open_browser is True
    assert hasattr(args, "func")
