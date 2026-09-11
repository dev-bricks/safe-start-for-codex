# Third-Party Licenses & Transparency Notice

> **Project:** `dev-bricks/safe-start-for-codex`  
> **Audited:** 2026-09-11  
> **Repository License:** [MIT License](LICENSE)  
> **Architecture & Privacy:** 100% Local-First, Zero-Egress, Unprivileged User-Mode (`RunAsInvoker`), Pure Python Standard Library Core

---

## Executive Summary & Compliance Assurance

`safe-start-for-codex` is engineered under strict architectural and governance invariants: **100% Local-First, Zero-Egress by default, unprivileged user-mode execution (`RunAsInvoker`), and non-destructive configuration gating**. The core automation scanner, configuration parser, pre-boot gating mechanism, snapshot manager, and staggered release scheduler operate completely within local filesystem boundaries without any unsolicited external network communication, telemetry, or remote telemetry.

All direct, runtime, optional, and development dependencies utilized across `safe-start-for-codex` are distributed under strictly **permissive and free open-source licenses** (MIT, Apache-2.0, PSFL, LGPLv3, GPLv2-with-PyInstaller-exception). There are **zero AGPL or proprietary restrictive copyleft constraints**, ensuring maximum portability for local developer desktop environments, multi-agent automated orchestration, and enterprise workstations.

Furthermore, `safe-start-for-codex` guarantees:
1. **100% Local-First & Zero Egress (INV-LOCAL-01):** Core startup gating, configuration inspection, and scheduling execute completely offline with zero telemetry and zero external network calls.
2. **Unprivileged User-Mode (`RunAsInvoker` / INV-SEC-02):** The utility runs strictly with standard user permissions. It never requests or requires UAC or administrative privilege elevation.
3. **Snapshot-Before-Mutation (INV-FILE-03):** An atomic configuration backup is persisted under `~/.codex/automation-safe-start/backups/` before any automation TOML file is altered.
4. **Selective Restoration Guard (INV-RESTORE-04):** Only automations paused by Safe Start in that active session are re-enabled; pre-existing disabled or paused automations remain untouched.
5. **Conservative Catch-Up Policy (INV-CATCH-05):** Missed execution analysis is strictly read-only; it never triggers manual "Run now" actions or forces sudden execution.
6. **Targeted Process Supervision (INV-PROC-06):** Stale process termination is strictly constrained to recognized Codex desktop process names (`ChatGPT.exe`, `codex.exe`) with conservative idle age thresholds.
7. **Atomic TOML Serialization (INV-INTEG-07):** Configuration modifications use temporary staging files and atomic renames to prevent partial or corrupted file states.
8. **Fail-Closed Diagnostics (INV-FAIL-08):** Corrupted configurations or unhandled filesystem states log descriptive diagnostics and halt cleanly without mutating active configurations.
9. **Cross-Platform Operating Parity (INV-PLAT-09):** Windows-targeted production execution accompanied by multi-OS source parsing smoke test suites across Linux and macOS.
10. **Dual Security Response & Triage SLA (INV-SLA-10):** Strict 48-hour acknowledgment and 5-business-day triage commitment via canonical security reporting channels (`security@open-bricks.org`, `security@dev-bricks.org`, `security@ellmos.ai`).

---

## Runtime Dependency Matrix

The core runtime of `safe-start-for-codex` has **zero external runtime dependencies** (`dependencies = []` in `pyproject.toml`).

| Package | Role / Functional Scope | License | Project Repository / Upstream |
|:---|:---|:---|:---|
| **Python Standard Library** | Core CLI, file I/O, TOML/JSON parsing, subprocess management, datetime/rrule calculation, atomic file operations | [PSFL-2.0](https://docs.python.org/3/license.html) | [python/cpython](https://github.com/python/cpython) |

---

## Optional Runtime Dependencies (System Tray & Desktop UI)

| Package | Constraint | Usage & Purpose | License | Source / Upstream |
|:---|:---:|:---|:---|:---|
| **Pillow** | `>=12.2.0` | Optional image handling and icon rendering for the Windows system tray application | [MIT-CMU / HPND](https://github.com/python-pillow/Pillow/blob/main/LICENSE) | [python-pillow/Pillow](https://github.com/python-pillow/Pillow) |
| **pystray** | `>=0.19.5` | Optional Windows system tray icon and background notification integration | [LGPLv3](https://github.com/moses-palmer/pystray/blob/master/COPYING) | [moses-palmer/pystray](https://github.com/moses-palmer/pystray) |

*Note on LGPLv3:* `pystray` is an optional dependency dynamically loaded in user space when running `safe-start-for-codex tray`. It is not linked statically and the base CLI operates with zero external dependencies.

---

## Direct Development, Build & Quality Assurance Tooling

| Package | Constraint | Usage & Purpose | License | Source / Upstream |
|:---|:---:|:---|:---|:---|
| **hatchling** | `>=1.24` | Modern PEP 517/621 build backend and wheel packaging | [MIT](https://github.com/pypa/hatch/blob/master/LICENSE.txt) | [pypa/hatch](https://github.com/pypa/hatch) |
| **pytest** | `>=9.1.1` | Automated test runner, contract verification suites, mock fixtures | [MIT](https://github.com/pytest-dev/pytest/blob/main/LICENSE) | [pytest-dev/pytest](https://github.com/pytest-dev/pytest) |
| **ruff** | `>=0.5.0` | High-performance Python linter and code formatting enforcement | [MIT / Apache-2.0](https://github.com/astral-sh/ruff/blob/main/LICENSE-MIT) | [astral-sh/ruff](https://github.com/astral-sh/ruff) |
| **PyInstaller** | `>=6.0` | Optional standalone Windows executable builder (`build_exe.bat`) | [GPLv2-or-later with Special Exception](https://github.com/pyinstaller/pyinstaller/blob/develop/COPYING.txt) | [pyinstaller/pyinstaller](https://github.com/pyinstaller/pyinstaller) |

---

## Transitive Build & Test Inventory

| Package | Used By | Version Checked | License | Source |
|:---|:---|:---:|:---|:---|
| **altgraph** | PyInstaller | 0.17.5 | MIT | https://pypi.org/project/altgraph/ |
| **pyinstaller-hooks-contrib** | PyInstaller | 2026.6 | Apache-2.0 | https://pypi.org/project/pyinstaller-hooks-contrib/ |
| **pluggy** | pytest | 1.6.0 | MIT | https://pypi.org/project/pluggy/ |
| **iniconfig** | pytest | 2.3.0 | MIT | https://pypi.org/project/iniconfig/ |
| **packaging** | pytest / build | 26.2 | Apache-2.0 / BSD-2-Clause | https://pypi.org/project/packaging/ |
| **colorama** | pytest / CLI | 0.4.6 | BSD-3-Clause | https://pypi.org/project/colorama/ |

---

## Distribution Notes & Compliance Verification

- Installing the base package via `pip install safe-start-for-codex` installs zero third-party packages.
- The optional `tray` extra installs `pystray` and `Pillow`. On macOS and Linux, `pystray` may declare platform-specific transitive packages (`pyobjc` / `python-xlib`).
- The optional `build` extra uses PyInstaller. PyInstaller's license includes a special exception explicitly authorizing the distribution of standalone binaries built by the tool under terms of the developer's choice.
- Binary release workflows inspect the bundled artifact set and ensure corresponding license notices are packaged.
