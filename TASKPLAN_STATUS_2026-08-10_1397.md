# TASKPLAN-Status 2026-08-10 — Windows Live-Smoke #1397

**Rolle:** TASKSOLVER · **Projekt:** `C:\_Local_DEV\repos\safe-start-for-codex`

## Ergebnis

Task #1397 wurde nach einem reproduzierten Cleanup-Befund und einem minimalen
Fix als erledigt verifiziert. Der Store-Start wurde ausgeführt; keine
Automationsdatei, kein Lockfile und kein Prozess wurde durch den Smoke-Lauf
verändert oder beendet.

## Baseline und Umgebung

- Branch `main` war vor dem Code-Slice sauber und `origin/main` um vier lokale
  Commits voraus; Repository-Locks (`LOCK*.txt`, `.automation-lock`) wurden
  nicht gefunden.
- Die Windows-App `OpenAI.Codex_26.803.5235.0_x64__2p2nqsd0c76g0` ist installiert
  und `Status=Ok`. Ihr Manifest verwendet `Application Id=App` und
  `app/ChatGPT.exe`; der lokale Installationspfad
  `LOCALAPPDATA\Programs\Codex\Codex.exe` existiert nicht.
- Der relevante Startpfad ist daher der im Code hinterlegte
  `shell:appsFolder\OpenAI.Codex_2p2nqsd0c76g0!App`-AUMID-Fallback.

## Gefundener und behobener Fehler

Der erste AUMID-Lauf startete die Store-App korrekt, aber der Cleanup-Readback
nach 154 Sekunden meldete den laufenden Store-`codex.exe`-App-Server als
`zombie_pids`, weil die zugehörigen `ChatGPT.exe`-Host-/Renderer-Prozesse nicht
zur Codex-Familie gezählt wurden.

Der Fix in `src/safe_start_for_codex/cli.py` erkennt jetzt sowohl `ChatGPT.exe`
als auch `codex.exe` unter dem verifizierten `\\WindowsApps\\OpenAI.Codex`-Marker.
Zwei Regressionstests decken Matching und den aktiven Store-Cleanup-Fall ab.

## Live- und Testnachweis nach dem Fix

- `launch_codex(False, ...)` kehrte erfolgreich zurück und schrieb den AUMID-
  Event `launch_codex_appid` in das isolierte Test-`CODEX_HOME`.
- Danach waren die Store-Prozessfamilie mit `ChatGPT.exe`-Host/Renderern und
  `app\\resources\\codex.exe`-App-Server sichtbar.
- Der erneute Cleanup-Dry-Run meldete `renderer_present=true`,
  `zombie_pids=[]`, `killed_pids=[]`, `removed_lockfile=false` und keine
  Companion-Orphans. Meldung: aktiver Renderer, kein Main-Prozess beendet.
- `python -X utf8 -m pytest -q`: **47 bestanden**.
- `python -X utf8 -m pytest tests/source_platform_smoke.py -q -ra`:
  **11 bestanden**.
- `python -B -m compileall -q src tests` und CLI-Help bestanden.
- Ruff für den geänderten Code und `tests/test_cli.py` bestand. Der vollständige
  Repo-Lauf behält die zwei zuvor dokumentierten, nicht aufgabenbezogenen
  `F401`-Befunde in anderen Testdateien.

## Commit und Grenze

Der eigene Code-/Test-/Dokumentations-Slice wird in einem lokalen Commit
zurückgelesen. Es gab keinen Publish-, Remote-, Automations- oder destruktiven
Cleanup-Lauf. Der weiterhin laufende Store-Prozess wurde nicht beendet.

