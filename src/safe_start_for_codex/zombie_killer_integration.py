"""Optional zombie-killer-tray integration for Safe Start (T-20260926-212716751).

Safe Start for Codex is cross-platform (Windows/Linux/macOS) with zero
required runtime dependencies. zombie-killer-tray is Windows-only (Win32
process APIs). This integration therefore stays entirely optional and
Windows-gated: nothing here is imported or run unless a caller explicitly
asks for it, and `launch_zombie_killer_watch()` refuses cleanly on any
non-Windows platform instead of attempting anything.

Same pattern as `dev-bricks/CareCenter-for-Codex`'s existing
`safe_start_integration.py`/`zombie_killer_integration.py`: a git-pinned pip
dependency, launched as its own subprocess via
`python -m zombie_killer_tray watch ...`, coordinated through the shared
zombie_events.jsonl audit log -- never an in-process import.
"""

from __future__ import annotations

import json
import os
import signal
import subprocess
import sys
from collections.abc import Callable
from dataclasses import asdict, dataclass
from pathlib import Path

from .cli import codex_home, no_window_kwargs

# T-20260926-212716751: zombie-killer-tray#4 (src/-Paketierung) merged as 039b4f2.
ZOMBIE_KILLER_PACKAGE_SPEC = (
    "zombie-killer-tray @ "
    "git+https://github.com/dev-bricks/zombie-killer-tray.git"
    "@039b4f2c7acd69063b39d6168c757b0b2fca2438"
)
ZOMBIE_KILLER_SOURCE_ENV = "SAFE_START_ZOMBIE_KILLER_SOURCE"
DEFAULT_WATCH_INTERVAL_SECONDS = 600
DEFAULT_MIN_AGE_SECONDS = 1800


@dataclass(slots=True)
class ZombieKillerInstallResult:
    status: str
    target: str
    command: list[str]
    message: str
    stdout: str = ""
    stderr: str = ""

    def to_dict(self) -> dict[str, object]:
        return asdict(self)

    def to_text(self) -> str:
        lines = [
            f"Status: {self.status}",
            f"Target: {self.target}",
            "Command: " + " ".join(self.command),
            self.message,
        ]
        if self.stdout.strip():
            lines.append("Output:")
            lines.append(self.stdout.strip())
        if self.stderr.strip():
            lines.append("Error output:")
            lines.append(self.stderr.strip())
        return "\n".join(lines)


@dataclass(slots=True)
class ZombieKillerLaunchResult:
    status: str
    command: list[str]
    message: str
    state_dir: str
    pid: int | None = None

    def to_dict(self) -> dict[str, object]:
        return asdict(self)

    def to_text(self) -> str:
        lines = [f"Status: {self.status}", "Command: " + " ".join(self.command), self.message,
                  f"State dir: {self.state_dir}"]
        if self.pid is not None:
            lines.append(f"PID: {self.pid}")
        return "\n".join(lines)


@dataclass(slots=True)
class ZombieKillerStopResult:
    status: str
    message: str
    pid: int | None = None

    def to_dict(self) -> dict[str, object]:
        return asdict(self)

    def to_text(self) -> str:
        lines = [f"Status: {self.status}", self.message]
        if self.pid is not None:
            lines.append(f"PID: {self.pid}")
        return "\n".join(lines)


@dataclass(slots=True)
class ZombieKillerStatus:
    available: bool
    supported_platform: bool
    state_dir: str
    last_cycle_at: float | None
    last_cycle_count: int | None
    notes: list[str]

    def to_dict(self) -> dict[str, object]:
        return asdict(self)

    def to_text(self) -> str:
        availability = "installed" if self.available else "not installed"
        lines = [f"zombie-killer-tray: {availability}", f"State dir: {self.state_dir}"]
        if self.last_cycle_at is not None:
            lines.append(f"Last cycle: {self.last_cycle_at} (reaped: {self.last_cycle_count})")
        if self.notes:
            lines.append("Notes:")
            lines.extend(f"- {note}" for note in self.notes)
        return "\n".join(lines)


def _is_windows() -> bool:
    """Testable seam for the platform gate -- monkeypatching `os.name` itself
    would break pathlib's own Windows/Posix class dispatch mid-test."""
    return os.name == "nt"


def zombie_killer_state_dir() -> Path:
    """zombie-killer-tray's own working directory, under CODEX_HOME.

    zombie-killer-tray writes its runtime state (`zombie_events.jsonl`,
    `zombie_worker_errors.log`) to its current working directory, not to a
    hardcoded path -- this is passed as `cwd=` to the watch subprocess
    (see `launch_zombie_killer_watch`).
    """
    path = codex_home() / "zombie-killer-tray"
    path.mkdir(parents=True, exist_ok=True)
    return path


def _zombie_killer_importable() -> bool:
    try:
        __import__("zombie_killer_tray.killer")
    except Exception:
        return False
    return True


def _local_zombie_killer_source() -> Path | None:
    env_path = os.environ.get(ZOMBIE_KILLER_SOURCE_ENV)
    if env_path:
        candidate = Path(env_path).expanduser()
        if (candidate / "pyproject.toml").exists():
            return candidate

    project_root = Path(__file__).resolve().parents[2]
    sibling = project_root.parent / "REL-PUB_zombie-killer-tray"
    if (sibling / "pyproject.toml").exists():
        return sibling
    return None


def zombie_killer_install_target() -> str:
    """Prefer a local sibling checkout, otherwise the commit-pinned GitHub source."""
    local_source = _local_zombie_killer_source()
    if local_source is not None:
        return str(local_source)
    return ZOMBIE_KILLER_PACKAGE_SPEC


def _pip_command_candidates() -> list[list[str]]:
    candidates: list[list[str]] = []
    if not getattr(sys, "frozen", False):
        candidates.append([sys.executable, "-m", "pip"])
    candidates.extend((["py", "-3", "-m", "pip"], ["python3", "-m", "pip"], ["python", "-m", "pip"]))

    unique: list[list[str]] = []
    seen: set[tuple[str, ...]] = set()
    for candidate in candidates:
        key = tuple(candidate)
        if key not in seen:
            unique.append(candidate)
            seen.add(key)
    return unique


def _resolve_watch_python_executable(
    *, runner: Callable[[list[str]], subprocess.CompletedProcess[str]] | None = None
) -> str | None:
    """Resolve a REAL python.exe path -- never `py.exe`, the Python Launcher.

    Review finding (T-20260926-212716751): Windows has no exec(), so
    launching the watcher via `["py", "-3", ...]` spawns py.exe as a WRAPPER
    process that itself spawns the real interpreter as ITS OWN child. The
    PID `subprocess.Popen` hands back is the launcher's, not the worker's --
    in a frozen build (`sys.executable` is the packaged host app, unusable
    as an interpreter, so `py -3` was the only remaining candidate),
    `stop_zombie_killer_watch` was signalling the launcher while the actual
    watcher kept running, unreachable, as an orphan.

    Not frozen: `sys.executable` already IS a real interpreter, used
    directly. Frozen: resolve the real path once via `-c "import sys;
    print(sys.executable)"` through each launcher candidate, so the actual
    watch subprocess is spawned directly against that resolved path.
    """
    if not getattr(sys, "frozen", False):
        return sys.executable
    run = runner or _run_install_command
    for candidate in (["py", "-3"], ["python3"], ["python"]):
        try:
            completed = run([*candidate, "-c", "import sys; print(sys.executable)"])
        except OSError:
            continue
        path = completed.stdout.strip() if completed.stdout else ""
        if completed.returncode == 0 and path and Path(path).is_file():
            return path
    return None


def _run_install_command(command: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command,
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )


def install_zombie_killer_package(
    *,
    target: str | None = None,
    runner: Callable[[list[str]], subprocess.CompletedProcess[str]] | None = None,
) -> ZombieKillerInstallResult:
    """Install or upgrade zombie-killer-tray via pip -- an explicit user action.

    Callable on any platform (pip will simply fail on a non-Windows box,
    since zombie-killer-tray itself requires Win32); `launch_zombie_killer_watch`
    is where the platform gate that actually matters lives.
    """
    chosen_target = target or zombie_killer_install_target()
    run = runner or _run_install_command
    attempts: list[ZombieKillerInstallResult] = []
    for pip_command in _pip_command_candidates():
        command = [*pip_command, "install", "--upgrade", chosen_target]
        try:
            completed = run(command)
        except OSError as exc:
            attempts.append(
                ZombieKillerInstallResult(
                    status="failed", target=chosen_target, command=command, message=str(exc)
                )
            )
            continue
        status = "ok" if completed.returncode == 0 else "failed"
        result = ZombieKillerInstallResult(
            status=status,
            target=chosen_target,
            command=command,
            message=(
                "zombie-killer-tray was installed or upgraded."
                if status == "ok"
                else f"pip exited with code {completed.returncode}."
            ),
            stdout=completed.stdout or "",
            stderr=completed.stderr or "",
        )
        if status == "ok":
            return result
        attempts.append(result)

    if attempts:
        last = attempts[-1]
        return ZombieKillerInstallResult(
            status="failed",
            target=chosen_target,
            command=last.command,
            message="zombie-killer-tray could not be installed.",
            stdout=last.stdout,
            stderr=last.stderr or last.message,
        )
    return ZombieKillerInstallResult(
        status="failed", target=chosen_target, command=[], message="No Python/pip command found."
    )


def _zombie_killer_env() -> dict[str, str]:
    env = os.environ.copy()
    local_source = _local_zombie_killer_source()
    if local_source is not None:
        src = str(local_source / "src")
        old_pythonpath = env.get("PYTHONPATH")
        env["PYTHONPATH"] = src if not old_pythonpath else src + os.pathsep + old_pythonpath
    return env


def _watch_pid_file(state_dir: Path) -> Path:
    return state_dir / "watch.pid"


def _write_watch_pid_file(state_dir: Path, pid: int, create_time: float | None) -> None:
    payload = {"pid": pid, "create_time": create_time}
    _watch_pid_file(state_dir).write_text(json.dumps(payload), encoding="utf-8")


def _read_watch_pid_file(state_dir: Path) -> tuple[int, float | None] | None:
    pid_file = _watch_pid_file(state_dir)
    if not pid_file.exists():
        return None
    try:
        payload = json.loads(pid_file.read_text(encoding="utf-8"))
        raw_create_time = payload.get("create_time")
        return (
            int(payload["pid"]),
            float(raw_create_time) if raw_create_time is not None else None,
        )
    except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError):
        return None


def _process_create_time(pid: int) -> float | None:
    try:
        import psutil
    except ImportError:
        return None
    try:
        return psutil.Process(pid).create_time()
    except psutil.Error:
        return None


def _verify_watch_process(pid: int, expected_create_time: float | None) -> bool | None:
    """True: `pid` is verifiably the same zombie-killer-tray watcher incarnation
    that was recorded. False: gone, or the PID was reused by something else.
    None: cannot verify at all (psutil unavailable or inaccessible) --
    callers MUST treat this as "do not touch" (review finding: `stop` used
    to fail-open on None, so a stale, verification-less PID file could
    terminate an unrelated process that happened to reuse the PID)."""
    try:
        import psutil
    except ImportError:
        return None
    try:
        proc = psutil.Process(pid)
        actual_create_time = proc.create_time()
        cmdline = " ".join(proc.cmdline())
    except psutil.Error:
        return False
    if expected_create_time is not None and abs(actual_create_time - expected_create_time) > 2.0:
        return False  # a different incarnation -- the pid was reused
    return "zombie_killer_tray" in cmdline


def launch_zombie_killer_watch(
    *,
    interval_seconds: int = DEFAULT_WATCH_INTERVAL_SECONDS,
    min_age_seconds: int = DEFAULT_MIN_AGE_SECONDS,
    apply: bool = True,
    popen: Callable[..., subprocess.Popen[str]] | None = None,
) -> ZombieKillerLaunchResult:
    """Start `python -m zombie_killer_tray watch` as its own, long-lived
    subprocess.

    Refuses cleanly on any non-Windows platform (zombie-killer-tray is
    Win32-only) rather than attempting a doomed subprocess spawn.

    `apply=False` starts in preview mode (no `--yes`): the watcher logs
    candidates but never terminates a real process. Defaults to `True` for
    production use; a caller that only wants to exercise the lifecycle
    (does the watcher survive, does stop work) MUST pass `apply=False` --
    otherwise the real subprocess can actually reap real, qualifying
    orphans on whatever machine runs it (review finding).

    NO `--parent-pid`: zombie-killer-tray kills the watch process as soon
    as whatever PID was passed via `--parent-pid` exits. A one-shot CLI
    call like `zombie-killer-watch` exits right after this function
    returns, so passing its own (thus already-doomed) PID there killed the
    watcher within ~1s of starting it. The watcher's lifecycle is instead
    tracked via its own PID file, independent of whoever launched it (see
    `stop_zombie_killer_watch`).

    Refuses a second start while the existing PID file describes a still-
    running (or unverifiable) watcher -- otherwise a second call overwrites
    `watch.pid` and the first watcher becomes unreachable (review finding).
    """
    state_dir = zombie_killer_state_dir()
    if not _is_windows():
        return ZombieKillerLaunchResult(
            status="unsupported-platform",
            command=[],
            message="zombie-killer-tray is Windows-only; skipped on this platform.",
            state_dir=str(state_dir),
        )

    existing = _read_watch_pid_file(state_dir)
    if existing is not None:
        existing_pid, existing_create_time = existing
        verified = _verify_watch_process(existing_pid, existing_create_time)
        if verified is not False:
            return ZombieKillerLaunchResult(
                status="already-running" if verified else "verification-unavailable",
                command=[],
                message=(
                    f"A watcher is already running (PID {existing_pid}); "
                    "use zombie-killer-stop to stop it."
                    if verified
                    else "Existing PID file cannot be verified (psutil missing?); "
                    "check before starting another one."
                ),
                state_dir=str(state_dir),
                pid=existing_pid,
            )
        _watch_pid_file(state_dir).unlink(missing_ok=True)  # stale/dead -- safe to clear

    python_executable = _resolve_watch_python_executable()
    if python_executable is None:
        return ZombieKillerLaunchResult(
            status="failed",
            command=[],
            message="No real Python interpreter found (the py.exe launcher is deliberately "
            "never used directly as the watch process, see _resolve_watch_python_executable).",
            state_dir=str(state_dir),
        )

    args = [
        "watch",
        *(["--yes"] if apply else []),
        "--interval", str(interval_seconds),
        "--min-age", str(min_age_seconds),
    ]
    command = [python_executable, "-m", "zombie_killer_tray", *args]
    env = _zombie_killer_env()
    run = popen or subprocess.Popen
    try:
        process = run(command, cwd=str(state_dir), env=env, close_fds=True, **no_window_kwargs())
    except OSError as exc:
        return ZombieKillerLaunchResult(
            status="failed", command=command, message=str(exc), state_dir=str(state_dir)
        )

    pid = getattr(process, "pid", None)
    pid_int = int(pid) if isinstance(pid, int) else None
    if pid_int is None:
        return ZombieKillerLaunchResult(
            status="failed",
            command=command,
            message="Subprocess returned no PID.",
            state_dir=str(state_dir),
        )
    _write_watch_pid_file(state_dir, pid_int, _process_create_time(pid_int))
    return ZombieKillerLaunchResult(
        status="ok",
        command=command,
        message="zombie-killer-tray was started as its own, long-lived watch subprocess.",
        state_dir=str(state_dir),
        pid=pid_int,
    )


def stop_zombie_killer_watch() -> ZombieKillerStopResult:
    """Stop the watch subprocess started by `launch_zombie_killer_watch`,
    identified via its PID file rather than any parent/child relationship."""
    state_dir = zombie_killer_state_dir()
    existing = _read_watch_pid_file(state_dir)
    if existing is None:
        return ZombieKillerStopResult(status="not-running", message="No PID file found.")
    pid, create_time = existing

    verified = _verify_watch_process(pid, create_time)
    if verified is None:
        # FAIL-CLOSED (review finding): cannot verify this PID is really our
        # watcher (psutil missing/inaccessible) -- refuse to touch it rather
        # than blindly signalling a possibly-unrelated, reused PID.
        return ZombieKillerStopResult(
            status="verification-unavailable",
            message="Cannot verify PID (psutil missing?); process was NOT stopped.",
            pid=pid,
        )
    if verified is False:
        _watch_pid_file(state_dir).unlink(missing_ok=True)
        return ZombieKillerStopResult(
            status="not-found", message="PID no longer belongs to zombie-killer-tray.", pid=pid
        )

    try:
        os.kill(pid, signal.SIGTERM)
    except OSError:
        _watch_pid_file(state_dir).unlink(missing_ok=True)
        return ZombieKillerStopResult(status="already-stopped", message="Process was not running.", pid=pid)

    _watch_pid_file(state_dir).unlink(missing_ok=True)
    return ZombieKillerStopResult(status="ok", message="zombie-killer-tray was stopped.", pid=pid)


def _last_cycle_event(state_dir: Path) -> dict[str, object] | None:
    events_path = state_dir / "zombie_events.jsonl"
    if not events_path.exists():
        return None
    last: dict[str, object] | None = None
    try:
        with events_path.open("r", encoding="utf-8", errors="replace") as handle:
            for line in handle:
                line = line.strip()
                if not line:
                    continue
                try:
                    record = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if isinstance(record, dict) and "cycle_at" in record:
                    last = record
    except OSError:
        return None
    return last


def build_zombie_killer_status() -> ZombieKillerStatus:
    state_dir = zombie_killer_state_dir()
    notes: list[str] = []
    supported = _is_windows()
    if not supported:
        notes.append("zombie-killer-tray is Windows-only; not applicable on this platform.")
    available = supported and _zombie_killer_importable()
    if supported and not available:
        notes.append("zombie-killer-tray package not importable; showing prior audit log if any.")

    last_cycle = _last_cycle_event(state_dir)
    return ZombieKillerStatus(
        available=available,
        supported_platform=supported,
        state_dir=str(state_dir),
        last_cycle_at=float(last_cycle["cycle_at"]) if last_cycle else None,
        last_cycle_count=int(last_cycle["count"]) if last_cycle and "count" in last_cycle else None,
        notes=notes,
    )
