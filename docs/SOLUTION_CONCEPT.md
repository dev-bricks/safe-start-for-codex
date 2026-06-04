# Solution Concept

Safe Start for Codex is a conservative local gate around Codex Desktop startup.

## Goals

- Keep Codex Desktop responsive during startup.
- Avoid enabling every active automation at the same instant.
- Never enable an automation that was paused before the tool started.
- Keep enough state to recover after interruption.
- Avoid killing active Codex sessions that have a live renderer.

## Non-Goals

- It is not a scheduler replacement.
- It is not an official Codex API.
- It does not try to interpret every possible recurrence rule.
- It does not call Codex Desktop's manual "Run now" action.
- It does not publish binaries, shortcuts, or local desktop files.

## Local Algorithm

1. Scan `CODEX_HOME/automations/*/automation.toml`.
2. Record the original status of every automation.
3. Pause automations whose original status is `ACTIVE`.
4. Launch Codex Desktop.
5. Wait for a short startup delay.
6. Compute a release queue:
   - future-safe automations first,
   - rare missed automations first when catch-up prioritization is enabled,
   - near-due or unknown schedule automations later.
7. Release the first small batch.
8. Release one additional automation per interval.
9. On restore or quit, restore only automations that this tool paused.

## Startup Cleanup

The Windows cleanup step is guarded:

- If a Codex renderer is present, no main Codex process is terminated.
- Main processes without a renderer are considered stale only after an age threshold.
- Lockfiles are removed only when no live main process remains.
- Companion app-server processes are removed only when they match known Codex markers and exceed an age threshold.

## Recovery Model

Snapshots are written under `~/.codex/automation-safe-start`:

- `latest.json` contains the last known run state.
- phase-specific snapshots show pause, release queue, finished, and restored states.
- `events.jsonl` records actions for debugging.

The command below restores only automations marked as paused by this tool:

```powershell
safe-start-for-codex restore-latest
```

## Catch-Up Model

Safe Start can create a read-only catch-up plan for schedules whose effective period is greater
than 24 hours by default. It compares the latest due time with best-effort run history from
Codex state, using only thread titles and timestamps, not prompt bodies.

When `catchup_enabled` is true, up to `catchup_max_per_start` rare missed automations are moved
to the early release group. Safe Start still does not trigger a manual run. This avoids ambiguity
around whether the UI's "Run now" button counts as a scheduled occurrence and avoids accidentally
starting the same automation twice.

## Native Codex Direction

A native implementation should live inside the Codex scheduler instead of editing TOML files. The same policy could be represented internally as:

- startup grace period,
- catch-up queue,
- per-user catch-up limit,
- explicit last-run and in-flight state,
- manual-run semantics that cannot race scheduled runs,
- scheduler-level rate limiting,
- UI-visible pending automation work.
