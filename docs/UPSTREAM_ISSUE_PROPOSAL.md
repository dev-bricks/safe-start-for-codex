# Upstream Issue Proposal: Startup Catch-Up Storms for Codex Desktop Automations

This is a draft for an upstream issue in `openai/codex`. It is intentionally written as a problem report plus a product-level proposal, not as an unsolicited pull request.

## Title

Codex Desktop should rate-limit automation catch-up after startup and avoid stale-process startup blocks

## Problem

When Codex Desktop starts on Windows with many local automations enabled, all due or near-due automations can become eligible at once. In practice this can create a startup surge: the app opens, multiple automations attempt to resume or catch up, and the user loses control of the desktop session for a while.

Related startup friction can also appear when stale Codex/Electron state remains from a previous session:

- a Codex main process exists without a live renderer,
- a stale Electron lockfile remains,
- old companion/app-server processes remain after a previous CLI or desktop session.

The user-facing symptom is not one single bug. It is a startup reliability gap: too much deferred automation work becomes active at the same moment, exactly when the app is least stable.

## Expected Behavior

Codex Desktop should start into a responsive state first. Automation work should resume after startup using a bounded, inspectable policy.

Suggested expectations:

- Active automations remain logically active, but are internally gated during app bootstrap.
- Automations whose next scheduled time is in the future can resume first.
- Due or missed automations are rate-limited or surfaced as pending catch-up work.
- Users can see that automation catch-up is happening.
- Startup cleanup does not terminate an active session with a live renderer.

## Suggested Native Design

1. Add an internal startup grace period for automations.
2. Compute a release queue from automation schedules.
3. Immediately release only a small first batch whose next run is safely in the future.
4. Release the rest gradually with a default interval.
5. Treat missed runs as a catch-up queue instead of starting them all at once.
6. Expose the queue in the UI or logs.
7. Add guarded stale-process and lockfile recovery for Windows startup.

## Workaround Reference

This repository contains a local workaround:

- Repository: https://github.com/dev-bricks/safe-start-for-codex
- It pauses currently `ACTIVE` automations by editing local automation TOML files.
- It launches Codex Desktop.
- It releases a small first batch and then one automation per interval.
- It restores only automations it paused.
- It writes snapshots for recovery.

That approach is useful locally, but it should not be the long-term solution. A native Codex implementation would not need to mutate user-visible TOML files and could coordinate directly with the scheduler.

## Why This Matters

Automation is most useful when it is boring and predictable. Startup catch-up storms make users hesitate to keep automations enabled, especially when they rely on Codex Desktop for interactive work.
