# Comment Draft for openai/codex#24327

This seems closely related to the missed-run catch-up behavior discussed here, with one additional startup-specific failure mode: when Codex Desktop starts on Windows with many local automations enabled, due or near-due work can become eligible at the same moment the app is still bootstrapping. The result can feel like a startup catch-up storm.

I published a small unofficial workaround here:

https://github.com/dev-bricks/safe-start-for-codex

The workaround is intentionally conservative:

- pause only automations that were `ACTIVE` at tool start,
- launch Codex Desktop,
- release a small first batch whose next scheduled time is safely in the future,
- release the remaining automations gradually,
- restore only automations that the tool itself paused,
- avoid terminating Codex sessions that still have a live renderer.

This is not meant as the long-term design. A native Codex solution could avoid editing TOML files and instead implement this inside the scheduler:

- startup grace period for automations,
- catch-up queue instead of immediate all-at-once execution,
- per-user catch-up/rate limits,
- UI-visible pending automation work,
- guarded Windows stale-process and lockfile recovery.

More detailed notes:

- Upstream issue proposal: https://github.com/dev-bricks/safe-start-for-codex/blob/main/docs/UPSTREAM_ISSUE_PROPOSAL.md
- Solution concept: https://github.com/dev-bricks/safe-start-for-codex/blob/main/docs/SOLUTION_CONCEPT.md
