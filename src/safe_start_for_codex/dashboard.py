"""Lightweight local web dashboard for Safe Start for Codex.

Provides real-time visualization of automation gating states, staged release queues,
catch-up planner diagnostics, and configuration without external dependencies (pure stdlib).
"""

from __future__ import annotations

import http.server
import json
import threading
import urllib.parse
import webbrowser
from datetime import datetime
from pathlib import Path
from typing import Any

from . import __version__


def get_dashboard_data(state_dir_path: Path | None = None) -> dict[str, Any]:
    """Collect current gating, snapshot, queue, and configuration data."""
    from .cli import (
        load_automations,
        read_gate_config,
        state_dir,
    )

    s_dir = state_dir_path if state_dir_path is not None else state_dir()
    latest_file = s_dir / "latest.json"
    catchup_file = s_dir / "latest-catchup-plan.json"

    snapshot_data: dict[str, Any] = {}
    snapshot_exists = latest_file.exists()
    snapshot_corrupt = False
    snapshot_error = ""

    if snapshot_exists:
        try:
            raw = latest_file.read_text(encoding="utf-8")
            parsed = json.loads(raw)
            if isinstance(parsed, dict):
                snapshot_data = parsed
            else:
                snapshot_corrupt = True
                snapshot_error = "Snapshot is not a JSON object"
        except (json.JSONDecodeError, OSError) as exc:
            snapshot_corrupt = True
            snapshot_error = str(exc)

    # Live automations inspection
    live_items: list[dict[str, Any]] = []
    live_error = ""
    try:
        loaded = load_automations()
        for it in loaded:
            live_items.append(
                {
                    "id": it.id,
                    "name": it.name,
                    "status": it.status,
                    "original_status": it.original_status,
                    "rrule": it.rrule,
                    "path": str(it.path),
                    "tool_paused": it.tool_paused,
                    "released": it.released,
                    "next_at": it.next_at,
                }
            )
    except SystemExit as exc:
        live_error = f"Automations directory unavailable: {exc}"
    except Exception as exc:
        live_error = str(exc)

    # Merge snapshot items and live items
    raw_snapshot_items = snapshot_data.get("items")
    snapshot_items_list = raw_snapshot_items if isinstance(raw_snapshot_items, list) else []

    items_by_id: dict[str, dict[str, Any]] = {}
    for it in snapshot_items_list:
        if isinstance(it, dict) and "id" in it:
            items_by_id[it["id"]] = dict(it)
    for it in live_items:
        items_by_id[it["id"]] = {**items_by_id.get(it["id"], {}), **it}

    items_to_report = list(items_by_id.values()) if items_by_id else live_items
    if not isinstance(items_to_report, list):
        items_to_report = []

    active_count = sum(1 for it in items_to_report if isinstance(it, dict) and str(it.get("status", "")).upper() == "ACTIVE")
    paused_count = sum(1 for it in items_to_report if isinstance(it, dict) and str(it.get("status", "")).upper() == "PAUSED")
    disabled_count = sum(1 for it in items_to_report if isinstance(it, dict) and str(it.get("status", "")).upper() == "DISABLED")
    total_count = len(items_to_report)

    tool_paused_ids = snapshot_data.get("tool_paused_ids")
    if not isinstance(tool_paused_ids, list):
        tool_paused_ids = []
    released_ids = snapshot_data.get("released_ids")
    if not isinstance(released_ids, list):
        released_ids = []

    # Catch-up report inspection
    catchup_data: dict[str, Any] = {}
    if catchup_file.exists():
        try:
            c_raw = catchup_file.read_text(encoding="utf-8")
            c_parsed = json.loads(c_raw)
            if isinstance(c_parsed, dict):
                catchup_data = c_parsed
        except Exception:
            pass

    catchup_candidates = catchup_data.get("candidates")
    if not isinstance(catchup_candidates, list):
        catchup_candidates = []

    catchup_eligible = catchup_data.get("eligible_ids")
    if not isinstance(catchup_eligible, list):
        catchup_eligible = []

    # Config settings - resilient against malformed/corrupt configs without SystemExit
    config_error = ""
    try:
        settings, config_path, config_exists = read_gate_config()
    except (SystemExit, Exception) as exc:
        from .cli import GateSettings, default_config_path

        settings = GateSettings()
        config_path = default_config_path()
        config_exists = False
        config_error = str(exc)

    phase = snapshot_data.get("phase", "idle")
    if not snapshot_exists:
        phase = "no-snapshot"

    return {
        "version": __version__,
        "timestamp": datetime.now().astimezone().isoformat(timespec="seconds"),
        "state_dir": str(s_dir),
        "phase": phase,
        "run_id": snapshot_data.get("run_id"),
        "created_at": snapshot_data.get("created_at"),
        "snapshot_exists": snapshot_exists,
        "snapshot_corrupt": snapshot_corrupt,
        "snapshot_error": snapshot_error,
        "counts": {
            "total": total_count,
            "active": active_count,
            "paused": paused_count,
            "disabled": disabled_count,
            "tool_paused": len(tool_paused_ids),
            "released": len(released_ids),
            "still_gated": max(len(tool_paused_ids) - len(released_ids), 0),
        },
        "tool_paused_ids": tool_paused_ids,
        "released_ids": released_ids,
        "items": items_to_report,
        "catchup": {
            "eligible_ids": catchup_eligible,
            "candidates_count": len(catchup_candidates),
            "candidates": catchup_candidates,
            "history_source": str(catchup_data.get("history_source") or ""),
            "created_at": catchup_data.get("created_at"),
        },
        "config": {
            "path": str(config_path),
            "exists": config_exists,
            "settings": settings.to_dict(),
            **({"error": config_error} if config_error else {}),
        },
        "live_error": live_error,
    }


def get_dashboard_html() -> str:
    """Return self-contained HTML dashboard with inline CSS and JavaScript."""
    return """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Safe Start for Codex — Web Dashboard</title>
  <style>
    :root {
      --bg: #0b1320;
      --card-bg: #111e33;
      --card-border: #1e3355;
      --header-bg: #070d17;
      --text: #e2e8f0;
      --text-muted: #94a3b8;
      --accent: #14b8a6;
      --accent-hover: #0d9488;
      --green: #22c55e;
      --yellow: #eab308;
      --blue: #3b82f6;
      --red: #ef4444;
      --purple: #a855f7;
    }
    * { box-sizing: border-box; margin: 0; padding: 0; }
    body {
      background: var(--bg);
      color: var(--text);
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
      line-height: 1.5;
      padding-bottom: 2rem;
    }
    header {
      background: var(--header-bg);
      border-bottom: 1px solid var(--card-border);
      padding: 1rem 1.5rem;
      display: flex;
      flex-wrap: wrap;
      justify-content: space-between;
      align-items: center;
      gap: 1rem;
    }
    .brand {
      display: flex;
      align-items: center;
      gap: 0.75rem;
    }
    .brand svg {
      width: 32px;
      height: 32px;
    }
    .brand h1 {
      font-size: 1.25rem;
      font-weight: 700;
      color: #fff;
      display: flex;
      align-items: center;
      gap: 0.5rem;
    }
    .badge-version {
      font-size: 0.75rem;
      background: var(--card-border);
      color: var(--accent);
      padding: 0.15rem 0.5rem;
      border-radius: 9999px;
    }
    .header-controls {
      display: flex;
      align-items: center;
      gap: 1rem;
    }
    .live-status {
      display: flex;
      align-items: center;
      gap: 0.4rem;
      font-size: 0.85rem;
      color: var(--text-muted);
    }
    .live-dot {
      width: 10px;
      height: 10px;
      border-radius: 50%;
      background: var(--green);
      animation: pulse 2s infinite;
    }
    @keyframes pulse {
      0% { opacity: 1; transform: scale(1); }
      50% { opacity: 0.4; transform: scale(0.9); }
      100% { opacity: 1; transform: scale(1); }
    }
    button.btn {
      background: var(--card-border);
      color: #fff;
      border: 1px solid var(--card-border);
      padding: 0.4rem 0.85rem;
      border-radius: 6px;
      cursor: pointer;
      font-size: 0.85rem;
      font-weight: 500;
      transition: background 0.15s ease;
    }
    button.btn:hover {
      background: var(--accent);
      border-color: var(--accent);
      color: #0b1320;
    }
    .container {
      max-width: 1300px;
      margin: 1.5rem auto;
      padding: 0 1rem;
    }
    .kpi-grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(210px, 1fr));
      gap: 1rem;
      margin-bottom: 1.5rem;
    }
    .card {
      background: var(--card-bg);
      border: 1px solid var(--card-border);
      border-radius: 8px;
      padding: 1rem 1.25rem;
    }
    .card-title {
      font-size: 0.75rem;
      text-transform: uppercase;
      letter-spacing: 0.05em;
      color: var(--text-muted);
      margin-bottom: 0.25rem;
    }
    .card-value {
      font-size: 1.75rem;
      font-weight: 700;
      color: #fff;
    }
    .card-subtext {
      font-size: 0.8rem;
      color: var(--text-muted);
      margin-top: 0.25rem;
    }
    .phase-badge {
      display: inline-block;
      padding: 0.25rem 0.6rem;
      border-radius: 6px;
      font-weight: 600;
      font-size: 0.85rem;
      text-transform: uppercase;
    }
    .phase-gated { background: rgba(59, 130, 246, 0.2); color: var(--blue); border: 1px solid var(--blue); }
    .phase-released { background: rgba(34, 197, 94, 0.2); color: var(--green); border: 1px solid var(--green); }
    .phase-restored { background: rgba(234, 179, 8, 0.2); color: var(--yellow); border: 1px solid var(--yellow); }
    .phase-idle { background: rgba(148, 163, 184, 0.2); color: var(--text-muted); border: 1px solid var(--text-muted); }

    .progress-section {
      margin-bottom: 1.5rem;
    }
    .progress-bar-bg {
      background: var(--card-border);
      height: 12px;
      border-radius: 6px;
      overflow: hidden;
      margin-top: 0.5rem;
    }
    .progress-bar-fill {
      background: linear-gradient(90deg, var(--accent), var(--green));
      height: 100%;
      width: 0%;
      transition: width 0.4s ease;
    }

    .tabs {
      display: flex;
      gap: 0.5rem;
      border-bottom: 1px solid var(--card-border);
      margin-bottom: 1rem;
    }
    .tab-btn {
      background: none;
      border: none;
      color: var(--text-muted);
      padding: 0.6rem 1rem;
      font-size: 0.9rem;
      font-weight: 600;
      cursor: pointer;
      border-bottom: 2px solid transparent;
      transition: color 0.15s, border-color 0.15s;
    }
    .tab-btn.active {
      color: var(--accent);
      border-bottom-color: var(--accent);
    }
    .tab-btn:hover {
      color: #fff;
    }
    .tab-content { display: none; }
    .tab-content.active { display: block; }

    .table-container {
      background: var(--card-bg);
      border: 1px solid var(--card-border);
      border-radius: 8px;
      overflow-x: auto;
    }
    table {
      width: 100%;
      border-collapse: collapse;
      text-align: left;
      font-size: 0.85rem;
    }
    th {
      background: rgba(0, 0, 0, 0.2);
      color: var(--text-muted);
      font-weight: 600;
      padding: 0.75rem 1rem;
      border-bottom: 1px solid var(--card-border);
    }
    td {
      padding: 0.75rem 1rem;
      border-bottom: 1px solid rgba(255, 255, 255, 0.05);
      color: var(--text);
    }
    tr:last-child td { border-bottom: none; }
    tr:hover td { background: rgba(255, 255, 255, 0.02); }

    .badge {
      display: inline-block;
      padding: 0.15rem 0.45rem;
      border-radius: 4px;
      font-size: 0.75rem;
      font-weight: 600;
    }
    .badge-active { background: rgba(34, 197, 94, 0.2); color: var(--green); }
    .badge-paused { background: rgba(234, 179, 8, 0.2); color: var(--yellow); }
    .badge-disabled { background: rgba(239, 68, 68, 0.2); color: var(--red); }
    .badge-tool { background: rgba(59, 130, 246, 0.2); color: var(--blue); }

    .filter-bar {
      display: flex;
      gap: 1rem;
      margin-bottom: 1rem;
    }
    .search-input {
      flex: 1;
      max-width: 400px;
      background: var(--card-bg);
      border: 1px solid var(--card-border);
      color: #fff;
      padding: 0.45rem 0.85rem;
      border-radius: 6px;
      font-size: 0.85rem;
    }
    .search-input:focus {
      outline: none;
      border-color: var(--accent);
    }

    .config-grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
      gap: 1rem;
    }
    .config-card {
      background: var(--card-bg);
      border: 1px solid var(--card-border);
      border-radius: 8px;
      padding: 1.25rem;
    }
    .config-row {
      display: flex;
      justify-content: space-between;
      padding: 0.4rem 0;
      border-bottom: 1px solid rgba(255, 255, 255, 0.05);
      font-size: 0.85rem;
    }
    .config-label { color: var(--text-muted); }
    .config-val { font-weight: 600; color: #fff; }
  </style>
</head>
<body>
  <header>
    <div class="brand">
      <svg viewBox="0 0 64 64" fill="none" xmlns="http://www.w3.org/2000/svg">
        <rect width="64" height="64" rx="14" fill="#0C2234"/>
        <path d="M32 9L50 17L46 44L32 55L18 44L14 17L32 9Z" fill="#1BA4B3"/>
        <rect x="23" y="21" width="5" height="21" rx="2" fill="#F5F8FA"/>
        <rect x="36" y="21" width="5" height="21" rx="2" fill="#F5F8FA"/>
        <path d="M45 22C48 26 49 32 46 38C44 42 40 46 34 47" stroke="#7DDC72" stroke-width="4" stroke-linecap="round"/>
      </svg>
      <div>
        <h1>Safe Start for Codex <span class="badge-version" id="appVersion">v1.1.6</span></h1>
      </div>
    </div>
    <div class="header-controls">
      <div class="live-status">
        <span class="live-dot"></span>
        <span id="liveStatusText">Live (127.0.0.1)</span>
      </div>
      <button class="btn" id="refreshBtn">Aktualisieren</button>
    </div>
  </header>

  <div class="container">
    <div class="kpi-grid">
      <div class="card">
        <div class="card-title">Gating Phase</div>
        <div class="card-value" id="valPhase">—</div>
        <div class="card-subtext" id="valRunId">Run: —</div>
      </div>
      <div class="card">
        <div class="card-title">Total Automations</div>
        <div class="card-value" id="valTotal">—</div>
        <div class="card-subtext" id="valActivePaused">— ACTIVE / — PAUSED</div>
      </div>
      <div class="card">
        <div class="card-title">Tool-Paused (Staged)</div>
        <div class="card-value" id="valToolPaused" style="color: var(--blue);">—</div>
        <div class="card-subtext">Zurückgehaltene Jobs</div>
      </div>
      <div class="card">
        <div class="card-title">Released (Gestartet)</div>
        <div class="card-value" id="valReleased" style="color: var(--green);">—</div>
        <div class="card-subtext" id="valRemaining">— verbleibend</div>
      </div>
      <div class="card">
        <div class="card-title">Catch-Up Kandidaten</div>
        <div class="card-value" id="valCatchup" style="color: var(--yellow);">—</div>
        <div class="card-subtext" id="valCatchupEligible">— sofortige Freigabe</div>
      </div>
    </div>

    <div class="card progress-section">
      <div style="display: flex; justify-content: space-between; align-items: center;">
        <div class="card-title" style="margin: 0;">Release Queue Fortschritt</div>
        <div id="progressText" style="font-size: 0.85rem; font-weight: 600; color: var(--accent);">0%</div>
      </div>
      <div class="progress-bar-bg">
        <div class="progress-bar-fill" id="progressBar"></div>
      </div>
    </div>

    <div class="tabs">
      <button class="tab-btn active" data-tab="tab-queue">Release Queue</button>
      <button class="tab-btn" data-tab="tab-automations">Alle Automatisierungen</button>
      <button class="tab-btn" data-tab="tab-catchup">Catch-Up Plan</button>
      <button class="tab-btn" data-tab="tab-config">Konfiguration</button>
    </div>

    <!-- Tab 1: Queue -->
    <div id="tab-queue" class="tab-content active">
      <div class="table-container">
        <table>
          <thead>
            <tr>
              <th>Status</th>
              <th>Automation ID</th>
              <th>Name</th>
              <th>Next Scheduled Run</th>
              <th>Gating Status</th>
            </tr>
          </thead>
          <tbody id="queueTableBody">
            <tr><td colspan="5" style="text-align: center; color: var(--text-muted);">Lade Daten...</td></tr>
          </tbody>
        </table>
      </div>
    </div>

    <!-- Tab 2: All Automations -->
    <div id="tab-automations" class="tab-content">
      <div class="filter-bar">
        <input type="text" id="filterInput" class="search-input" placeholder="Nach ID, Name oder Intervall filtern...">
      </div>
      <div class="table-container">
        <table>
          <thead>
            <tr>
              <th>Status</th>
              <th>ID</th>
              <th>Name</th>
              <th>Recurrence (RRULE)</th>
              <th>Nächste Fälligkeit</th>
            </tr>
          </thead>
          <tbody id="automationsTableBody">
            <tr><td colspan="5" style="text-align: center; color: var(--text-muted);">Lade Daten...</td></tr>
          </tbody>
        </table>
      </div>
    </div>

    <!-- Tab 3: Catch-Up -->
    <div id="tab-catchup" class="tab-content">
      <div class="table-container">
        <table>
          <thead>
            <tr>
              <th>Berechtigt</th>
              <th>ID</th>
              <th>Name</th>
              <th>Intervall</th>
              <th>Letzte Fälligkeit</th>
              <th>Letzte Ausführung</th>
              <th>Begründung</th>
            </tr>
          </thead>
          <tbody id="catchupTableBody">
            <tr><td colspan="7" style="text-align: center; color: var(--text-muted);">Kein Catch-Up-Bericht vorhanden.</td></tr>
          </tbody>
        </table>
      </div>
    </div>

    <!-- Tab 4: Config -->
    <div id="tab-config" class="tab-content">
      <div class="config-grid">
        <div class="config-card">
          <h3 style="font-size: 1rem; margin-bottom: 0.75rem; color: var(--accent);">Gating Parameter</h3>
          <div class="config-row"><span class="config-label">Initial Release</span><span class="config-val" id="cfgInitialRelease">—</span></div>
          <div class="config-row"><span class="config-label">Interval Minutes</span><span class="config-val" id="cfgIntervalMinutes">—</span></div>
          <div class="config-row"><span class="config-label">Startup Delay Seconds</span><span class="config-val" id="cfgStartupDelay">—</span></div>
          <div class="config-row"><span class="config-label">Min Future Lead Minutes</span><span class="config-val" id="cfgMinFutureLead">—</span></div>
          <div class="config-row"><span class="config-label">Auto Launch Codex</span><span class="config-val" id="cfgLaunch">—</span></div>
          <div class="config-row"><span class="config-label">Cleanup Blocker</span><span class="config-val" id="cfgCleanup">—</span></div>
        </div>
        <div class="config-card">
          <h3 style="font-size: 1rem; margin-bottom: 0.75rem; color: var(--accent);">Catch-Up Settings</h3>
          <div class="config-row"><span class="config-label">Catchup Enabled</span><span class="config-val" id="cfgCatchupEnabled">—</span></div>
          <div class="config-row"><span class="config-label">Lookback Days</span><span class="config-val" id="cfgCatchupLookback">—</span></div>
          <div class="config-row"><span class="config-label">Max Per Start</span><span class="config-val" id="cfgCatchupMax">—</span></div>
          <div class="config-row"><span class="config-label">Min Period Hours</span><span class="config-val" id="cfgCatchupMinPeriod">—</span></div>
        </div>
      </div>
    </div>
  </div>

  <script>
    let globalData = null;

    async function loadData() {
      try {
        const res = await fetch('/api/status');
        if (!res.ok) throw new Error('API returned status ' + res.status);
        globalData = await res.json();
        renderDashboard(globalData);
      } catch (err) {
        console.error('Failed to load dashboard data:', err);
        document.getElementById('liveStatusText').innerText = 'Verbindung fehlgeschlagen';
        document.querySelector('.live-dot').style.background = 'var(--red)';
      }
    }

    function renderDashboard(data) {
      document.getElementById('appVersion').innerText = 'v' + (data.version || '1.1.6');
      document.getElementById('liveStatusText').innerText = 'Live (' + (data.phase || 'idle') + ')';
      document.querySelector('.live-dot').style.background = 'var(--green)';

      // Phase
      const phaseEl = document.getElementById('valPhase');
      const phase = (data.phase || 'idle').toLowerCase();
      phaseEl.innerText = phase.toUpperCase();
      phaseEl.className = 'phase-badge phase-' + (phase === 'gated' ? 'gated' : phase === 'released' ? 'released' : phase === 'restored' ? 'restored' : 'idle');
      document.getElementById('valRunId').innerText = data.run_id ? 'Run: ' + data.run_id : 'Kein aktiver Lauf';

      // Counts
      const counts = data.counts || {};
      document.getElementById('valTotal').innerText = counts.total || 0;
      document.getElementById('valActivePaused').innerText = (counts.active || 0) + ' ACTIVE / ' + (counts.paused || 0) + ' PAUSED';
      document.getElementById('valToolPaused').innerText = counts.tool_paused || 0;
      document.getElementById('valReleased').innerText = counts.released || 0;
      document.getElementById('valRemaining').innerText = (counts.still_gated || 0) + ' verbleibend';

      // Progress
      const tp = counts.tool_paused || 0;
      const rel = counts.released || 0;
      const pct = tp > 0 ? Math.min(100, Math.round((rel / tp) * 100)) : (phase === 'released' ? 100 : 0);
      document.getElementById('progressBar').style.width = pct + '%';
      document.getElementById('progressText').innerText = pct + '% (' + rel + '/' + tp + ')';

      // Catch-up
      const catchup = data.catchup || {};
      document.getElementById('valCatchup').innerText = catchup.candidates_count || 0;
      document.getElementById('valCatchupEligible').innerText = (catchup.eligible_ids ? catchup.eligible_ids.length : 0) + ' sofortige Freigabe';

      // Tables
      renderQueueTable(data);
      renderAutomationsTable(data);
      renderCatchupTable(data);
      renderConfig(data);
    }

    function renderQueueTable(data) {
      const tbody = document.getElementById('queueTableBody');
      const items = data.items || [];
      const toolPausedSet = new Set(data.tool_paused_ids || []);
      const releasedSet = new Set(data.released_ids || []);

      const queueItems = items.filter(it => toolPausedSet.has(it.id));
      if (queueItems.length === 0) {
        tbody.innerHTML = '<tr><td colspan="5" style="text-align: center; color: var(--text-muted);">Aktuell sind keine Automatisierungen in der Release Queue gestaged.</td></tr>';
        return;
      }

      tbody.innerHTML = queueItems.map(it => {
        const isRel = releasedSet.has(it.id);
        const badge = isRel
          ? '<span class="badge badge-active">FREIGEGEBEN</span>'
          : '<span class="badge badge-tool">GESTAGED</span>';
        return `<tr>
          <td><span class="badge badge-paused">${it.status || 'PAUSED'}</span></td>
          <td><code>${escapeHtml(it.id)}</code></td>
          <td><strong>${escapeHtml(it.name || it.id)}</strong></td>
          <td>${it.next_at ? escapeHtml(it.next_at) : '<em style="color:var(--text-muted)">Unbekannt</em>'}</td>
          <td>${badge}</td>
        </tr>`;
      }).join('');
    }

    function renderAutomationsTable(data) {
      const tbody = document.getElementById('automationsTableBody');
      const items = data.items || [];
      const filter = (document.getElementById('filterInput').value || '').toLowerCase();

      const filtered = items.filter(it => {
        if (!filter) return true;
        const text = ((it.id || '') + ' ' + (it.name || '') + ' ' + (it.rrule || '') + ' ' + (it.status || '')).toLowerCase();
        return text.includes(filter);
      });

      if (filtered.length === 0) {
        tbody.innerHTML = '<tr><td colspan="5" style="text-align: center; color: var(--text-muted);">Keine passenden Automatisierungen gefunden.</td></tr>';
        return;
      }

      tbody.innerHTML = filtered.map(it => {
        const st = (it.status || 'UNKNOWN').toUpperCase();
        const badgeClass = st === 'ACTIVE' ? 'badge-active' : st === 'PAUSED' ? 'badge-paused' : 'badge-disabled';
        return `<tr>
          <td><span class="badge ${badgeClass}">${st}</span></td>
          <td><code>${escapeHtml(it.id)}</code></td>
          <td>${escapeHtml(it.name || it.id)}</td>
          <td><code>${escapeHtml(it.rrule || '—')}</code></td>
          <td>${it.next_at ? escapeHtml(it.next_at) : '<span style="color:var(--text-muted)">—</span>'}</td>
        </tr>`;
      }).join('');
    }

    function renderCatchupTable(data) {
      const tbody = document.getElementById('catchupTableBody');
      const candidates = (data.catchup && data.catchup.candidates) || [];

      if (candidates.length === 0) {
        tbody.innerHTML = '<tr><td colspan="7" style="text-align: center; color: var(--text-muted);">Keine verpassten seltenen Automatisierungen erkannt.</td></tr>';
        return;
      }

      tbody.innerHTML = candidates.map(c => {
        const eligBadge = c.eligible
          ? '<span class="badge badge-active">JA</span>'
          : '<span class="badge badge-paused">NEIN</span>';
        return `<tr>
          <td>${eligBadge}</td>
          <td><code>${escapeHtml(c.automation_id)}</code></td>
          <td>${escapeHtml(c.name || c.automation_id)}</td>
          <td>${c.period_hours ? c.period_hours + 'h' : '—'}</td>
          <td>${c.last_due_at ? escapeHtml(c.last_due_at) : '—'}</td>
          <td>${c.last_observed_at ? escapeHtml(c.last_observed_at) : '<em style="color:var(--text-muted)">keine</em>'}</td>
          <td>${escapeHtml(c.reason || '—')}</td>
        </tr>`;
      }).join('');
    }

    function renderConfig(data) {
      const cfg = (data.config && data.config.settings) || {};
      document.getElementById('cfgInitialRelease').innerText = cfg.initial_release ?? '3';
      document.getElementById('cfgIntervalMinutes').innerText = (cfg.interval_minutes ?? '5') + ' min';
      document.getElementById('cfgStartupDelay').innerText = (cfg.startup_delay_seconds ?? '45') + ' s';
      document.getElementById('cfgMinFutureLead').innerText = (cfg.min_future_lead_minutes ?? '2') + ' min';
      document.getElementById('cfgLaunch').innerText = cfg.launch ? 'Ja' : 'Nein';
      document.getElementById('cfgCleanup').innerText = cfg.cleanup ? 'Ja' : 'Nein';
      document.getElementById('cfgCatchupEnabled').innerText = cfg.catchup_enabled ? 'Aktiviert' : 'Deaktiviert';
      document.getElementById('cfgCatchupLookback').innerText = (cfg.catchup_lookback_days ?? '30') + ' Tage';
      document.getElementById('cfgCatchupMax').innerText = cfg.catchup_max_per_start ?? '1';
      document.getElementById('cfgCatchupMinPeriod').innerText = (cfg.catchup_min_period_hours ?? '24') + ' h';
    }

    function escapeHtml(str) {
      if (!str) return '';
      return String(str)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#039;');
    }

    // Tabs
    document.querySelectorAll('.tab-btn').forEach(btn => {
      btn.addEventListener('click', () => {
        document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
        document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
        btn.classList.add('active');
        const target = btn.getAttribute('data-tab');
        document.getElementById(target).classList.add('active');
      });
    });

    document.getElementById('filterInput').addEventListener('input', () => {
      if (globalData) renderAutomationsTable(globalData);
    });

    document.getElementById('refreshBtn').addEventListener('click', loadData);

    // Initial load and periodic poll
    loadData();
    setInterval(loadData, 3000);
  </script>
</body>
</html>
"""


class DashboardRequestHandler(http.server.BaseHTTPRequestHandler):
    """Hermetic, localhost-only HTTP request handler for dashboard API & UI."""

    server: "DashboardServer"

    def log_message(self, format: str, *args: Any) -> None:
        """Suppress default HTTP request logging to stderr."""
        return

    def _send_security_headers(self, content_type: str, status_code: int = 200) -> None:
        self.send_response(status_code)
        self.send_header("Content-Type", content_type)
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("X-Frame-Options", "DENY")
        self.send_header("Cache-Control", "no-cache, no-store, must-revalidate")
        self.send_header(
            "Content-Security-Policy",
            "default-src 'self' 'unsafe-inline' data:; frame-ancestors 'none';",
        )
        self.end_headers()

    def _normalize_path(self) -> str:
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path.strip()
        if path != "/" and path.endswith("/"):
            path = path.rstrip("/")
        return path

    def _state_dir(self) -> Path | None:
        return getattr(self.server, "state_dir_path", None)

    def do_HEAD(self) -> None:
        path = self._normalize_path()
        if path in ("/", "/index.html", "/index.htm"):
            self._send_security_headers("text/html; charset=utf-8")
        elif path in ("/api/status", "/api/queue", "/api/automations", "/api/catchup", "/api/config"):
            self._send_security_headers("application/json; charset=utf-8")
        elif path == "/favicon.ico":
            self._send_security_headers("image/svg+xml")
        else:
            self._send_security_headers("application/json; charset=utf-8", 404)

    def do_GET(self) -> None:
        path = self._normalize_path()
        state_dir = self._state_dir()

        if path in ("/", "/index.html", "/index.htm"):
            body = get_dashboard_html().encode("utf-8")
            self._send_security_headers("text/html; charset=utf-8")
            try:
                self.wfile.write(body)
            except (ConnectionError, BrokenPipeError, OSError):
                pass
            return

        if path == "/api/status":
            data = get_dashboard_data(state_dir)
            body = json.dumps(data, ensure_ascii=False, indent=2).encode("utf-8")
            self._send_security_headers("application/json; charset=utf-8")
            try:
                self.wfile.write(body)
            except (ConnectionError, BrokenPipeError, OSError):
                pass
            return

        if path == "/api/queue":
            data = get_dashboard_data(state_dir)
            tool_paused_ids = data.get("tool_paused_ids")
            tool_paused_list = list(tool_paused_ids) if isinstance(tool_paused_ids, list) else []
            tool_paused_set = set(tool_paused_list)
            raw_items = data.get("items")
            items_list = raw_items if isinstance(raw_items, list) else []
            queue_payload = {
                "phase": data.get("phase"),
                "run_id": data.get("run_id"),
                "counts": data.get("counts") if isinstance(data.get("counts"), dict) else {},
                "tool_paused_ids": tool_paused_list,
                "released_ids": data.get("released_ids") if isinstance(data.get("released_ids"), list) else [],
                "items": [
                    it for it in items_list
                    if isinstance(it, dict) and it.get("id") in tool_paused_set
                ],
            }
            body = json.dumps(queue_payload, ensure_ascii=False, indent=2).encode("utf-8")
            self._send_security_headers("application/json; charset=utf-8")
            try:
                self.wfile.write(body)
            except (ConnectionError, BrokenPipeError, OSError):
                pass
            return

        if path == "/api/automations":
            data = get_dashboard_data(state_dir)
            counts = data.get("counts")
            total = counts.get("total", 0) if isinstance(counts, dict) else 0
            raw_items = data.get("items")
            items_list = raw_items if isinstance(raw_items, list) else []
            automations_payload = {
                "total": total,
                "items": items_list,
            }
            body = json.dumps(automations_payload, ensure_ascii=False, indent=2).encode("utf-8")
            self._send_security_headers("application/json; charset=utf-8")
            try:
                self.wfile.write(body)
            except (ConnectionError, BrokenPipeError, OSError):
                pass
            return

        if path == "/api/catchup":
            data = get_dashboard_data(state_dir)
            catchup_payload = data.get("catchup") if isinstance(data.get("catchup"), dict) else {}
            body = json.dumps(catchup_payload, ensure_ascii=False, indent=2).encode("utf-8")
            self._send_security_headers("application/json; charset=utf-8")
            try:
                self.wfile.write(body)
            except (ConnectionError, BrokenPipeError, OSError):
                pass
            return

        if path == "/api/config":
            data = get_dashboard_data(state_dir)
            config_payload = data.get("config") if isinstance(data.get("config"), dict) else {}
            body = json.dumps(config_payload, ensure_ascii=False, indent=2).encode("utf-8")
            self._send_security_headers("application/json; charset=utf-8")
            try:
                self.wfile.write(body)
            except (ConnectionError, BrokenPipeError, OSError):
                pass
            return

        if path == "/favicon.ico":
            svg = (
                '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 32 32">'
                '<rect width="32" height="32" rx="8" fill="#0C2234"/>'
                '<circle cx="16" cy="16" r="8" fill="#1BA4B3"/>'
                '</svg>'
            ).encode("utf-8")
            self._send_security_headers("image/svg+xml")
            try:
                self.wfile.write(svg)
            except (ConnectionError, BrokenPipeError, OSError):
                pass
            return

        # 404 Fallback
        self._send_security_headers("application/json; charset=utf-8", 404)
        try:
            self.wfile.write(b'{"error": "Not Found", "status": 404}')
        except (ConnectionError, BrokenPipeError, OSError):
            pass


class DashboardServer(http.server.ThreadingHTTPServer):
    """Threading HTTP server carrying optional state directory configuration."""

    def __init__(
        self,
        server_address: tuple[str, int],
        RequestHandlerClass: type[http.server.BaseHTTPRequestHandler],
        state_dir_path: Path | None = None,
    ) -> None:
        super().__init__(server_address, RequestHandlerClass)
        self.state_dir_path = state_dir_path


def create_dashboard_server(
    host: str = "127.0.0.1",
    port: int = 8765,
    state_dir_path: Path | None = None,
) -> DashboardServer:
    """Instantiate a configured DashboardServer bound to host and port."""
    return DashboardServer((host, port), DashboardRequestHandler, state_dir_path=state_dir_path)


def run_dashboard(
    host: str = "127.0.0.1",
    port: int = 8765,
    open_browser: bool = False,
    stop_event: threading.Event | None = None,
    state_dir_path: Path | None = None,
) -> int:
    """Launch dashboard HTTP server and block until interrupted or stop_event is set."""
    server = create_dashboard_server(host=host, port=port, state_dir_path=state_dir_path)
    actual_port = server.server_port
    url = f"http://{host}:{actual_port}/"

    print(f"[safe-start-dashboard] Web dashboard live at: {url}")
    print("[safe-start-dashboard] Press Ctrl+C to stop.")

    if open_browser:
        try:
            webbrowser.open(url)
        except Exception:
            pass

    if stop_event is not None:
        def poll_stop() -> None:
            stop_event.wait()
            server.shutdown()
        threading.Thread(target=poll_stop, daemon=True, name="dashboard-stop-monitor").start()

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n[safe-start-dashboard] Stopped dashboard server.")
    finally:
        server.server_close()

    return 0
