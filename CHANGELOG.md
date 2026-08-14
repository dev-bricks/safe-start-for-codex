# Changelog

All notable changes to this project are documented here.

## [Unreleased]

### Fixed

- Windows Store installations now classify both the `ChatGPT.exe` host and
  child `codex.exe` app-server as one Codex process family. Startup cleanup no
  longer proposes terminating the live Store app-server after the zombie age
  threshold when a renderer is active.

- Source Platform Smoke now installs the `tray` extra on Linux and macOS. The
  tray test mocks `pystray` but draws the fallback icon for real, so Pillow has
  to be present; without it `command_tray` returned 1 and the workflow had been
  red on every push since 2026-08-01.

- Kept `status` readable when a historical Safe Start snapshot exists but the
  configured Codex home has no automations directory yet: the command now
  prints the snapshot plus a clear unavailable-state message and exits with
  code 1 instead of propagating `SystemExit`.

### Documentation & Hygiene

- Technical Hygiene & Maintenance Check (Pfad A) on 2026-08-14: configured pytest discovery for cross-platform smoke tests in `pyproject.toml` (58/58 passed), resolved ruff unused import diagnostics, added sys.path fallback for standalone smoke test script execution, and refreshed README/README_de/`llms.txt` verification status and timestamps. [G 2026-08-14]
- SOFTWARE GITHUB check on 2026-08-12: stopped tracking internal maintainer
  artefacts (`BEFUNDE.md`, `TASKPLAN_STATUS_*.md`), hardened `.gitignore` for
  local verification files, and refreshed README/README_de/`llms.txt` plus the
  Plan-D/release pointer documents after a clean verification run.
- SOFTWARE GITHUB check on 2026-08-07: fast-forwarded the verified local
  Plan-D clone to `origin/main`, refreshed README/README_de/`llms.txt`
  verification timestamps and pytest badge counts (45 unit tests, 11 source
  platform smoke tests), and updated `PLAN_D_POINTER.md` plus `RELEASES.md`
  to the current HEAD/tag-readback state.
- Technical Hygiene & Maintenance Check (Pfad A) on 2026-08-04: refreshed `llms.txt` and README timestamps (`2026-08-04`), verified full unit test suite (44 passed) and source-platform smoke test suite (11 passed, total 55/55 passed 100% green), verified `compileall`. [G 2026-08-04]
- Maintainer verification on 2026-08-01 passed the full suite (44 tests), the
  separate source-platform smoke suite (11 tests), and `compileall`; refreshed
  verification dates in the README files and `llms.txt`, and advanced the
  Plan-D pointer to the current synchronized `main` HEAD. No code or release
  artifact was changed.
- Refreshed `llms.txt` header (`Last-checked: 2026-07-30`), added `open-bricks` ecosystem badges to `README.md` and `README_de.md`, and verified 44 passing pytest tests. [G 2026-07-30]
- Conducted Path B Discoverability & SEO audit, added ecosystem cross-links (`CareCenter-for-Codex`, `CodeBox`, `companion-for-agy`, `ellmos-filecommander-mcp`) and verification timestamps to `README.md` and `README_de.md`.
- Refreshed `llms.txt` header (`Last-checked: 2026-07-26`) and verified 44 passing pytest test suite execution.
- Added Mermaid system flow diagrams to `README.md` and `README_de.md`.
- Added Shields.io status badges and AI/LLM integration callouts (`> [!NOTE]`) to `README.md` and `README_de.md`.


### Security

- Raised the optional tray dependency floor for Pillow to `>=12.2.0` after OSV reported advisories for the previous `>=10.0` lower bound.

### Documentation

- Technical hygiene audit: verified test suite (36/36 passed), updated `llms.txt` `Last-checked` timestamp to 2026-07-25, tracked `PLAN_D_POINTER.md` asset inventory documentation.
- Added `THIRD_PARTY_LICENSES.txt` for direct build, tray, and development
  dependency license metadata.
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
- Made tray status text clearer when nothing is currently gated or when all gated automations have already been released, so users do not see confusing `0/0` progress wording.

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
