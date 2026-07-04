"""Command line entrypoint for Safe Start for Codex."""

from __future__ import annotations

import argparse
import contextlib
import json
import os
import re
import shutil
import sqlite3
import subprocess
import sys
import threading
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime, time as day_time, timedelta
from pathlib import Path
from typing import Callable, Iterable


CREATE_NO_WINDOW = 0x08000000
CODEX_STORE_AUMID = "OpenAI.Codex_2p2nqsd0c76g0!App"
CODEX_STORE_MARKER = r"\WindowsApps\OpenAI.Codex"
DEFAULT_INITIAL_RELEASE = 3
DEFAULT_INTERVAL_MINUTES = 5
DEFAULT_STARTUP_DELAY_SECONDS = 45
DEFAULT_MIN_FUTURE_LEAD_MINUTES = 2
CONFIG_FILE_NAME = "config.json"

DAY_MAP = {
    "MO": 0,
    "TU": 1,
    "WE": 2,
    "TH": 3,
    "FR": 4,
    "SA": 5,
    "SU": 6,
}


def no_window_kwargs() -> dict[str, object]:
    if os.name == "nt":
        return {"creationflags": CREATE_NO_WINDOW}
    return {}


def local_now() -> datetime:
    return datetime.now().astimezone()


def timestamp_ms() -> int:
    return int(time.time() * 1000)


def codex_home() -> Path:
    return Path(os.environ.get("CODEX_HOME") or Path.home() / ".codex")


def state_dir() -> Path:
    path = codex_home() / "automation-safe-start"
    path.mkdir(parents=True, exist_ok=True)
    return path


def default_config_path() -> Path:
    return codex_home() / "automation-safe-start" / CONFIG_FILE_NAME


def automations_dir() -> Path:
    return codex_home() / "automations"


def codex_state_db_path() -> Path:
    return codex_home() / "state_5.sqlite"


def codex_user_data_dir() -> Path:
    appdata = Path(os.environ.get("APPDATA") or Path.home() / "AppData" / "Roaming")
    return appdata / "Codex"


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def _atomic_write_text(path: Path, text: str, *, newline: str | None = None) -> None:
    # Bugsweep 20 BUG-A03: atomar schreiben (tmp + os.replace), sonst bleibt bei einem Absturz
    # mitten im write_text eine korrupte Datei zurueck — latest.json / automation.toml werden
    # von der Tray-App bzw. dem naechsten Lauf gelesen.
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(text, encoding="utf-8", newline=newline)
    os.replace(tmp, path)


def quoted_value(text: str, key: str) -> str:
    match = re.search(rf'^{re.escape(key)}\s*=\s*"(.*?)"\s*$', text, re.MULTILINE)
    return match.group(1) if match else ""


def int_value(text: str, key: str) -> int | None:
    match = re.search(rf"^{re.escape(key)}\s*=\s*(\d+)\s*$", text, re.MULTILINE)
    return int(match.group(1)) if match else None


@dataclass
class Automation:
    id: str
    name: str
    path: str
    original_status: str
    status: str
    kind: str
    rrule: str
    created_at: int | None
    updated_at: int | None
    next_at: str | None = None
    tool_paused: bool = False
    released: bool = False


@dataclass(frozen=True, slots=True)
class ProcessInfo:
    pid: int
    name: str
    executable: str = ""
    command_line: str = ""
    parent_pid: int = 0
    created_at: str = ""


@dataclass(slots=True)
class CleanupResult:
    renderer_present: bool = False
    zombie_pids: list[int] = field(default_factory=list)
    stale_lockfile: bool = False
    companion_orphan_pids: list[int] = field(default_factory=list)
    killed_pids: list[int] = field(default_factory=list)
    removed_lockfile: bool = False
    dry_run: bool = True
    messages: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class GateSettings:
    initial_release: int = DEFAULT_INITIAL_RELEASE
    interval_minutes: int = DEFAULT_INTERVAL_MINUTES
    startup_delay_seconds: int = DEFAULT_STARTUP_DELAY_SECONDS
    min_future_lead_minutes: int = DEFAULT_MIN_FUTURE_LEAD_MINUTES
    launch: bool = True
    cleanup: bool = True
    catchup_enabled: bool = False
    catchup_lookback_days: int = 30
    catchup_max_per_start: int = 1
    catchup_min_period_hours: int = 24

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


GATE_CONFIG_FIELDS = frozenset(GateSettings.__dataclass_fields__)


def _require_int_config(value: object, key: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise SystemExit(f"Config value '{key}' must be an integer.")
    if value < 0:
        raise SystemExit(f"Config value '{key}' must be greater than or equal to 0.")
    return value


def _require_bool_config(value: object, key: str) -> bool:
    if not isinstance(value, bool):
        raise SystemExit(f"Config value '{key}' must be true or false.")
    return value


def read_gate_config(path: Path | None = None) -> tuple[GateSettings, Path, bool]:
    config_path = path or default_config_path()
    settings = GateSettings()
    if not config_path.exists():
        return settings, config_path, False

    try:
        raw = json.loads(config_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise SystemExit(f"Could not parse config JSON at {config_path}: {exc}") from exc

    if not isinstance(raw, dict):
        raise SystemExit(f"Config file must contain a JSON object: {config_path}")

    unknown = sorted(set(raw) - GATE_CONFIG_FIELDS)
    if unknown:
        valid = ", ".join(sorted(GATE_CONFIG_FIELDS))
        raise SystemExit(f"Unknown config key(s): {', '.join(unknown)}. Valid keys: {valid}")

    values = settings.to_dict()
    for key, value in raw.items():
        if key in {"launch", "cleanup", "catchup_enabled"}:
            values[key] = _require_bool_config(value, key)
        else:
            values[key] = _require_int_config(value, key)
    return GateSettings(**values), config_path, True


def resolve_gate_settings(args: argparse.Namespace) -> tuple[GateSettings, Path, bool]:
    settings, config_path, exists = read_gate_config(getattr(args, "config", None))
    values = settings.to_dict()
    for key in sorted(GATE_CONFIG_FIELDS):
        override = getattr(args, key, None)
        if override is not None:
            if key in {"launch", "cleanup", "catchup_enabled"}:
                values[key] = _require_bool_config(override, key)
            else:
                values[key] = _require_int_config(override, key)
    return GateSettings(**values), config_path, exists


def write_default_config(path: Path, *, force: bool = False) -> None:
    if path.exists() and not force:
        raise SystemExit(f"Config already exists: {path}. Use --force to overwrite it.")
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(GateSettings().to_dict(), ensure_ascii=False, indent=2)
    _atomic_write_text(path, payload + "\n")


@dataclass(frozen=True, slots=True)
class ObservedRun:
    automation_id: str
    thread_id: str
    created_at: str
    title: str
    confidence: str = "thread-title"

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(slots=True)
class CatchupCandidate:
    automation_id: str
    name: str
    status: str
    rrule: str
    period_hours: float | None
    last_due_at: str | None
    next_due_at: str | None
    last_observed_at: str | None
    missed: bool
    eligible: bool
    reason: str
    confidence: str

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(slots=True)
class CatchupReport:
    created_at: str
    lookback_days: int
    min_period_hours: int
    max_per_start: int
    history_source: str
    candidates: list[CatchupCandidate]
    eligible_ids: list[str]
    notes: list[str]

    def to_dict(self) -> dict[str, object]:
        return {
            "created_at": self.created_at,
            "lookback_days": self.lookback_days,
            "min_period_hours": self.min_period_hours,
            "max_per_start": self.max_per_start,
            "history_source": self.history_source,
            "eligible_ids": self.eligible_ids,
            "notes": self.notes,
            "candidates": [candidate.to_dict() for candidate in self.candidates],
        }


def load_automations() -> list[Automation]:
    root = automations_dir()
    result: list[Automation] = []
    if not root.exists():
        raise SystemExit(f"Automations directory not found: {root}")

    for toml in sorted(root.glob("*/automation.toml")):
        text = read_text(toml)
        automation_id = quoted_value(text, "id") or toml.parent.name
        status = quoted_value(text, "status") or "UNKNOWN"
        result.append(
            Automation(
                id=automation_id,
                name=quoted_value(text, "name") or automation_id,
                path=str(toml),
                original_status=status,
                status=status,
                kind=quoted_value(text, "kind"),
                rrule=quoted_value(text, "rrule"),
                created_at=int_value(text, "created_at"),
                updated_at=int_value(text, "updated_at"),
            )
        )
    return result


def set_status(path: Path, status: str) -> bool:
    text = read_text(path)
    current = quoted_value(text, "status")
    if current == status:
        return False

    if re.search(r'^status\s*=\s*".*?"\s*$', text, re.MULTILINE):
        text = re.sub(
            r'^status\s*=\s*".*?"\s*$',
            f'status = "{status}"',
            text,
            count=1,
            flags=re.MULTILINE,
        )
    else:
        text += f'\nstatus = "{status}"\n'

    if re.search(r"^updated_at\s*=\s*\d+\s*$", text, re.MULTILINE):
        text = re.sub(
            r"^updated_at\s*=\s*\d+\s*$",
            f"updated_at = {timestamp_ms()}",
            text,
            count=1,
            flags=re.MULTILINE,
        )
    _atomic_write_text(path, text, newline="")
    return True


def write_snapshot(
    run_id: str,
    items: Iterable[Automation],
    phase: str,
    **meta: object,
) -> Path:
    rows = [asdict(item) for item in items]
    data = {
        "run_id": run_id,
        "phase": phase,
        "created_at": local_now().isoformat(timespec="seconds"),
        "codex_home": str(codex_home()),
        "tool_paused_ids": [row["id"] for row in rows if row.get("tool_paused")],
        "released_ids": [row["id"] for row in rows if row.get("released")],
        "items": rows,
        **meta,
    }
    path = state_dir() / f"{run_id}-{phase}.json"
    payload = json.dumps(data, ensure_ascii=False, indent=2)
    _atomic_write_text(path, payload)
    _atomic_write_text(state_dir() / "latest.json", payload)
    return path


def append_log(run_id: str, event: str, **payload: object) -> None:
    record = {
        "ts": local_now().isoformat(timespec="seconds"),
        "run_id": run_id,
        "event": event,
        **payload,
    }
    with (state_dir() / "events.jsonl").open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, ensure_ascii=False) + "\n")


def _as_process_list(raw: object) -> list[dict[str, object]]:
    if raw is None:
        return []
    if isinstance(raw, list):
        return [item for item in raw if isinstance(item, dict)]
    if isinstance(raw, dict):
        return [raw]
    return []


def windows_processes() -> list[ProcessInfo]:
    if os.name != "nt":
        return []
    command = [
        "powershell",
        "-NoProfile",
        "-ExecutionPolicy",
        "Bypass",
        "-Command",
        (
            "[Console]::OutputEncoding=[System.Text.Encoding]::UTF8; "
            "Get-CimInstance Win32_Process | "
            "Select-Object ProcessId,ParentProcessId,Name,ExecutablePath,CommandLine,"
            "@{N='CreationDate';E={ if ($_.CreationDate) { $_.CreationDate.ToString('s') } else { '' } }} | "
            "ConvertTo-Json -Compress"
        ),
    ]
    try:
        completed = subprocess.run(
            command,
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=30,
            **no_window_kwargs(),
        )
    except (subprocess.TimeoutExpired, OSError) as exc:
        # Bugsweep 20 BUG-A01: WMI/PowerShell kann haengen -> ohne timeout blockierte das
        # Tool dauerhaft. BUG-A02: Fehler sichtbar machen, sonst meldet cleanup faelschlich
        # "keine Prozesse" (stilles [] wirkt wie "sauber"), obwohl der Abruf scheiterte.
        print(f"[safe-start] windows_processes fehlgeschlagen: {exc}", file=sys.stderr)
        return []
    if completed.returncode != 0:
        print(
            f"[safe-start] windows_processes returncode={completed.returncode}: "
            f"{(completed.stderr or '').strip()[:200]}",
            file=sys.stderr,
        )
        return []
    if not completed.stdout.strip():
        return []

    try:
        rows = _as_process_list(json.loads(completed.stdout))
    except json.JSONDecodeError as exc:
        print(f"[safe-start] windows_processes JSON-Parse-Fehler: {exc}", file=sys.stderr)
        return []

    processes: list[ProcessInfo] = []
    for row in rows:
        try:
            pid = int(row.get("ProcessId") or 0)
            parent_pid = int(row.get("ParentProcessId") or 0)
        except (TypeError, ValueError):
            continue
        if not pid:
            continue
        processes.append(
            ProcessInfo(
                pid=pid,
                name=str(row.get("Name") or ""),
                executable=str(row.get("ExecutablePath") or ""),
                command_line=str(row.get("CommandLine") or ""),
                parent_pid=parent_pid,
                created_at=str(row.get("CreationDate") or ""),
            )
        )
    return processes


def _normalise_path(path: str) -> str:
    return path.replace("/", "\\").strip().strip('"').lower()


def find_codex_exe() -> Path | None:
    local_appdata = os.environ.get("LOCALAPPDATA")
    if local_appdata:
        candidate = Path(local_appdata) / "Programs" / "Codex" / "Codex.exe"
        if candidate.exists():
            return candidate
    return None


def matches_codex_executable(process: ProcessInfo) -> bool:
    exe_path = find_codex_exe()
    target = _normalise_path(str(exe_path or ""))
    executable = _normalise_path(process.executable)
    if target and executable == target:
        return True

    marker = _normalise_path(CODEX_STORE_MARKER)
    if marker and marker in executable and executable.endswith("\\codex.exe"):
        return True

    command_line = _normalise_path(process.command_line)
    if target and (command_line == target or command_line.startswith(target + " ")):
        return True
    return bool(marker and marker in command_line and "codex.exe" in command_line)


def find_codex_processes_by_executable(processes: Iterable[ProcessInfo]) -> list[ProcessInfo]:
    own_pid = os.getpid()
    return sorted(
        [process for process in processes if process.pid != own_pid and matches_codex_executable(process)],
        key=lambda item: item.pid,
    )


TYPE_PATTERN = re.compile(r"--type=([a-z0-9-]+)")


def process_type(process: ProcessInfo) -> str:
    match = TYPE_PATTERN.search(process.command_line)
    return match.group(1) if match else "main"


def build_children_map(processes: Iterable[ProcessInfo]) -> dict[int, list[int]]:
    children: dict[int, list[int]] = {}
    for process in processes:
        children.setdefault(process.parent_pid, []).append(process.pid)
    return children


def descendant_pids(root_pid: int, processes: Iterable[ProcessInfo]) -> set[int]:
    children = build_children_map(processes)
    result: set[int] = set()
    stack = list(children.get(root_pid, []))
    while stack:
        pid = stack.pop()
        if pid in result or pid == root_pid:
            continue
        result.add(pid)
        stack.extend(children.get(pid, []))
    return result


def tree_pids(root_pid: int, processes: Iterable[ProcessInfo]) -> set[int]:
    return {root_pid} | descendant_pids(root_pid, processes)


def process_age_seconds(created_at: str) -> float:
    if not created_at:
        return float("inf")
    try:
        return (datetime.now() - datetime.fromisoformat(created_at)).total_seconds()
    except (ValueError, TypeError):
        # Bugsweep 20 BUG-A04: TypeError moeglich (created_at kein str, oder naive/aware-Mix
        # bei Offset im Timestamp) -> defensiv als "uralt" behandeln.
        return float("inf")


NPM_CODEX_MARKER = r"\npm\node_modules\@openai\codex"
EMBEDDED_CODEX_MARKER = r"\appdata\local\openai\codex\bin"


def is_companion_orphan(process: ProcessInfo, *, min_age_seconds: int = 300) -> bool:
    command_line = process.command_line.lower()
    executable = (process.executable or "").lower()
    full = f"{executable} {command_line}"

    if "app-server" not in command_line:
        return False
    if "--analytics-default-enabled" in command_line:
        return False

    is_npm = NPM_CODEX_MARKER.lower() in full
    is_embedded = EMBEDDED_CODEX_MARKER.lower() in full and "--listen stdio://" in command_line
    if not (is_npm or is_embedded):
        return False

    return process_age_seconds(process.created_at) >= min_age_seconds


def kill_process_tree(pid: int) -> tuple[bool, str]:
    # BUGSWEEP-20 REVIEW-NOTIZ (L-01/L-02, NICHT auto-gefixt — User-Entscheidung):
    #  L-01 Self-Kill: `/T` killt den GESAMTEN Prozessbaum. Liefe safe-start jemals selbst als
    #   Kind/Enkel eines Codex-Mains, koennte es sich mit-killen (der own_pid-Ausschluss in
    #   find_codex_processes_by_executable schuetzt nur den Listeneintrag, nicht den /T-Descendant).
    #  L-02 PID-Recycling-Race: zwischen windows_processes()-Snapshot und kill_process_tree(pid)
    #   kann Windows die PID recyceln -> theoretisch falscher Kill. Niedriges Risiko (einmaliger
    #   Startup-Lauf), Fix waere Re-Verify des Executable vor dem Kill. Bewusst belassen.
    # Bugsweep 20 BUG-A01: taskkill kann in seltenen Systemzustaenden blockieren -> timeout.
    try:
        completed = subprocess.run(
            ["taskkill", "/PID", str(pid), "/T", "/F"],
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=15,
            **no_window_kwargs(),
        )
    except (subprocess.TimeoutExpired, OSError) as exc:
        return False, f"taskkill fehlgeschlagen/timeout: {exc}"
    output = (completed.stdout or "").strip() or (completed.stderr or "").strip()
    return completed.returncode == 0, output


def cleanup_start_blockers(
    *,
    execute: bool,
    run_id: str,
    zombie_min_age_seconds: int = 120,
    companion_min_age_seconds: int = 300,
) -> CleanupResult:
    all_processes = windows_processes()
    codex_processes = find_codex_processes_by_executable(all_processes)
    codex_by_pid = {process.pid: process for process in codex_processes}
    mains = [process for process in codex_processes if process_type(process) == "main"]
    renderer_present = any(process_type(process) == "renderer" for process in codex_processes)

    zombie_pids: list[int] = []
    # BUGSWEEP-20 REVIEW-NOTIZ (L-03, NICHT auto-gefixt — User-Entscheidung): der renderer_present-
    # Check ist GLOBAL ueber alle Codex-Prozesse. Solange IRGENDeine Instanz einen Renderer hat,
    # wird die Zombie-Main-Erkennung komplett uebersprungen — auch fuer voellig separate, tote Mains.
    # Wirkt konservativ (lieber nichts killen), ist aber evtl. unvollstaendig. Semantik bewusst belassen.
    if not renderer_present:
        for main in mains:
            subtree = tree_pids(main.pid, all_processes)
            has_renderer = any(
                pid in codex_by_pid and process_type(codex_by_pid[pid]) == "renderer"
                for pid in subtree
            )
            if not has_renderer and process_age_seconds(main.created_at) >= zombie_min_age_seconds:
                zombie_pids.append(main.pid)

    lockfile = codex_user_data_dir() / "lockfile"
    stale_lockfile = lockfile.exists() and not mains
    companion_orphans = [
        process
        for process in all_processes
        if is_companion_orphan(process, min_age_seconds=companion_min_age_seconds)
    ]

    result = CleanupResult(
        renderer_present=renderer_present,
        zombie_pids=sorted(zombie_pids),
        stale_lockfile=stale_lockfile,
        companion_orphan_pids=sorted(process.pid for process in companion_orphans),
        dry_run=not execute,
    )
    append_log(run_id, "startup_cleanup_scan", **result.to_dict())

    if os.name != "nt":
        result.messages.append("Startup cleanup is only active on Windows.")
        return result

    if renderer_present:
        result.messages.append("Codex renderer is active; no main process was terminated.")

    for pid in result.zombie_pids:
        if not execute:
            result.messages.append(f"Would terminate stale Codex main process: PID {pid}")
            continue
        ok, message = kill_process_tree(pid)
        append_log(run_id, "startup_cleanup_kill_zombie", pid=pid, ok=ok, message=message)
        if ok:
            result.killed_pids.append(pid)
            result.messages.append(f"Terminated stale Codex main process: PID {pid}")
        else:
            result.messages.append(f"Could not terminate Codex main process PID {pid}: {message}")

    no_live_mains = set(process.pid for process in mains) <= set(result.zombie_pids)
    lockfile_stale_after_kill = (
        lockfile.exists()
        and (stale_lockfile or (execute and result.killed_pids and no_live_mains))
    )
    if lockfile_stale_after_kill:
        if not execute:
            result.messages.append(f"Would remove stale lockfile: {lockfile}")
        else:
            try:
                lockfile.unlink()
                result.removed_lockfile = True
                result.messages.append(f"Removed stale lockfile: {lockfile}")
                append_log(run_id, "startup_cleanup_lockfile_removed", path=str(lockfile))
            except OSError as exc:
                result.messages.append(f"Could not remove lockfile: {exc}")
                append_log(run_id, "startup_cleanup_lockfile_failed", path=str(lockfile), error=str(exc))

    for orphan in companion_orphans:
        if not execute:
            result.messages.append(f"Would terminate orphaned Codex companion: PID {orphan.pid}")
            continue
        ok, message = kill_process_tree(orphan.pid)
        append_log(
            run_id,
            "startup_cleanup_kill_companion_orphan",
            pid=orphan.pid,
            ok=ok,
            message=message,
        )
        if ok:
            result.killed_pids.append(orphan.pid)
            result.messages.append(f"Terminated orphaned Codex companion: PID {orphan.pid}")
        else:
            result.messages.append(f"Could not terminate companion PID {orphan.pid}: {message}")

    if not result.messages:
        result.messages.append("No startup-blocking Codex leftovers found.")
    return result


def parse_rrule(rrule: str) -> dict[str, list[str] | str | int]:
    value = rrule.removeprefix("RRULE:")
    parts: dict[str, list[str] | str | int] = {}
    for chunk in value.split(";"):
        if "=" not in chunk:
            continue
        key, raw = chunk.split("=", 1)
        key = key.upper()
        if key == "INTERVAL":
            try:
                parts[key] = int(raw)
            except ValueError:
                parts[key] = 1
        elif "," in raw:
            parts[key] = [item.strip().upper() for item in raw.split(",") if item.strip()]
        else:
            parts[key] = raw.strip().upper()
    return parts


def values_as_ints(parts: dict[str, list[str] | str | int], key: str, default: list[int]) -> list[int]:
    raw = parts.get(key)
    if raw is None:
        return default
    values = raw if isinstance(raw, list) else [raw]
    result: list[int] = []
    for item in values:
        try:
            result.append(int(str(item)))
        except ValueError:
            continue
    return result or default


def allowed_days(parts: dict[str, list[str] | str | int]) -> set[int]:
    raw = parts.get("BYDAY")
    if raw is None:
        return set(range(7))
    values = raw if isinstance(raw, list) else [raw]
    days = {DAY_MAP[token] for token in (_normalise_day_token(item) for item in values) if token in DAY_MAP}
    return days or set(range(7))


def rrule_next_after(rrule: str, after: datetime) -> datetime | None:
    if not rrule:
        return None
    parts = parse_rrule(rrule)
    frequency = str(parts.get("FREQ") or "").upper()
    interval = max(1, int(parts.get("INTERVAL") or 1))
    minutes = values_as_ints(parts, "BYMINUTE", [0])
    hours = values_as_ints(parts, "BYHOUR", list(range(24)))
    days = allowed_days(parts)

    if frequency == "HOURLY" and (interval > 24 or 24 % interval != 0):
        step = timedelta(hours=interval)
        target_minute = sorted(minutes)[0] if minutes else 0
        candidate = after.replace(second=0, microsecond=0) + step
        candidate = candidate.replace(minute=target_minute, second=0, microsecond=0)
        if candidate <= after:
            candidate += timedelta(hours=1)
        deadline = after + timedelta(days=14)
        while candidate <= deadline:
            if candidate.weekday() in days and candidate.hour in hours:
                return candidate
            candidate += step
        return None

    cursor = after.replace(second=0, microsecond=0) + timedelta(minutes=1)
    deadline = after + timedelta(days=14)
    while cursor <= deadline:
        if cursor.weekday() not in days or cursor.minute not in minutes:
            cursor += timedelta(minutes=1)
            continue
        if frequency in {"DAILY", "WEEKLY"} and cursor.hour in hours:
            return cursor
        if frequency == "HOURLY" and cursor.hour in hours and cursor.hour % max(interval, 1) == 0:
            return cursor
        if frequency not in {"DAILY", "WEEKLY", "HOURLY"} and cursor.hour in hours:
            return cursor
        cursor += timedelta(minutes=1)
    return None


def _normalise_day_token(value: object) -> str:
    match = re.search(r"([A-Z]{2})$", str(value).strip().upper())
    return match.group(1) if match else ""


def _raw_values(parts: dict[str, list[str] | str | int], key: str) -> list[object]:
    raw = parts.get(key)
    if raw is None:
        return []
    return raw if isinstance(raw, list) else [raw]


def _byday_count(parts: dict[str, list[str] | str | int]) -> int:
    days = {
        token
        for token in (_normalise_day_token(item) for item in _raw_values(parts, "BYDAY"))
        if token in DAY_MAP
    }
    return len(days) or 1


def rrule_effective_period_hours(rrule: str) -> float | None:
    """Estimate the effective period between runs for common Codex cron RRULEs."""
    if not rrule:
        return None
    parts = parse_rrule(rrule)
    frequency = str(parts.get("FREQ") or "").upper()
    interval = max(int(parts.get("INTERVAL") or 1), 1)
    if frequency == "MINUTELY":
        return interval / 60
    if frequency == "HOURLY":
        return float(interval)
    if frequency == "DAILY":
        return float(24 * interval)
    if frequency == "WEEKLY":
        return float(24 * 7 * interval) / _byday_count(parts)
    if frequency == "MONTHLY":
        return float(24 * 30 * interval)
    if frequency == "YEARLY":
        return float(24 * 365 * interval)
    return None


def _allowed_months(parts: dict[str, list[str] | str | int]) -> set[int]:
    return set(values_as_ints(parts, "BYMONTH", list(range(1, 13))))


def _allowed_monthdays(parts: dict[str, list[str] | str | int]) -> set[int]:
    # BUGSWEEP-20 REVIEW-NOTIZ (L-02 RRULE, NICHT auto-gefixt — User-Entscheidung): MONTHLY ohne
    # BYMONTHDAY defaultet hier auf den 1. statt (RFC 5545) den Tag aus DTSTART abzuleiten. Eine am
    # 15. angelegte MONTHLY-Automation ohne BYMONTHDAY=15 gilt dadurch evtl. faelschlich als verpasst.
    # RRULE-Semantik bewusst nicht angetastet (Terminlogik ist heikel).
    return set(values_as_ints(parts, "BYMONTHDAY", [1]))


def _matches_frequency_day(
    parts: dict[str, list[str] | str | int],
    current: datetime,
    start: datetime,
) -> bool:
    frequency = str(parts.get("FREQ") or "").upper()
    interval = max(int(parts.get("INTERVAL") or 1), 1)
    if current.weekday() not in allowed_days(parts):
        return False
    if frequency == "DAILY":
        return ((current.date() - start.date()).days % interval) == 0
    if frequency == "WEEKLY":
        return (((current.date() - start.date()).days // 7) % interval) == 0
    if frequency == "MONTHLY":
        months = (current.year - start.year) * 12 + current.month - start.month
        return (
            months >= 0
            and months % interval == 0
            and current.month in _allowed_months(parts)
            and current.day in _allowed_monthdays(parts)
        )
    if frequency == "YEARLY":
        years = current.year - start.year
        return (
            years >= 0
            and years % interval == 0
            and current.month in _allowed_months(parts)
            and current.day in _allowed_monthdays(parts)
        )
    return False


def rrule_occurrences_between(
    rrule: str,
    start: datetime,
    end: datetime,
    *,
    limit: int = 1000,
) -> list[datetime]:
    if not rrule or end <= start or limit <= 0:
        return []
    parts = parse_rrule(rrule)
    frequency = str(parts.get("FREQ") or "").upper()
    interval = max(int(parts.get("INTERVAL") or 1), 1)
    minutes = values_as_ints(parts, "BYMINUTE", [0])
    hours = values_as_ints(parts, "BYHOUR", list(range(24)))
    result: list[datetime] = []

    if frequency == "HOURLY":
        if interval > 24 or 24 % interval != 0:
            step = timedelta(hours=interval)
            target_minute = sorted(minutes)[0] if minutes else 0
            cursor = (start.replace(second=0, microsecond=0) + step).replace(minute=target_minute, second=0, microsecond=0)
            if cursor <= start:
                cursor += timedelta(hours=1)
            while cursor <= end and len(result) < limit:
                if cursor.hour in hours:
                    result.append(cursor)
                cursor += step
            return result
        cursor = start.replace(second=0, microsecond=0) + timedelta(minutes=1)
        while cursor <= end and len(result) < limit:
            if cursor.minute in minutes and cursor.hour in hours and cursor.hour % interval == 0:
                result.append(cursor)
            cursor += timedelta(minutes=1)
        return result

    if frequency not in {"DAILY", "WEEKLY", "MONTHLY", "YEARLY"}:
        return result

    cursor_day = start.date()
    end_day = end.date()
    tzinfo = start.tzinfo
    while cursor_day <= end_day and len(result) < limit:
        day_start = datetime.combine(cursor_day, day_time(0, 0), tzinfo=tzinfo)
        if _matches_frequency_day(parts, day_start, start):
            for hour in sorted(hours):
                for minute in sorted(minutes):
                    candidate = datetime.combine(cursor_day, day_time(hour, minute), tzinfo=tzinfo)
                    if start < candidate <= end:
                        result.append(candidate)
                        if len(result) >= limit:
                            break
                if len(result) >= limit:
                    break
        cursor_day += timedelta(days=1)
    return result


def _coerce_datetime(value: object) -> datetime | None:
    if value is None or value == "":
        return None
    if isinstance(value, (int, float)):
        numeric = float(value)
        if numeric > 10_000_000_000:
            numeric = numeric / 1000
        try:
            return datetime.fromtimestamp(numeric).astimezone()
        except (OSError, OverflowError, ValueError):
            return None
    text = str(value).strip()
    if not text:
        return None
    try:
        if text.endswith("Z"):
            text = text[:-1] + "+00:00"
        parsed = datetime.fromisoformat(text)
        return parsed.astimezone() if parsed.tzinfo is not None else parsed
    except ValueError:
        return None


def _align_datetime(value: datetime | None, reference: datetime) -> datetime | None:
    if value is None:
        return None
    if reference.tzinfo is None and value.tzinfo is not None:
        return value.replace(tzinfo=None)
    if reference.tzinfo is not None and value.tzinfo is None:
        return value.replace(tzinfo=reference.tzinfo)
    if reference.tzinfo is not None and value.tzinfo is not None:
        return value.astimezone(reference.tzinfo)
    return value


def _datetime_from_ms(value: int | None) -> datetime | None:
    return _coerce_datetime(value)


def _parse_report_datetime(value: str | None) -> datetime | None:
    return _coerce_datetime(value)


def read_observed_runs_from_state(
    automations: Iterable[Automation],
    state_db: Path | None = None,
) -> tuple[dict[str, list[ObservedRun]], str, list[str]]:
    """Best-effort run history from Codex state, reading only thread IDs/titles/timestamps."""
    db_path = state_db or codex_state_db_path()
    notes = [
        "Run history is best-effort and title-based; prompt bodies are not read.",
        "No automation is triggered by catchup planning.",
    ]
    observed: dict[str, list[ObservedRun]] = {item.id: [] for item in automations}
    if not db_path.exists():
        notes.append(f"State DB not found: {db_path}")
        return observed, "none", notes

    try:
        uri = f"file:{db_path.resolve().as_posix()}?mode=ro"
        # Bugsweep 20 BUG-B1: `with sqlite3.connect(...)` committet/rollbackt nur, schliesst die
        # Connection NICHT -> Datei-Handle bleibt bis zum GC offen (Leak, mehrfache catchup-Aufrufe).
        with contextlib.closing(sqlite3.connect(uri, uri=True)) as connection:
            connection.row_factory = sqlite3.Row
            columns = {
                str(row["name"])
                for row in connection.execute("PRAGMA table_info(threads)").fetchall()
            }
            if not columns:
                notes.append("No threads table found in state DB.")
                return observed, str(db_path), notes
            id_column = "id" if "id" in columns else "thread_id" if "thread_id" in columns else ""
            if not id_column or "title" not in columns:
                notes.append("Threads table does not expose id/title columns.")
                return observed, str(db_path), notes
            wanted = [
                column
                for column in (
                    id_column,
                    "title",
                    "created_at_ms",
                    "created_at",
                    "updated_at_ms",
                    "updated_at",
                )
                if column in columns
            ]
            order_column = "created_at_ms" if "created_at_ms" in columns else "created_at" if "created_at" in columns else id_column
            query = f"SELECT {', '.join(wanted)} FROM threads ORDER BY {order_column} DESC LIMIT 2000"
            rows = [dict(row) for row in connection.execute(query).fetchall()]
    except sqlite3.Error as exc:
        notes.append(f"Could not read state DB: {exc}")
        return observed, str(db_path), notes

    matchers = [
        (
            item.id,
            [needle.casefold() for needle in (item.id, item.name) if len(str(needle).strip()) >= 3],
        )
        for item in automations
    ]
    for row in rows:
        title = str(row.get("title") or "")
        haystack = title.casefold()
        if not haystack:
            continue
        timestamp = (
            _coerce_datetime(row.get("created_at_ms"))
            or _coerce_datetime(row.get("created_at"))
            or _coerce_datetime(row.get("updated_at_ms"))
            or _coerce_datetime(row.get("updated_at"))
        )
        if timestamp is None:
            continue
        for automation_id, needles in matchers:
            if any(needle and needle in haystack for needle in needles):
                observed.setdefault(automation_id, []).append(
                    ObservedRun(
                        automation_id=automation_id,
                        thread_id=str(row.get(id_column) or ""),
                        created_at=timestamp.isoformat(timespec="seconds"),
                        title=title,
                    )
                )
    return observed, str(db_path), notes


def build_catchup_report(
    automations: list[Automation] | None = None,
    *,
    now: datetime | None = None,
    lookback_days: int = 30,
    min_period_hours: int = 24,
    max_per_start: int = 1,
    include_paused: bool = False,
    state_db: Path | None = None,
    observed_runs: dict[str, list[ObservedRun]] | None = None,
) -> CatchupReport:
    items = automations if automations is not None else load_automations()
    current = now or local_now()
    lookback_start = current - timedelta(days=max(lookback_days, 0))
    if observed_runs is None:
        observed_runs, history_source, notes = read_observed_runs_from_state(items, state_db)
    else:
        history_source = str(state_db or codex_state_db_path())
        notes = ["Run history was supplied by the caller."]

    candidates: list[CatchupCandidate] = []
    for item in items:
        period = rrule_effective_period_hours(item.rrule)
        if period is None or period <= min_period_hours:
            continue

        status = (item.original_status or item.status or "UNKNOWN").upper()
        if not include_paused and status != "ACTIVE":
            continue

        created_at = _align_datetime(_datetime_from_ms(item.created_at), current)
        since = max(lookback_start, created_at) if created_at is not None else lookback_start
        due_times = rrule_occurrences_between(item.rrule, since, current, limit=1000)
        last_due = due_times[-1] if due_times else None
        next_due = rrule_next_after(item.rrule, current)
        observed_for_item = observed_runs.get(item.id, [])
        observed_dates = [
            parsed
            for parsed in (_parse_report_datetime(run.created_at) for run in observed_for_item)
            if parsed is not None
        ]
        aligned_observed = [
            value
            for value in (_align_datetime(observed_at, current) for observed_at in observed_dates)
            if value is not None
        ]
        last_observed = max(aligned_observed) if aligned_observed else None
        missed = bool(last_due and (last_observed is None or last_observed < last_due))

        if status != "ACTIVE":
            reason = "paused"
        elif not last_due:
            reason = "no due time in lookback window"
        elif missed:
            reason = "latest rare due time has no observed run"
        else:
            reason = "observed after latest due time"

        candidates.append(
            CatchupCandidate(
                automation_id=item.id,
                name=item.name,
                status=status,
                rrule=item.rrule,
                period_hours=round(period, 2),
                last_due_at=last_due.isoformat(timespec="seconds") if last_due else None,
                next_due_at=next_due.isoformat(timespec="seconds") if next_due else None,
                last_observed_at=last_observed.isoformat(timespec="seconds") if last_observed else None,
                missed=missed,
                eligible=False,
                reason=reason,
                confidence="thread-title" if observed_for_item else "schedule-only",
            )
        )

    missed_active = [
        candidate
        for candidate in candidates
        if candidate.missed and candidate.status == "ACTIVE"
    ]
    missed_active.sort(key=lambda candidate: candidate.last_due_at or "")
    eligible_ids = [candidate.automation_id for candidate in missed_active[: max(max_per_start, 0)]]
    eligible = set(eligible_ids)
    for candidate in candidates:
        if candidate.automation_id in eligible:
            candidate.eligible = True
            candidate.reason = "eligible for early release"
        elif candidate.missed and candidate.status == "ACTIVE":
            candidate.reason = "missed but held by catchup_max_per_start"

    return CatchupReport(
        created_at=current.isoformat(timespec="seconds"),
        lookback_days=lookback_days,
        min_period_hours=min_period_hours,
        max_per_start=max_per_start,
        history_source=history_source,
        candidates=candidates,
        eligible_ids=eligible_ids,
        notes=notes,
    )


def write_catchup_report(run_id: str, report: CatchupReport) -> Path:
    data = {
        "run_id": run_id,
        **report.to_dict(),
    }
    payload = json.dumps(data, ensure_ascii=False, indent=2)
    path = state_dir() / f"{run_id}-catchup-plan.json"
    _atomic_write_text(path, payload)
    _atomic_write_text(state_dir() / "latest-catchup-plan.json", payload)
    return path


def split_release_queue(
    active_items: list[Automation],
    release_reference: datetime,
    min_lead: timedelta,
) -> tuple[list[Automation], list[Automation]]:
    future_safe: list[tuple[datetime, str, Automation]] = []
    fallback: list[tuple[datetime, str, Automation]] = []
    for item in active_items:
        next_at = rrule_next_after(item.rrule, release_reference)
        item.next_at = next_at.isoformat(timespec="seconds") if next_at else None
        if next_at and next_at >= release_reference + min_lead:
            future_safe.append((next_at, item.id, item))
        else:
            fallback.append((next_at or release_reference + timedelta(days=30), item.id, item))
    future_safe.sort(key=lambda row: (row[0], row[1]))
    fallback.sort(key=lambda row: (row[0], row[1]))
    return [item for _, _, item in future_safe], [item for _, _, item in fallback]


def launch_codex(dry_run: bool, run_id: str) -> None:
    exe = find_codex_exe()
    if dry_run:
        append_log(run_id, "dry_run_launch_codex", path=str(exe or CODEX_STORE_AUMID))
        return
    if os.name != "nt":
        raise RuntimeError("Codex Desktop launch is only implemented for Windows.")
    if exe:
        append_log(run_id, "launch_codex", path=str(exe))
        subprocess.Popen([str(exe)], cwd=str(exe.parent), close_fds=True, **no_window_kwargs())
        return
    app_id = rf"shell:appsFolder\{CODEX_STORE_AUMID}"
    append_log(run_id, "launch_codex_appid", app_id=app_id)
    subprocess.Popen(["explorer.exe", app_id], close_fds=True, **no_window_kwargs())


class SafeStartGate:
    def __init__(
        self,
        *,
        initial_release: int = DEFAULT_INITIAL_RELEASE,
        interval_minutes: int = DEFAULT_INTERVAL_MINUTES,
        startup_delay_seconds: int = DEFAULT_STARTUP_DELAY_SECONDS,
        min_future_lead_minutes: int = DEFAULT_MIN_FUTURE_LEAD_MINUTES,
        launch: bool = True,
        cleanup: bool = True,
        catchup_enabled: bool = False,
        catchup_lookback_days: int = 30,
        catchup_max_per_start: int = 1,
        catchup_min_period_hours: int = 24,
        dry_run: bool = False,
        notifier: Callable[[str, str], None] | None = None,
        quiet: bool = False,
    ) -> None:
        self.initial_release = initial_release
        self.interval_minutes = interval_minutes
        self.startup_delay_seconds = startup_delay_seconds
        self.min_future_lead_minutes = min_future_lead_minutes
        self.launch = launch
        self.cleanup = cleanup
        self.catchup_enabled = catchup_enabled
        self.catchup_lookback_days = catchup_lookback_days
        self.catchup_max_per_start = catchup_max_per_start
        self.catchup_min_period_hours = catchup_min_period_hours
        self.dry_run = dry_run
        self.notifier = notifier
        self.quiet = quiet
        self.run_id = local_now().strftime("%Y%m%d-%H%M%S")
        self.items: list[Automation] = []
        self.tool_paused: list[Automation] = []
        self.release_queue: list[Automation] = []
        self.cleanup_result: CleanupResult | None = None
        self.catchup_report: CatchupReport | None = None
        self.stop_event = threading.Event()
        self.lock = threading.RLock()
        self.restored = False
        self.completed = False
        self.last_message = "Start prepared"

    def emit(self, message: str, *, title: str = "Safe Start for Codex") -> None:
        self.last_message = message
        if not self.quiet:
            print(f"[safe-start] {message}", flush=True)
        append_log(self.run_id, "message", message=message)
        if self.notifier:
            try:
                self.notifier(title, message)
            except Exception:
                pass

    def wait_or_stop(self, seconds: int) -> bool:
        if self.dry_run or seconds <= 0:
            return self.stop_event.is_set()
        return self.stop_event.wait(seconds)

    def pause_active(self) -> None:
        active = [item for item in self.items if item.status.upper() == "ACTIVE"]
        for item in active:
            item.tool_paused = True
            append_log(self.run_id, "pause", automation_id=item.id, dry_run=self.dry_run)
            if not self.dry_run:
                set_status(Path(item.path), "PAUSED")
            item.status = "PAUSED"
        self.tool_paused = active
        self.emit(f"Found {len(self.items)} automations; paused {len(active)} active automations.")

    def release_item(self, item: Automation) -> None:
        if item.released:
            return
        append_log(
            self.run_id,
            "release",
            automation_id=item.id,
            dry_run=self.dry_run,
            next_at=item.next_at,
        )
        if not self.dry_run:
            set_status(Path(item.path), "ACTIVE")
        item.status = "ACTIVE"
        item.released = True
        self.emit(f"Released: {item.id} (next scheduled time: {item.next_at or 'unknown'})")

    def restore(self, reason: str = "exit", *, stop: bool = True) -> None:
        if stop:
            self.stop_event.set()
        with self.lock:
            if self.restored:
                return
            restored = 0
            for item in self.tool_paused:
                if item.original_status.upper() != "ACTIVE":
                    continue
                append_log(
                    self.run_id,
                    "restore",
                    automation_id=item.id,
                    reason=reason,
                    dry_run=self.dry_run,
                )
                if not self.dry_run:
                    set_status(Path(item.path), item.original_status)
                item.status = item.original_status
                item.released = True
                restored += 1
            self.restored = True
            write_snapshot(self.run_id, self.items, "restored", reason=reason, restored=restored)
            self.emit(f"Restored original state for {restored} tool-paused automations.")

    def status_text(self) -> str:
        with self.lock:
            paused = len(self.tool_paused)
            released = sum(1 for item in self.tool_paused if item.released)
            remaining = max(paused - released, 0)
            return f"{released}/{paused} released, {remaining} still gated. Last status: {self.last_message}"

    def run(self) -> None:
        self.emit("Startup gate is running.")
        if self.cleanup:
            self.cleanup_result = cleanup_start_blockers(execute=not self.dry_run, run_id=self.run_id)
            for message in self.cleanup_result.messages:
                self.emit(message)

        self.items = load_automations()
        self.pause_active()
        write_snapshot(
            self.run_id,
            self.items,
            "paused",
            cleanup=self.cleanup_result.to_dict() if self.cleanup_result else None,
        )

        if self.launch:
            launch_codex(self.dry_run, self.run_id)
            self.emit(f"Codex launched. First release in {self.startup_delay_seconds} seconds.")
            if self.wait_or_stop(self.startup_delay_seconds):
                self.emit("Stopped before first release.")
                return

        reference = local_now()
        future_safe, fallback = split_release_queue(
            self.tool_paused,
            reference,
            timedelta(minutes=self.min_future_lead_minutes),
        )
        catchup_priority_ids: set[str] = set()
        if self.catchup_enabled:
            self.catchup_report = build_catchup_report(
                self.items,
                now=reference,
                lookback_days=self.catchup_lookback_days,
                min_period_hours=self.catchup_min_period_hours,
                max_per_start=self.catchup_max_per_start,
            )
            write_catchup_report(self.run_id, self.catchup_report)
            append_log(
                self.run_id,
                "catchup_plan",
                eligible_ids=self.catchup_report.eligible_ids,
                candidates=len(self.catchup_report.candidates),
                history_source=self.catchup_report.history_source,
            )
            catchup_priority_ids = set(self.catchup_report.eligible_ids)
            if catchup_priority_ids:
                self.emit(
                    "Catch-up plan: "
                    f"{len(catchup_priority_ids)} rare missed automation(s) prioritized for early release."
                )
            else:
                self.emit("Catch-up plan: no rare missed automation needs early release.")

        ordered = future_safe + fallback
        priority = [item for item in ordered if item.id in catchup_priority_ids]
        remaining_future = [item for item in future_safe if item.id not in catchup_priority_ids]
        remaining_fallback = [item for item in fallback if item.id not in catchup_priority_ids]
        first_capacity = max(self.initial_release, len(priority))
        first = priority + remaining_future[: max(first_capacity - len(priority), 0)]
        rest = remaining_future[max(first_capacity - len(priority), 0) :] + remaining_fallback
        self.release_queue = first + rest
        write_snapshot(
            self.run_id,
            self.items,
            "release-queue",
            first_release_ids=[item.id for item in first],
            delayed_release_ids=[item.id for item in rest],
            fallback_ids=[item.id for item in fallback],
            catchup_priority_ids=sorted(catchup_priority_ids),
        )
        self.emit(
            f"Initial release: {len(first)} future-safe automations. "
            f"Then one more every {self.interval_minutes} minutes."
        )

        for item in first:
            if self.stop_event.is_set():
                return
            self.release_item(item)

        for index, item in enumerate(rest, start=1):
            self.emit(f"Next release in {self.interval_minutes} minutes ({index}/{len(rest)}).")
            if self.wait_or_stop(self.interval_minutes * 60):
                self.emit("Release staggering stopped.")
                return
            self.release_item(item)

        self.completed = True
        write_snapshot(self.run_id, self.items, "finished")
        append_log(self.run_id, "finished", released=len(self.release_queue), dry_run=self.dry_run)
        self.emit("Release staggering finished. Tray remains available for restore/quit.")


def command_start(args: argparse.Namespace) -> int:
    settings, config_path, config_exists = resolve_gate_settings(args)
    gate = SafeStartGate(
        initial_release=settings.initial_release,
        interval_minutes=settings.interval_minutes,
        startup_delay_seconds=settings.startup_delay_seconds,
        min_future_lead_minutes=settings.min_future_lead_minutes,
        launch=settings.launch,
        cleanup=settings.cleanup,
        catchup_enabled=settings.catchup_enabled,
        catchup_lookback_days=settings.catchup_lookback_days,
        catchup_max_per_start=settings.catchup_max_per_start,
        catchup_min_period_hours=settings.catchup_min_period_hours,
        dry_run=args.dry_run,
    )
    append_log(
        gate.run_id,
        "config",
        config_path=str(config_path),
        config_exists=config_exists,
        settings=settings.to_dict(),
    )
    try:
        gate.run()
        return 0
    except KeyboardInterrupt:
        print("\nInterrupted. Restoring original automation state.", flush=True)
        return 130
    finally:
        if args.restore_on_exit:
            gate.restore("process-exit")


def command_tray(args: argparse.Namespace) -> int:
    try:
        import pystray
        from PIL import Image, ImageDraw
    except ImportError as exc:
        print(f"Tray dependency missing: {exc}")
        print("Install with: python -m pip install 'safe-start-for-codex[tray]'")
        return 1

    def draw_fallback_icon(size: int = 64) -> Image.Image:
        image = Image.new("RGBA", (size, size), (12, 23, 38, 0))
        draw = ImageDraw.Draw(image)
        draw.rounded_rectangle((3, 3, size - 4, size - 4), radius=14, fill=(12, 34, 52, 255))
        draw.polygon(
            [
                (size * 0.5, size * 0.14),
                (size * 0.78, size * 0.26),
                (size * 0.72, size * 0.68),
                (size * 0.5, size * 0.86),
                (size * 0.28, size * 0.68),
                (size * 0.22, size * 0.26),
            ],
            fill=(27, 164, 179, 255),
        )
        draw.rectangle((size * 0.36, size * 0.33, size * 0.43, size * 0.66), fill=(245, 248, 250, 255))
        draw.rectangle((size * 0.57, size * 0.33, size * 0.64, size * 0.66), fill=(245, 248, 250, 255))
        draw.arc((size * 0.30, size * 0.23, size * 0.70, size * 0.73), 300, 80, fill=(125, 220, 114, 255), width=4)
        return image

    icon_ref: dict[str, pystray.Icon] = {}

    def notify(title: str, message: str) -> None:
        icon = icon_ref.get("icon")
        if not icon:
            return
        try:
            icon.notify(message, title)
        except Exception:
            pass

    settings, config_path, config_exists = resolve_gate_settings(args)
    gate = SafeStartGate(
        initial_release=settings.initial_release,
        interval_minutes=settings.interval_minutes,
        startup_delay_seconds=settings.startup_delay_seconds,
        min_future_lead_minutes=settings.min_future_lead_minutes,
        launch=settings.launch,
        cleanup=settings.cleanup,
        catchup_enabled=settings.catchup_enabled,
        catchup_lookback_days=settings.catchup_lookback_days,
        catchup_max_per_start=settings.catchup_max_per_start,
        catchup_min_period_hours=settings.catchup_min_period_hours,
        dry_run=args.dry_run,
        notifier=notify,
        quiet=True,
    )
    append_log(
        gate.run_id,
        "config",
        config_path=str(config_path),
        config_exists=config_exists,
        settings=settings.to_dict(),
    )

    def on_status(_icon: pystray.Icon, _item: object) -> None:
        notify("Safe Start for Codex", gate.status_text())

    def on_restore(_icon: pystray.Icon, _item: object) -> None:
        gate.restore("tray-restore")
        notify("Safe Start for Codex", "Original automation state has been restored.")

    def on_quit(icon: pystray.Icon, _item: object) -> None:
        gate.restore("tray-exit")
        icon.stop()

    menu = pystray.Menu(
        pystray.MenuItem("Show status", on_status, default=True),
        pystray.MenuItem("Restore original state", on_restore),
        pystray.MenuItem("Quit and restore", on_quit),
    )
    icon = pystray.Icon("safe-start-for-codex", draw_fallback_icon(), "Safe Start for Codex", menu)
    icon_ref["icon"] = icon

    def worker() -> None:
        try:
            gate.run()
        except Exception as exc:
            append_log(gate.run_id, "worker_error", error=str(exc))
            gate.restore("worker-error")
            notify("Safe Start for Codex error", str(exc))

    def updater() -> None:
        while not gate.stop_event.wait(30):
            try:
                icon.title = "Safe Start for Codex - " + gate.status_text()[:80]
            except Exception:
                return

    def setup(_icon: pystray.Icon) -> None:
        threading.Thread(target=worker, name="safe-start-for-codex-worker", daemon=True).start()
        threading.Thread(target=updater, name="safe-start-for-codex-title", daemon=True).start()
        notify("Safe Start for Codex", "Automation gate is running in the tray.")

    icon.run(setup=setup)
    return 0


def command_status(_: argparse.Namespace) -> int:
    latest = state_dir() / "latest.json"
    if not latest.exists():
        print("No Safe Start snapshot exists yet.")
        return 0
    # Bugsweep 20 BUG-B3: korrupte/halb-geschriebene latest.json (Absturz, OneDrive-Sync-Konflikt)
    # soll eine lesbare Meldung geben statt das CLI mit JSONDecodeError abzubrechen.
    try:
        data = json.loads(latest.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as exc:
        print(f"Snapshot beschaedigt/unlesbar ({latest}): {exc}")
        return 1
    print(f"Latest snapshot: {latest}")
    print(f"Run: {data.get('run_id')} | Phase: {data.get('phase')} | Time: {data.get('created_at')}")
    print(f"Tool-paused: {len(data.get('tool_paused_ids') or [])}")
    print(f"Released: {len(data.get('released_ids') or [])}")
    current = load_automations()
    active = sum(1 for item in current if item.status.upper() == "ACTIVE")
    paused = sum(1 for item in current if item.status.upper() == "PAUSED")
    print(f"Current state: {active} ACTIVE, {paused} PAUSED, {len(current)} total")
    return 0


def command_config_show(args: argparse.Namespace) -> int:
    settings, config_path, exists = read_gate_config(args.config)
    data = {
        "path": str(config_path),
        "exists": exists,
        "settings": settings.to_dict(),
    }
    print(json.dumps(data, ensure_ascii=False, indent=2))
    return 0


def command_config_init(args: argparse.Namespace) -> int:
    config_path = args.config or default_config_path()
    write_default_config(config_path, force=args.force)
    print(f"Config written: {config_path}")
    return 0


def command_catchup_plan(args: argparse.Namespace) -> int:
    settings, _, _ = resolve_gate_settings(args)
    report = build_catchup_report(
        lookback_days=settings.catchup_lookback_days,
        min_period_hours=settings.catchup_min_period_hours,
        max_per_start=settings.catchup_max_per_start,
        include_paused=args.include_paused,
    )
    if args.json:
        print(json.dumps(report.to_dict(), ensure_ascii=False, indent=2))
        return 0

    print(f"Catch-up plan created: {report.created_at}")
    print(f"History source: {report.history_source}")
    print(f"Rare candidates: {len(report.candidates)}")
    print(f"Eligible for early release: {len(report.eligible_ids)}")
    for candidate in report.candidates:
        marker = "*" if candidate.eligible else "-"
        print(
            f"{marker} {candidate.automation_id}: missed={candidate.missed}, "
            f"last_due={candidate.last_due_at or 'unknown'}, "
            f"last_observed={candidate.last_observed_at or 'none'}, "
            f"reason={candidate.reason}"
        )
    if report.notes:
        print("Notes:")
        for note in report.notes:
            print(f"- {note}")
    return 0


def command_restore_latest(args: argparse.Namespace) -> int:
    latest = state_dir() / "latest.json"
    if not latest.exists():
        print("No snapshot found for restore.")
        return 1
    # Bugsweep 20 BUG-B3: korrupte latest.json -> lesbare Meldung statt unkontrolliertem Crash.
    try:
        data = json.loads(latest.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as exc:
        print(f"Snapshot beschaedigt/unlesbar ({latest}): {exc}")
        return 1
    restored = 0
    for row in data.get("items") or []:
        if not row.get("tool_paused"):
            continue
        original = row.get("original_status")
        path = Path(row.get("path") or "")
        if original == "ACTIVE" and path.exists():
            print(f"[restore] {row.get('id')} -> {original}")
            if not args.dry_run:
                set_status(path, original)
            restored += 1
    print(f"Restored {restored} tool-paused automations from {latest}")
    return 0


def command_backup(_: argparse.Namespace) -> int:
    root = automations_dir()
    dest = state_dir() / ("manual-backup-" + local_now().strftime("%Y%m%d-%H%M%S"))
    shutil.copytree(root, dest, ignore=shutil.ignore_patterns("_archive"))
    print(f"Backup created: {dest}")
    return 0


def add_gate_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--config",
        type=Path,
        default=None,
        help=f"Path to a Safe Start config JSON file. Default: {default_config_path()}",
    )
    parser.add_argument("--initial-release", type=int, default=None)
    parser.add_argument("--interval-minutes", type=int, default=None)
    parser.add_argument("--startup-delay-seconds", type=int, default=None)
    parser.add_argument("--min-future-lead-minutes", type=int, default=None)
    parser.add_argument("--catchup-enabled", dest="catchup_enabled", action=argparse.BooleanOptionalAction, default=None)
    parser.add_argument("--catchup-lookback-days", type=int, default=None)
    parser.add_argument("--catchup-max-per-start", type=int, default=None)
    parser.add_argument("--catchup-min-period-hours", type=int, default=None)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--launch", dest="launch", action=argparse.BooleanOptionalAction, default=None)
    parser.add_argument("--cleanup", dest="cleanup", action=argparse.BooleanOptionalAction, default=None)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Unofficial Windows startup gate for Codex Desktop automations."
    )
    sub = parser.add_subparsers(dest="command")

    start = sub.add_parser("start", help="Foreground run with restore on process exit.")
    add_gate_arguments(start)
    start.add_argument("--no-restore-on-exit", dest="restore_on_exit", action="store_false")
    start.set_defaults(restore_on_exit=True, func=command_start)

    tray = sub.add_parser("tray", help="Run a tray app with restore on quit.")
    add_gate_arguments(tray)
    tray.set_defaults(func=command_tray)

    dry = sub.add_parser("dry-run", help="Show the planned flow without changing files.")
    add_gate_arguments(dry)
    dry.set_defaults(dry_run=True, launch=False, restore_on_exit=True, func=command_start)

    status = sub.add_parser("status", help="Show latest snapshot and current ACTIVE/PAUSED state.")
    status.set_defaults(func=command_status)

    config_show = sub.add_parser("config-show", help="Show the resolved Safe Start configuration.")
    config_show.add_argument("--config", type=Path, default=None)
    config_show.set_defaults(func=command_config_show)

    config_init = sub.add_parser("config-init", help="Write a default Safe Start config.json.")
    config_init.add_argument("--config", type=Path, default=None)
    config_init.add_argument("--force", action="store_true")
    config_init.set_defaults(func=command_config_init)

    catchup = sub.add_parser(
        "catchup-plan",
        help="Report rare automations that appear to have missed a scheduled run.",
    )
    add_gate_arguments(catchup)
    catchup.add_argument("--json", action="store_true")
    catchup.add_argument("--include-paused", action="store_true")
    catchup.set_defaults(func=command_catchup_plan)

    restore = sub.add_parser("restore-latest", help="Restore only automations paused by this tool.")
    restore.add_argument("--dry-run", action="store_true")
    restore.set_defaults(func=command_restore_latest)

    backup = sub.add_parser("backup", help="Create a manual backup of automation TOML files.")
    backup.set_defaults(func=command_backup)
    return parser


def main(argv: list[str] | None = None) -> int:
    if argv is None:
        argv = sys.argv[1:]
    parser = build_parser()
    if not argv:
        parser.print_help()
        return 0
    args = parser.parse_args(argv)
    if not hasattr(args, "func"):
        parser.print_help()
        return 0
    return int(args.func(args))
