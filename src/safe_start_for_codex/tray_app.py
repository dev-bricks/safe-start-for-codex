"""Windowed tray entrypoint for packaged Safe Start builds."""

from __future__ import annotations

import os
import sys
import traceback
from datetime import datetime
from pathlib import Path

main = None


def _load_main():
    global main
    if main is not None:
        return main
    if __package__:
        from .cli import main as cli_main
    else:
        package_dir = Path(__file__).resolve().parent
        for candidate in (package_dir.parent, package_dir):
            path = str(candidate)
            if path not in sys.path:
                sys.path.insert(0, path)

        from safe_start_for_codex.cli import main as cli_main
    main = cli_main
    return cli_main


def _log_startup_error(message: str) -> None:
    log_root = Path(os.environ.get("SAFE_START_LOG_DIR") or r"C:\_Local_DEV\codex-safe-start\logs")
    try:
        log_root.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        (log_root / f"startup-error-{stamp}.txt").write_text(message, encoding="utf-8")
    except OSError:
        pass

def run() -> int:
    try:
        code = int(_load_main()(["tray"]))
    except BaseException:  # noqa: BLE001 - windowed EXEs need a visible breadcrumb.
        _log_startup_error(traceback.format_exc())
        return 1
    if code:
        _log_startup_error(f"Safe Start tray command exited with code {code}.")
    return code


if __name__ == "__main__":
    raise SystemExit(run())
