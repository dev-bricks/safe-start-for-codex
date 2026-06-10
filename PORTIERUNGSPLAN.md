# PORTIERUNGSPLAN — safe-start-for-codex

## Plattform-Strategie

**Windows-first:** safe-start-for-codex ist ein Windows-Startup-Gate für Codex Desktop.
Kernfunktionen (Prozess-Launch, Store-AUMID, Aufräumen von Start-Blockern) setzen
Windows-APIs voraus und sind explizit mit `if os.name != "nt"` abgesichert.

**macOS/Linux als Smoke-Ziele:** Die plattformneutralen Schichten (rrule-Parser, TOML-Scanner,
config.json-Verwaltung, Catchup-Planung) werden auf macOS und Linux kontinuierlich getestet
(`tests/source_platform_smoke.py`, Workflow `source-platform-smoke.yml`). Das sichert, dass
Imports, Datenmodelle und Berechnungen plattformübergreifend korrekt bleiben.

## Grenzen

| Schicht | Windows | macOS | Linux |
|---------|---------|-------|-------|
| rrule-Parser | ✓ | ✓ | ✓ |
| TOML-Scanner | ✓ | ✓ | ✓ |
| Config read/write | ✓ | ✓ | ✓ |
| Catchup-Bericht | ✓ | ✓ | ✓ |
| Tray-App (pystray) | ✓ | Nur mit Display | Nur mit Display |
| Prozess-Start (Codex.exe) | ✓ | — | — |
| Store-Start (AUMID) | ✓ | — | — |
| `cleanup_start_blockers` | ✓ | No-op | No-op |
| `SafeStartGate.run()` | ✓ | No-op | No-op |

## Tray auf Nicht-Windows

pystray funktioniert unter macOS (mit AppKit) und Linux (mit GTK/AppIndicator), benötigt
aber eine Display-Umgebung. Headless-CI führt keine Tray-Tests aus.

## Nicht geplant

- macOS/Linux Store-Integration
- Mobile, Browser, Flutter-Ports
