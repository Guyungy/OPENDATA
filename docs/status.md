# Status

## Current milestone

**Milestone focus:** Documentation and operating guidance hardening.

Implemented in this update:
- Added a formal roadmap in `docs/roadmap.md`.
- Added a reusable Codex task template and control prompt in `docs/codex-ops.md`.
- Linked development-loop docs from `README.md`.

## What changed

- The repository now includes explicit planning and execution guidance for
  long-horizon Codex work.
- Milestone boundaries, done criteria, and review-queue behavior are now
  documented in a single place.

## Validation status

- `pytest` must remain green after each milestone.
- Workspace artifacts should still be produced from sample inputs.

## Next tasks

1. Keep `docs/status.md` updated per completed milestone.
2. Add a JSON-schema-based validation report artifact for run outputs.
3. Expand governance acceptance checks into dedicated tests.
