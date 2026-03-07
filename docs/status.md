# Status

## Current milestone

**Milestone focus:** P1-1 Identity / Alias Memory Layer.

Implemented in this update:
- Added canonical alias memory artifact at `canonical/alias_map.json` with canonical entity keyed alias entries (`canonical_entity_id`, `canonical_name`, `aliases`, `source_refs`, `confidence`, `updated_at`).
- Added identity hypothesis artifact at `governance/identity_candidates.json` with lifecycle statuses (`pending|accepted|rejected|deferred`) and evidence-backed candidate links.
- Added explicit merge-block memory artifact at `governance/merge_blocks.json` for rejected identity decisions and retry suppression.
- Updated canonical merge resolution to consult alias memory and merge blocks before auto-merge, and to emit unresolved identity candidates when ambiguity remains.
- Updated review decision application to feed accepted/rejected `entity_merge` and `alias` outcomes back into alias map, identity candidates, and merge blocks.
- Extended dashboard summaries with identity memory counts and recent identity decision context.
- Regenerated sample workspace artifacts and applied identity-affecting review decisions to validate persisted feedback loop behavior.

## Validation status

- `PYTHONPATH=src pytest -q` passes, including identity memory behavior tests for:
  - accepted alias updating alias map,
  - rejected entity merge creating merge-block memory,
  - unresolved ambiguity producing identity candidates,
  - alias map reuse in later run resolution,
  - merge-block driven downgrade from auto-merge to review.
- Sample pipeline and review loop run completed on `workspaces/sample` with updated identity artifacts and dashboard summary sections.

## Next tasks

1. Add stable identity-candidate correlation keys across reruns to reduce duplicate hypotheses.
2. Add richer reviewer-facing merge-block rationale templates for faster adjudication.
3. Add trend views for identity memory growth/closure across snapshots.
