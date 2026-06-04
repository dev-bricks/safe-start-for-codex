# Safe Start for Codex

Unofficial Windows startup gate for Codex Desktop automations.

Safe Start for Codex is a small Python utility for users who run many Codex Desktop automations and want to avoid a startup surge after opening the app. It temporarily pauses currently active local automations, launches Codex Desktop, then releases the paused automations in a controlled sequence.

This project is not affiliated with, endorsed by, or maintained by OpenAI.

## What It Does

- Scans local Codex automation TOML files under `CODEX_HOME` or `~/.codex`.
- Pauses automations that were `ACTIVE` at tool start.
- Starts Codex Desktop on Windows.
- Releases a small first batch whose next schedule is safely in the future.
- Releases the remaining automations gradually.
- Restores only automations that this tool paused.
- Optionally removes stale Codex startup leftovers on Windows, such as old main processes without a renderer and stale lockfiles.

It does not activate automations that were already paused before the run.

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

Dry run:

```powershell
safe-start-for-codex dry-run
```

Start Codex and gate automations in the foreground:

```powershell
safe-start-for-codex start
```

Run as a tray app:

```powershell
safe-start-for-codex tray
```

Show current status:

```powershell
safe-start-for-codex status
```

Restore the latest tool-paused automations:

```powershell
safe-start-for-codex restore-latest
```

## Upstream Proposal

The workaround exists because the underlying behavior is better solved inside Codex itself. See:

- [Upstream issue draft](docs/UPSTREAM_ISSUE_PROPOSAL.md)
- [Solution concept](docs/SOLUTION_CONCEPT.md)

In short: Codex Desktop could include a native startup catch-up policy, a rate-limited automation release gate, and safer startup cleanup for stale app processes.

## Deutsche Kurzfassung

Safe Start for Codex ist ein inoffizieller Windows-Workaround gegen Automations-Nachholwellen beim Start von Codex Desktop. Bitte zuerst `dry-run` ausführen und beachten, dass das Tool lokale Automationsdateien unter `~/.codex` verändert.

## Development

```powershell
python -m pip install -e ".[dev]"
pytest
```

## License

MIT License. See [LICENSE](LICENSE).
