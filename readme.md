# MindVault

MindVault is an AI-first, artifact-driven knowledge operating system.

This repository implements a runnable incremental pipeline that separates:
- `raw` (immutable source records)
- `extracted` (claims and candidates)
- `canonical` (resolved entities/relations/events/insights/schema/taxonomy/ontology)
- `governance` (conflicts/placeholders/schema queue/taxonomy candidates/review queue/review decisions/confidence)

## Quick start

```bash
python -m mindvault run --workspace workspaces/sample --input-dir sample_data/sources
```

Each workspace can define intent in `config/intent.json`:

```json
{
  "goal": "Track acquisitions and launches",
  "focus": ["acquired", "announced"],
  "ignore": ["opinion", "ad"],
  "preferred_entity_types": ["organization", "product"],
  "preferred_relation_types": ["acquired"],
  "report_preferences": {"include_intent_summary": true}
}
```

The runtime reads this file and uses it in extraction, canonical merge alignment metadata,
and dashboard/report generation. If missing, the pipeline writes a default intent file.


Each workspace can define merge policy in `config/merge_policy.json`:

```json
{
  "review_low_confidence_entity_merge": true,
  "entity_merge_min_confidence": 0.65,
  "review_aliases": true,
  "placeholder_review_enabled": true,
  "schema_auto_promote_min_evidence": 99
}
```

When policy requires review, unresolved low-confidence decisions are routed into
`governance/review_queue.json` instead of being silently canonicalized.

Review outcomes are persisted in `governance/review_decisions.json`, with applied effects
fed back into canonical/governance artifacts and summarized in dashboard/changelog outputs.

Taxonomy/ontology growth is persisted in:
- `canonical/taxonomy.json`
- `canonical/ontology.json`
- `governance/taxonomy_candidates.json`

Uncertain taxonomy and ontology additions are routed to taxonomy candidates + `taxonomy_promotion`
review items instead of direct canonical promotion.

Identity memory artifacts are also persisted and reused across runs:
- `canonical/alias_map.json`
- `governance/identity_candidates.json`
- `governance/merge_blocks.json`


This produces workspace artifacts under:

- `config/merge_policy.json`

- `raw/`
- `extracted/`
- `canonical/`
- `governance/`
- `snapshots/`
- `reports/`
- `visuals/`
- `trace/`

## Runtime architecture

1. Ingest and register source metadata (immutable raw records).
2. Route to source adapters (`chat`, `webpage`, `document`) to normalize chunks.
3. Extract claims and candidate artifacts from chunks.
4. Resolve candidates into canonical entities/relations/events.
5. Build taxonomy + ontology artifacts and route uncertain additions to taxonomy candidate governance.
6. Run governance checks (confidence, conflicts, placeholders, schema queue, review queue).
7. Write snapshot and changelog for each run (including taxonomy/ontology growth deltas).
8. Render dashboard summary (including identity-memory and taxonomy/ontology metrics) and graph export artifacts.

## Validation and tests

- Unit/integration tests with `pytest`.
- JSON contract validation for artifacts using explicit required field checks.

Run tests:

```bash
pytest
```

## Sample data and outputs

- Inputs: `sample_data/sources/*.json`
- Example run outputs: `workspaces/sample/`

To create a new workspace with its own intent:

1. Create `workspaces/<id>/config/intent.json` using the schema above.
2. Run `python -m mindvault run --workspace workspaces/<id> --input-dir sample_data/sources`.
3. Inspect `reports/dashboard.md` and `canonical/current.json` for intent-aware outputs.

## Notes

Business intelligence remains inspectable in declarative policy files and artifacts, while Python code handles runtime orchestration, persistence, and validation.

## Codex development workflow

For long-horizon agent work, use repository docs (not one-off chat prompts) as the control plane:
- `docs/codex-ops.md` for the control prompt + task template.
- `docs/roadmap.md` for milestone sequencing.
- `docs/status.md` for current progress and next tasks.

This keeps milestone boundaries, validation, and review-queue behavior explicit and recoverable between runs.
