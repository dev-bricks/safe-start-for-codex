# Safe Start for Codex — Releases

Stand: 2026-06-18
Aktueller veröffentlichter Tag: `v1.1.3`
Release-Modell: Open Source frei

## Release-Anker

- Kanonischer Release-Anker ist GitHub: `dev-bricks/safe-start-for-codex`
- Versionierung läuft über `pyproject.toml` und `CHANGELOG.md`
- `CHANGELOG.md` führt zusätzlich einen `Unreleased`-Block für den nächsten Tag

## Aktueller Release-Workflow

### GitHub

- Source-Stand und Tags werden über das öffentliche GitHub-Repo veröffentlicht.
- Der aktuelle dokumentierte Release-Stand ist `v1.1.3` vom 2026-06-10.

### Lokales Windows-Komfortartefakt

- Die optionale Tray-EXE wird lokal über `build_exe.bat` gebaut.
- Ausgabeziel: `C:\_Local_DEV\codex-safe-start\bin\CodexSafeStart.exe`
- Build-Arbeitsverzeichnisse:
  - `C:\_Local_DEV\codex_build\safe-start-for-codex`
  - `C:\_Local_DEV\codex_build\safe-start-for-codex-spec`
- Diese Build-Artefakte bleiben bewusst außerhalb des Repos.

## Versionsübersicht

| Version | Datum | Kanal | Hinweis |
|---|---|---|---|
| `v1.1.3` | 2026-06-10 | GitHub | Source-Platform-Smokes und Portierungsplan ergänzt |
| `v1.1.2` | 2026-06-05 | GitHub | EXE-Build gegen geerbte `PYTHONPATH`-Einflüsse isoliert |
| `v1.1.1` | 2026-06-05 | GitHub | Windowed-Tray-Entrypoint und reproduzierbares `build_exe.bat` ergänzt |
| `v1.1.0` | 2026-06-04 | GitHub | `config.json`, Catch-up-Plan und konfigurierbare Release-Steuerung |
| `v1.0.0` | 2026-06-04 | GitHub | Initiales öffentliches Source-Release |

## Release-Checkliste

- `pyproject.toml`-Version und `CHANGELOG.md` synchronisieren
- `pytest` ausführen
- Optional: `build_exe.bat` für die lokale Tray-EXE ausführen
- Git-Tag und GitHub-Release veröffentlichen
- Diese Datei aktualisieren, wenn sich Release-Kanal oder Artefaktpfade ändern
