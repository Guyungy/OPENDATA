# Status

## Current milestone

**Milestone focus:** P0-1 Workspace Intent layer.

Implemented in this update:
- Added workspace intent contract at `workspaces/<id>/config/intent.json` with required fields (`goal`, `focus`, `ignore`, `preferred_entity_types`, `preferred_relation_types`, `report_preferences`).
- Loaded intent in runtime and propagated it into extraction, canonical merge context, and dashboard/report output.
- Updated sample workspace with `workspaces/sample/config/intent.json`.
- Added behavior test that the same source yields different canonical relation outputs under different workspace intents.

## What changed

- Runtime now creates/loads per-workspace intent and records intent stage in trace.
- Extraction applies intent focus/ignore filters and preferred entity/relation type guidance.
- Canonical entities now include explicit `intent_alignment` metadata.
- Dashboard includes workspace intent summary panel when report preference is enabled.

## Validation status

- `pytest` passes with intent-aware artifact assertions and behavior checks.
- Sample pipeline run produces intent-aware outputs in canonical and reports artifacts.

## Next tasks

1. P0-2 Review Queue (`governance/review_queue.json`) and dashboard pending-review counts.
2. P0-3 Canonical Merge Policy (`config/merge_policy.json`) with workspace overrides.
3. Extend governance behavior tests to assert review-required gating paths.
