# Safe Start for Codex

Unofficial Windows startup gate for Codex Desktop automations.

![Safe Start for Codex Banner](assets/safe_start_banner.png)

[![Deutsch](https://img.shields.io/badge/lang-de-blue.svg)](README_de.md)
[![CI](https://github.com/dev-bricks/safe-start-for-codex/actions/workflows/ci.yml/badge.svg)](https://github.com/dev-bricks/safe-start-for-codex/actions/workflows/ci.yml)
[![Source Platform Smoke](https://github.com/dev-bricks/safe-start-for-codex/actions/workflows/source-platform-smoke.yml/badge.svg)](https://github.com/dev-bricks/safe-start-for-codex/actions/workflows/source-platform-smoke.yml)

Safe Start for Codex is a small Python utility for users who run many Codex Desktop automations and want to avoid a startup surge after opening the app. It temporarily pauses currently active local automations, launches Codex Desktop, then releases the paused automations in a controlled sequence.

This project is not affiliated with, endorsed by, or maintained by OpenAI.

The tray mode reports startup and background worker failures through local logs and desktop notifications, so configuration errors do not fail silently in the background.

## Who It Helps

Use Safe Start for Codex if you run Codex Desktop on Windows with many local recurring automations, reminders, monitors, or background checks and need a predictable startup path. The project is intentionally narrow: it is a local automation startup gate, not a replacement scheduler, cloud service, or Codex fork.

## What It Does

- Scans local Codex automation TOML files under `CODEX_HOME` or `~/.codex`.
- Pauses automations that were `ACTIVE` at tool start.
- Starts Codex Desktop on Windows.
- Releases a small first batch whose next schedule is safely in the future.
- Releases the remaining automations gradually.
- Restores only automations that this tool paused.
- Optionally removes stale Codex startup leftovers on Windows, such as old main processes without a renderer and stale lockfiles.
- Can generate a read-only catch-up plan for rare automations that appear to have missed a scheduled run.
- Includes Windows CI plus source-platform smoke checks for macOS and Linux parsing/config logic.

It does not activate automations that were already paused before the run.
It does not call Codex Desktop's manual "Run now" action.

## Safety Notice

This is a workaround around local Codex Desktop automation behavior. It edits files in `~/.codex/automations/*/automation.toml`, creates snapshots under `~/.codex/automation-safe-start`, and may terminate stale Codex-related Windows processes during startup cleanup.

Run a dry run first:

```powershell
safe-start-for-codex dry-run
```

Create a backup before first real use:

```powershell
safe-start-for-codex backup
```

## Installation

From a clone:

```powershell
python -m pip install -e .
```

For the optional tray mode:

```powershell
python -m pip install -e ".[tray]"
```

## Usage

| Command | Description |
|---|---|
| `safe-start-for-codex dry-run` | Simulates scanning and gating without changing files. |
| `safe-start-for-codex backup` | Creates a backup snapshot of active configurations. |
| `safe-start-for-codex start` | Launches Codex Desktop and gates automations in the foreground. |
| `safe-start-for-codex tray` | Launches as a background tray application in the Windows system tray. |
| `safe-start-for-codex status` | Prints the current state of gated automations. |
| `safe-start-for-codex config-init` | Generates a default `config.json` configuration file. |
| `safe-start-for-codex config-show` | Displays the currently active configuration. |
| `safe-start-for-codex catchup-plan` | Lists missed runs for rare/infrequent automations. |
| `safe-start-for-codex restore-latest` | Forces restoration of the latest paused automations. |

## Configuration

By default, Safe Start reads:

```text
~/.codex/automation-safe-start/config.json
```

Example:

```json
{
  "initial_release": 3,
  "interval_minutes": 5,
  "startup_delay_seconds": 45,
  "min_future_lead_minutes": 2,
  "launch": true,
  "cleanup": true,
  "catchup_enabled": false,
  "catchup_lookback_days": 30,
  "catchup_max_per_start": 1,
  "catchup_min_period_hours": 24
}
```

`initial_release`, `interval_minutes`, and `startup_delay_seconds` control how many automations are re-enabled at startup, how long Safe Start waits between later releases, and how long it waits after launching Codex. Command-line flags override the JSON config for that run.

When `catchup_enabled` is true, Safe Start creates a best-effort catch-up report and prioritizes up to `catchup_max_per_start` rare missed automations for early release. The threshold is controlled by `catchup_min_period_hours`; the default only considers schedules rarer than daily. The feature is intentionally conservative: it reads schedule metadata and thread titles/timestamps, but it does not trigger Codex's manual run action.

## Upstream Proposal

The workaround exists because the underlying behavior is better solved inside Codex itself. See:

- [Upstream issue draft](docs/UPSTREAM_ISSUE_PROPOSAL.md)
- [Solution concept](docs/SOLUTION_CONCEPT.md)

In short: Codex Desktop could include a native startup catch-up policy, a rate-limited automation release gate, clearer run-state semantics, and safer startup cleanup for stale app processes.

## Discovery Context

Search phrases that describe this repository precisely:

```text
safe-start-for-codex
Safe Start for Codex
Codex Desktop automation startup gate
Codex Desktop automation surge prevention
Windows Codex automation scheduler guard
local Codex automation catch-up planner
```

The exact repository path is `dev-bricks/safe-start-for-codex`. Broad searches for "Codex startup" or "automation gate" often collide with general OpenAI Codex tutorials, sandboxing articles, and unrelated GitHub projects.

## Deutsche Kurzfassung

Safe Start for Codex ist ein inoffizieller Windows-Workaround gegen Automations-Nachholwellen beim Start von Codex Desktop. Bitte zuerst `dry-run` ausführen und beachten, dass das Tool lokale Automationsdateien unter `~/.codex` verändert.

## Development

```powershell
python -m pip install -e ".[dev]"
pytest
```

Build the windowed tray EXE:

```powershell
.\build_exe.bat
```

## License

MIT License. See [LICENSE](LICENSE).
