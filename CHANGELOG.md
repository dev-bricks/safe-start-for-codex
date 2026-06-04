# Changelog

All notable changes to this project are documented here.

## [1.1.0] - 2026-06-04

### Added

- `config.json` support with `config-init` and `config-show` commands.
- Configurable startup release count, release interval, startup delay, launch, cleanup, and catch-up settings.
- Read-only `catchup-plan` command for rare schedules that appear to have missed a due run.
- Optional catch-up prioritization during Safe Start runs, without triggering Codex Desktop's manual "Run now" action.

## [1.0.0] - 2026-06-04

### Added

- Initial public source release.
- Windows startup gate for local Codex Desktop automations.
- Dry-run, status, backup, restore, foreground, and tray commands.
- Upstream issue draft and solution concept.
- Test coverage for TOML status changes and recurrence queue behavior.
