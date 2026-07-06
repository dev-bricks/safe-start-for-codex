# Changelog

All notable changes to this project are documented here.

## [Unreleased]

### Security

- Raised the optional tray dependency floor for Pillow to `>=12.2.0` after OSV reported advisories for the previous `>=10.0` lower bound.

### Documentation

- Documented visible tray failure reporting and ignored local project lock files.
- Added README/README_de discovery context for exact `dev-bricks/safe-start-for-codex` search phrases and Codex Desktop startup-gate disambiguation.
- Added workflow badges and refreshed `llms.txt` with `Last-checked`, audience, search phrases, and source-platform smoke context.
- Standardized `llms.txt`: moved `Last-checked` to `## Last-checked:` header at line 1 (llms.txt format convention).
- Added `docs/superpowers/` to `.gitignore` (Claude Code plugin artifacts).

### Fixed

- Use the existing atomic JSON writer for `config-init` and catch-up plan state files, so interrupted writes do not leave partial local Safe Start state.
- Made tray worker `SystemExit` failures visible through the Safe Start event log and notifications instead of letting the background thread die silently.
- Made the windowed tray EXE leave startup-error logs under `C:\_Local_DEV\codex-safe-start\logs` instead of failing silently.
- Updated `build_exe.bat` to install and bundle PyStray/Pillow tray dependencies explicitly.

## [1.1.3] - 2026-06-10

### Added

- Cross-platform smoke tests (`tests/source_platform_smoke.py`) for rrule, config, TOML, and catchup logic on macOS and Linux.
- GitHub Actions workflow `source-platform-smoke.yml` running on ubuntu-latest and macos-latest.
- `PORTIERUNGSPLAN.md` documenting the Windows-first platform boundary.

### Fixed

- Fixed direct execution of `tray_app.py` so the windowed EXE entrypoint can import the package CLI without a parent package context.

## [1.1.2] - 2026-06-05

### Fixed

- Isolated the Windows EXE build from inherited `PYTHONPATH` entries and bundled the Safe Start icon.

## [1.1.1] - 2026-06-05

### Fixed

- Added a windowed tray entrypoint and reproducible `build_exe.bat` for the desktop shortcut EXE.

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
