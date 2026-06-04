"""Windowed tray entrypoint for packaged Safe Start builds."""

from __future__ import annotations

from .cli import main


def run() -> int:
    return main(["tray"])


if __name__ == "__main__":
    raise SystemExit(run())
