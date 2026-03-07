# Status

## Current milestone

**Milestone focus:** P0-2 Review Queue (`governance/review_queue.json`).

Implemented in this update:
- Added workspace merge policy contract at `workspaces/<id>/config/merge_policy.json` with review controls for low-confidence entity merges, alias review, schema auto-promotion threshold, and placeholder relevance review.
- Added review queue artifact generation at `governance/review_queue.json` with required fields (`id`, `type`, `workspace_id`, `status`, `priority`, `target_ids`, `reason`, `supporting_artifacts`, `supporting_claims`, `confidence`, `suggested_action`, `created_at`, `updated_at`).
- Integrated review queue generation into canonical resolution (`entity_merge`, `alias`), conflict auditing (`conflict`), schema candidate handling (`schema_promotion`), and placeholder aging relevance (`placeholder_relevance`).
- Updated dashboard with a review summary panel and pending review counts by type.
- Regenerated sample workspace artifacts to include review queue and merge policy outputs.

## What changed

- Runtime now creates/loads per-workspace merge policy and records policy stage in trace.
- Low-confidence entity merge candidates can be held from canonical state and surfaced in review queue.
- Conflict detection now creates paired conflict review items.
- Schema candidates continue to persist to schema queue and now also emit schema promotion review items when below auto-promotion threshold.
- Unknown-type placeholders can emit placeholder relevance review items.

## Validation status

- `pytest` passes, including new behavior tests for low-confidence entity merge review routing, conflict review item generation, and schema candidate review routing.
- Sample pipeline run produces updated governance and dashboard artifacts with pending review counts.

## Next tasks

1. P0-3 Canonical Merge Policy enrichment with workspace-specific escalation paths and reviewer assignment metadata.
2. Add taxonomy candidate review routing and richer review lifecycle transitions (`in_review`, `resolved`, `rejected`).
3. Expand dashboard governance section with priority-segmented pending review trends.
