# Contributing to Safe Start for Codex / Mitwirken an Safe Start for Codex

Welcome! We welcome contributions to `Safe Start for Codex` (Unofficial Windows startup gate for Codex Desktop automations and catch-up pacing from [dev-bricks](https://github.com/dev-bricks)). To preserve local-first process safety, non-destructive configuration gating, unprivileged execution, single-writer filesystem safety, and compliance across multi-host environments, all contributions must adhere to the quality standards and operational invariants defined below.

---

## English

### 1. General Principles & Quality Gates
1. **100% Local-First & Zero-Egress (`INV-LOCAL-01`)**: Core startup gating, configuration inspection, and scheduling operate strictly offline using standard libraries. Zero outbound network sockets, zero telemetry, and zero phone-home tracking. All state is host-local.
2. **Non-Elevation & Unprivileged User-Mode (`INV-SEC-02` / `RunAsInvoker`)**: All CLI commands, background daemons, system tray monitors, and test runners operate strictly within standard unprivileged user space. Administrative elevation (UAC/root/sudo) is strictly prohibited.
3. **Snapshot-Before-Mutation (`INV-FILE-03`)**: Before modifying any `automation.toml`, an atomic snapshot is preserved in `~/.codex/automation-safe-start/backups/`.
4. **Selective Restoration Guard (`INV-RESTORE-04`)**: Only automations paused by Safe Start in that active session are re-enabled upon release. Pre-existing disabled or paused automations remain untouched.
5. **Conservative Catch-Up Policy (`INV-CATCH-05`)**: Catch-up planning is strictly read-only and diagnostic; it never triggers manual "Run now" actions or forces immediate execution.
6. **Targeted Process Supervision (`INV-PROC-06`)**: Process supervision and termination are constrained to recognized Codex executable names (`ChatGPT.exe`, `codex.exe`) with conservative idle age thresholds.
7. **Atomic TOML Serialization (`INV-INTEG-07`)**: Configuration modifications use temporary staging files and atomic renames to prevent partial or corrupted file states on unexpected termination.
8. **Fail-Closed Diagnostics (`INV-FAIL-08`)**: Corrupted configurations or unhandled filesystem states log descriptive diagnostics and halt cleanly without mutating active configurations.
9. **Cross-Platform Operating Parity (`INV-PLAT-09`)**: Windows-targeted production execution accompanied by multi-OS source parsing smoke test suites across Linux and macOS.
10. **Dual Security Response SLA (`INV-SLA-10`)**: Strict commitment to 48-hour initial response and 5-business-day triage via canonical security channels ([SECURITY.md](SECURITY.md)).
11. **Version Freeze Discipline (`T-20260920-167562623`)**: Package version `1.1.6` is strictly frozen across `pyproject.toml`, source code, and all manifests. Do not bump the version string. Document all advancements under `## Unreleased` in `CHANGELOG.md`.
12. **Clean Code & Regression Testing**: Every feature or fix must include regression tests in `tests/`. Keep test coverage at a 100% pass rate.
13. **Bilingual Parity**: Maintain synchronized structural and navigational parity across `README.md` and `README_de.md` (18-point dual anchors `sec-01` through `sec-18`).

### 2. Local Development Workflow (Plan D)
```bash
# Clone the repository (canonical Plan D location)
git clone https://github.com/dev-bricks/safe-start-for-codex.git "C:\_Local_DEV\repos\safe-start-for-codex"
cd "C:\_Local_DEV\repos\safe-start-for-codex"

# Create virtual environment and install editable dev dependencies
python -m venv .venv
.venv\Scripts\python -m pip install -e ".[dev,tray]"

# Run comprehensive test suite
pytest -ra -v

# Run fast static code analysis
ruff check .

# Check bytecode compilation
python -m compileall -q src tests

# Check whitespace and git diff cleanliness
git diff --check

# Verify version freeze compliance (must return 0 matches)
git diff -G"version = "
```

### 3. Submission Protocol
- Open an issue for architectural discussions before large refactoring.
- Keep provider API keys, tokens, and private credentials strictly outside the repository. Never commit real personal data, `.env` files, private documents, or absolute host paths.
- Ensure all 10 governance invariants (`INV-LOCAL-01` to `INV-SLA-10`) remain VERIFIED.
- Pull requests must target the `main` branch.

### 4. License
By contributing to `Safe Start for Codex`, you agree that your contributions will be licensed under the [MIT License](LICENSE).

---

## Deutsch

### 1. Grundsätze & Qualitäts-Tore
1. **100% Local-First & Zero-Egress (`INV-LOCAL-01`)**: Das Kern-Startup-Gate, die Konfigurationsprüfung und die Zeitplanung arbeiten standardmäßig vollständig offline mit der Python-Standardbibliothek. Keine ausgehenden Netzwerk-Sockets, keine Telemetrie, kein Phone-Home. Der gesamte Status verbleibt host-lokal.
2. **Unprivilegierte Benutzer-Ausführung (`INV-SEC-02` / `RunAsInvoker`)**: Sämtliche CLI-Befehle, Hintergrund-Daemons, System-Tray-Monitore und Test-Runner laufen strikt im unprivilegierten Standard-Benutzerkontext. Administrative Rechte oder UAC-Elevationen sind verboten.
3. **Snapshot-Vor-Modifikation (`INV-FILE-03`)**: Vor jeder Änderung an einer `automation.toml` wird ein atomarer Snapshot unter `~/.codex/automation-safe-start/backups/` gesichert.
4. **Selektiver Wiederherstellungs-Schutz (`INV-RESTORE-04`)**: Nur Automatisierungen, die von Safe Start in dieser aktiven Sitzung pausiert wurden, werden bei der Freigabe reaktiviert. Zuvor deaktivierte oder pausierte Automatisierungen bleiben unberührt.
5. **Konservative Aufhol-Politik (`INV-CATCH-05`)**: Die Analyse verpasster Ausführungen ist rein lesend und diagnostisch; sie triggert niemals manuelle Sofortausführungen.
6. **Gezielte Prozessüberwachung (`INV-PROC-06`)**: Prozessüberwachung und Beendigung verwaister Instanzen sind strikt auf bekannte Codex-Prozessnamen (`ChatGPT.exe`, `codex.exe`) mit konservativen Altersgrenzen beschränkt.
7. **Atomare TOML-Serialisierung (`INV-INTEG-07`)**: Konfigurationsänderungen nutzen temporäre Staging-Dateien und atomare Umbenennungen, um korrupte Zustände bei plötzlichem Programmabbruch zu verhindern.
8. **Fail-Closed Diagnostik (`INV-FAIL-08`)**: Fehlerhafte Konfigurationen oder unerwartete Dateisystemzustände protokollieren aussagekräftige Fehlermeldungen und brechen sauber ab, ohne aktive Dateien zu verändern.
9. **Plattformübergreifende Betriebs-Parität (`INV-PLAT-09`)**: Primäre Windows-Produktionsausführung flankiert von Multi-OS Quelltext-Parsing Smoke-Tests unter Linux und macOS.
10. **Duale Sicherheits-SLA (`INV-SLA-10`)**: Verbindliche Zusage von 48h Reaktionszeit und 5 Werktagen Triage-Bewertung über kanonische Sicherheitskanäle ([SECURITY.md](SECURITY.md)).
11. **Version-Freeze-Disziplin (`T-20260920-167562623`)**: Paketversion `1.1.6` ist über alle Manifeste, Quelltexte und Badges hinweg strikt eingefroren. Kein Versions-Bump. Alle Weiterentwicklungen werden unter `## Unreleased` in `CHANGELOG.md` dokumentiert.
12. **Sauberer Code & Regressionstests**: Jede Änderung erfordert begleitende Tests in `tests/`. Die Testsuite muss zu 100% grün bleiben.
13. **Bilinguale Parität**: Strukturelle und navigatorische Parität zwischen `README.md` und `README_de.md` (18-Punkte Dual-Anker `sec-01` bis `sec-18`) ist zwingend einzuhalten.

### 2. Lokaler Entwicklungs-Workflow (Plan D)
```bash
# Klonen des Repositories (kanonischer Plan D Pfad)
git clone https://github.com/dev-bricks/safe-start-for-codex.git "C:\_Local_DEV\repos\safe-start-for-codex"
cd "C:\_Local_DEV\repos\safe-start-for-codex"

# Virtuelle Umgebung erstellen und Entwicklungsabhängigkeiten installieren
python -m venv .venv
.venv\Scripts\python -m pip install -e ".[dev,tray]"

# Testsuite ausführen
pytest -ra -v

# Schnelle statische Code-Prüfung ausführen
ruff check .

# Bytecode-Kompilierung validieren
python -m compileall -q src tests

# Whitespace und Git-Diff-Sauberkeit prüfen
git diff --check

# Einhaltung des Versions-Freezes validieren (muss 0 Treffer liefern)
git diff -G"version = "
```

### 3. Einreichungsprotokoll
- Bei größeren Refactorings bitte zuerst ein Issue für Architekturabstimmungen eröffnen.
- API-Schlüssel, Tokens und Zugangsdaten niemals im Repository ablegen. Keine echten persönlichen Daten, `.env`-Dateien oder absolute Host-Pfade committen.
- Sicherstellen, dass alle 10 Invarianten (`INV-LOCAL-01` bis `INV-SLA-10`) intakt bleiben.
- Pull-Requests müssen gegen den `main`-Branch gerichtet sein.

### 4. Lizenz
Mit Ihrer Mitwirkung an `Safe Start for Codex` erklären Sie sich damit einverstanden, dass Ihre Beiträge unter der [MIT-Lizenz](LICENSE) bereitgestellt werden.
