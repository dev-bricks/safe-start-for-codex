# Changelog

All notable changes to this project are documented here.

## [1.1.4] - 2026-09-10

- Technical Hygiene, CI Compilation Gate, Standardized Pytest Flags & Contract Suite (GITHUBBOT_ONE_REPO_CLEANER / Pfad A) on 2026-09-10:
  - Bumped version to 1.1.4 across `pyproject.toml`, `src/safe_start_for_codex/__init__.py`, `README.md`, `README_de.md`, `RELEASES.md`, `MARKETING-LOG.txt`, and `llms.txt`.
  - Comprehensive `.gitignore` hardening against multi-host sync conflicts (`*-conflict-*`, `*.sync-conflict-*`, `*.conflict`, `*-CONFLIT-*`, `*.sync-temp-*`, `*-ASUS-GEI.*`, `*-WORKSTATION-LG.*`, `*-WORKSTATION.*`, `* (kopie)*`, `* (copy)*`), multi-agent locks (`LOCK`, `LOCK.*`, `*.lock`, `LOCK*.txt`, `LOCK.permissions.json`, `uv.lock`), coverage/packaging caches (`coverage/`, `htmlcov/`, `.coverage`, `.coverage.*`, `wheelhouse/`, `.wheel-smoke/`), and temporary editor files (`*.tmp`, `*.bak`, `*.swp`, `*~`, `*.log`).
  - Standardized pytest execution options in `pyproject.toml` with `addopts = "-ra -v"`.
  - Hardened GitHub Actions CI workflows (`.github/workflows/ci.yml` and `.github/workflows/source-platform-smoke.yml`) with automated bytecode compilation check (`python -m compileall -q src tests`) and standardized pytest execution (`pytest -ra -v`).
  - Expanded automated contract test suite in `tests/test_version_metadata.py` with 4 new contract tests (`test_gitignore_hygiene_patterns`, `test_pytest_configuration_and_flags`, `test_ci_workflow_pytest_flags`, `test_changelog_recent_pfad_a_entry`) to 91 passing tests (100% green).
  - Synchronized `llms.txt` verification timestamp (`2026-09-10`), version (`1.1.4`), and test suite count. [G 2026-09-10]
- Hardened startup cleanup lockfile supervision in `cleanup_start_blockers`:
  - Resolved false negative in dry-run mode (`--dry-run`) where stale lockfiles were not reported when zombie main processes were present.
  - Guarded lockfile unlinking during active cleanup runs to prevent deleting the lockfile when any Codex main process failed to terminate, preventing multi-instance concurrency collisions and data corruption.
  - Accurately flagged `CleanupResult.stale_lockfile` when all detected main processes are stale zombies.
  - Added dedicated regression tests for dry-run reporting, successful unlinking, and failure preservation (87/87 pytest tests passing 100% green). [G 2026-09-09]
- Hardened SafeStartGate Lifecycle & Recurrence Pacing Engine (SOFTWARE_BUGSEARCH Bugsweep) on 2026-09-11:
  - Made `SafeStartGate.release_item`, `SafeStartGate.restore`, and `SafeStartGate.pause_active` resilient against missing or moved automation files and transient `OSError` file mutations, preventing premature termination of the staggered release loop and avoiding permanent `PAUSED` deadlocks on remaining automations.
  - Enforced `allowed_days` (e.g. `BYDAY=MO,TU,WE,TH,FR`) in `rrule_occurrences_between` for `HOURLY` recurrences, preventing false weekend occurrences in catch-up report generation and incorrect early release queue prioritization.
  - Validated standard `FREQ` recurrence tokens in `rrule_next_after`, returning `None` for invalid or unknown recurrence rules and routing malformed tasks to safe fallback rather than synthesizing erroneous future execution timestamps.
  - Reused unified path resolution helper `resolve_automation_path` across `SafeStartGate` methods and `command_restore_latest`.
  - Added dedicated regression test suite in `tests/test_cli.py` covering missing file handling, partial failure recovery, RRULE token validation, and weekday-filtered hourly intervals (96/96 pytest tests passing 100% green). [G 2026-09-11]

- Discoverability, Visual Architecture, Governance Matrix & Contract Tests (GITHUBBOT_ONE_REPO_MARKETING_AND_DESIGN / Pfad B) on 2026-09-08:
  - Implemented standardized 14-point Quick Navigation (`🧭 Quick Navigation` / `🧭 Schnellnavigation`) across `README.md` and `README_de.md` with explicit functional anchor links and bilingual language switchers.
  - Added dual interactive Mermaid diagrams: System Architecture flowchart (`graph TB`) covering Control Interfaces, Gating Core, and Codex Target Environment, and an Execution Lifecycle sequence diagram (`sequenceDiagram`) detailing startup gating, atomic snapshot backups, zombie process supervision, and staggered background releases.
  - Formulated 10 Core Governance & Runtime Invariants Matrix (Local-First & Zero Egress, Non-Elevation, Snapshot-Before-Mutation, Selective Restoration Guard, Conservative Catch-Up Policy, Targeted Process Supervision, Atomic TOML Serialization, Fail-Closed Diagnostics, Dual-Platform Architecture, Ecosystem Parity).
  - Expanded Sibling Tools & Ecosystem Cross-Integration Matrix across 12 companion projects (`dev-bricks`, `ellmos-ai`, and `open-bricks`).
  - Hardened GitHub Actions CI (`.github/workflows/ci.yml`) with automated `pip` caching (`cache: 'pip'`).
  - Strengthened bilingual `SECURITY.md` with precise 48h acknowledgment and 5-business-day triage SLA commitments.
  - Expanded automated contract test suite in `tests/test_version_metadata.py` with tests for 14-point navigation anchors, dual Mermaid diagrams, governance invariants table, ecosystem cross-links, and security SLA commitments (84/84 pytest tests passing 100% green).
  - Synchronized Shields.io badges, `llms.txt`, and local `MARKETING-LOG.txt`. [G 2026-09-08]
- Technical Hygiene, Multi-OS CI Matrix & Contract Test Suite (GITHUBBOT_ONE_REPO_CLEANER / Pfad A) on 2026-08-24:
  - Hardened GitHub Actions CI workflows (`.github/workflows/ci.yml` and `.github/workflows/source-platform-smoke.yml`) with concurrency groups (`cancel-in-progress: true`), multi-version Python matrix testing (Python 3.11, 3.12, 3.13), and automated `ruff check .` linting gate before test execution.
  - Expanded `pyproject.toml` with PEP 621 classifiers (`Environment :: Console`, `Environment :: MacOS X`, `Environment :: X11 Applications`, `Operating System :: OS Independent`, `Operating System :: POSIX :: Linux`, `Operating System :: MacOS`, `Programming Language :: Python :: 3.13`, `Topic :: Desktop Environment`), `dev` dependencies (`ruff>=0.5.0`), and full `[project.urls]` (`Bug Tracker`, `Parent Organization`, `Umbrella Ecosystem`).
  - Enriched bilingual `SECURITY.md` with Supported Versions table (`1.1.x`) and full official security contacts (`security@ellmos.ai`, `security@open-bricks.org`, `support@lukasgeiger.com`, `lukas@open-bricks.org`).
  - Refreshed direct dependency license inventory `THIRD_PARTY_LICENSES.txt` with 2026-08-24 verification timestamp and `ruff` license metadata.
  - Expanded automated contract test suite in `tests/test_security_license_contract.py`, `tests/test_third_party_licenses.py`, and `tests/test_version_metadata.py` with CI concurrency, ruff lint gate, CLI parser subcommand registry, and README/README_de bilingual section parity validation (79/79 pytest tests passing 100% green).
  - Synchronized Shields.io test badges and `llms.txt` verification timestamp (`2026-08-24`). [G 2026-08-24]
- Technical Hygiene, Security & License Audit (SOFTWARE_SECURITY_LICENSE_AUDIT) on 2026-08-23:

  - Hardened dependency floors in `pyproject.toml` (`pytest>=9.1.1` to prevent GHSA-6w46-j5rx-g56g / CVE-2025-7117, `pystray>=0.19.5`) and expanded project URLs (`Documentation`, `Repository`, `Changelog`, `Security`).
  - Enriched bilingual `SECURITY.md` with official reporting guidelines, direct security contacts (`security@ellmos.ai`, `support@lukasgeiger.com`), local-first & zero-egress architecture guarantees, unprivileged user-mode execution, and non-destructive atomic file safeguards.
  - Updated `THIRD_PARTY_LICENSES.txt` with refreshed inventory timestamp (`2026-08-23`), hardened dependency constraints, and full transitive build/test package inventory (`altgraph`, `pyinstaller-hooks-contrib`, `pluggy`, `iniconfig`, `packaging`, `colorama`).
  - Strengthened `.gitignore` with sync conflict patterns (`*-WORKSTATION-LG*`, `*.conflict`, `*.sync-conflict-*`) and removed stale OneDrive conflict files.
  - Added comprehensive security & license contract test suite `tests/test_security_license_contract.py` verifying dependency vulnerability floors, license metadata, bilingual security policy, repo hygiene, PEP 621 URLs/classifiers, and zero plaintext secrets or hardcoded user paths (76/76 pytest tests passing 100% green). [G 2026-08-23]
- Fixed `rrule_next_after` and `_matches_frequency_day` for `FREQ=DAILY` and `FREQ=WEEKLY` with `INTERVAL > 1`: DAILY and WEEKLY recurrences are now properly evaluated with day-by-day frequency matching and Monday-aligned calendar weeks rather than skipping interval checks in the cursor loop or misaligning mid-week anchor intervals.
- Hardened `command_restore_latest` to evaluate automation `original_status` case-insensitively (supporting lowercase `"active"` TOML status) and added fallback path resolution via `automations_dir()`.
- Added regression tests for DAILY/WEEKLY intervals, calendar week alignment, and case-insensitive restore handling (70/70 pytest tests passing). [G 2026-08-21]


- Fixed recurrence calculation in `rrule_next_after` for `FREQ=MONTHLY` and `FREQ=YEARLY` so explicit `BYMONTHDAY` / `BYMONTH` rules and `dtstart` anchors are respected instead of incorrectly matching tomorrow or aborting at a 14-day limit.

- Handled missing automations directory in `command_backup` with a clear error message instead of raising unhandled `FileNotFoundError`.

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

- Discoverability, README-Design, Badges & Metadata Parity Check (Pfad B) on 2026-08-16: synchronized testsuite badge to 66 passed (55 unit/regression/metadata + 11 platform smoke), added version and ecosystem (`dev-bricks`, `open-bricks`) badges, added interactive bilingual Mermaid system architecture diagrams, expanded sibling tools ecosystem cross-references (`CareCenter-for-Codex`, `CodeBox`, `companion-for-agy`, `automation-master`, `WikiStub-Seed`, `MethodenAnalyser`), implemented automated metadata & manifest parity test suite (`tests/test_version_metadata.py`), added ruff configuration in `pyproject.toml`, and refreshed `llms.txt` verification timestamps and test counts. [G 2026-08-16]
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
