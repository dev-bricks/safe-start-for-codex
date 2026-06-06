"""Windowed tray entrypoint for packaged Safe Start builds."""

from __future__ import annotations

if __package__:
    from .cli import main
else:
    import sys
    from pathlib import Path

    package_dir = Path(__file__).resolve().parent
    for candidate in (package_dir.parent, package_dir):
        path = str(candidate)
        if path not in sys.path:
            sys.path.insert(0, path)

    from safe_start_for_codex.cli import main


def run() -> int:
    return main(["tray"])


if __name__ == "__main__":
    raise SystemExit(run())
