# MindVault

MindVault is an AI-first, artifact-driven knowledge operating system.

This repository implements a runnable incremental pipeline that separates:
- `raw` (immutable source records)
- `extracted` (claims and candidates)
- `canonical` (resolved entities/relations/events/insights/schema/taxonomy)
- `governance` (conflicts/placeholders/schema queue/confidence)

## Quick start

```bash
python -m mindvault run --workspace workspaces/sample --input-dir sample_data/sources
```

This produces workspace artifacts under:

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
5. Run governance checks (confidence, conflicts, placeholders, schema queue).
6. Write snapshot and changelog for each run.
7. Render dashboard summary and graph export artifacts.

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

## Notes

Business intelligence remains inspectable in declarative policy files and artifacts, while Python code handles runtime orchestration, persistence, and validation.
