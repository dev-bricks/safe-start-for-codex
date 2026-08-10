# Offene Befunde — safe-start-for-codex

**Erfasst am:** 2026-08-04
**Rolle:** MAINTAINER (GitHubBot Pfad A Hygiene)

---

### Befund 1: Arbeitskopie & Git-Status

- **Fundort:** Repository `C:\_Local_DEV\repos\safe-start-for-codex` (Branch `main`).
- **Beleg:**  
  `git status` war sauber (`main...origin/main`).
- **Status:** Dokumentation und Zeitstempel für Pfad A erneuert.

---

### Befund 2: Testsuiten-Status & Instandhaltung

- **Fundort:** `tests/` & `llms.txt`
- **Beleg:**  
  44 Pytest-Tests bestanden 100% grün (`python -m pytest -q`); der separate
  Source-Platform-Smoke-Lauf bestand mit 11 Tests (`python -m pytest
  tests/source_platform_smoke.py -q -ra`). `python -m compileall -q src tests`
  lief ohne Fehler.
- **Maßnahme:**  
`llms.txt` sowie die README-Prüfstände wurden im Pfad-A-Hygiene-Lauf vom
2026-08-04 aktualisiert.

---

### Befund 3: Aktueller MAINTAINER-Readback 2026-08-10

- **Fundort:** lokaler Plan-D-Clone `C:\_Local_DEV\repos\safe-start-for-codex`.
- **Git-Beleg:** Branch `main`, HEAD `4199591` (`docs: clarify unpushed source pin`),
  initial `main...origin/main [ahead 2]`; Arbeitsbaum und Root-Locks sauber. Der
  Vergleich nutzt den vorhandenen lokalen Remote-Ref; kein Fetch, Push, GitHub-Tag-
  Readback oder Release wurde ausgeführt.
- **Tests:** `python -X utf8 -m pytest -q` **45 bestanden**; der separate Lauf
  `python -X utf8 -m pytest tests/source_platform_smoke.py -q -ra` **11 bestanden**;
  `python -B -m compileall -q src tests` **bestanden**.
- **CLI-Smoke:** `PYTHONPATH=src python -m safe_start_for_codex --help` erfolgreich;
  kein Codex-Desktop-Start, kein Tray-Start und kein Zugriff auf das reale
  `CODEX_HOME`-Automationsverzeichnis.
- **Ruff:** 2 bestehende `F401`-Befunde in Testdateien (`pytest`, `json`); kein
  Cleanup in diesem Slice, weil die Tests bereits grün sind und die Änderung keinen
  funktionalen Maintainer-Gap schließt.
- **Doku:** README-Badge (45) und `llms.txt`-Angabe (45 + 11 Source-Smoke) stimmen
  mit dem frischen lokalen Lauf überein. Die dokumentierten Gates für CI-Readback,
  GitHub-Tag/Release und optionale Tray-EXE bleiben ohne Live-Nachweis offen.
- **Maßnahme:** Nur dieser Readback wurde ergänzt; keine Code-, Release-, Build- oder
  Nutzerdatenänderung.
