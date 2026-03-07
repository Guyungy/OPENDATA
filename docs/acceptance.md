# Acceptance Criteria

## Product-level acceptance

MindVault is acceptable only if it can:
1. ingest at least three distinct input source classes,
2. preserve raw inputs,
3. produce extracted claims and candidates,
4. maintain a canonical knowledge layer,
5. surface conflicts instead of hiding them,
6. track placeholders,
7. version all important changes,
8. generate a governance-oriented dashboard.

## Architecture-level acceptance

The implementation must:
- separate raw, extracted, canonical, and governance artifacts,
- keep provenance for all canonical facts,
- avoid direct raw-text-to-fact shortcuts,
- support schema evolution through candidate promotion,
- remain runnable milestone by milestone.

## Output artifact acceptance

Each workspace should eventually contain:

- raw/
- extracted/
- canonical/
- governance/
- snapshots/
- reports/
- visuals/
- trace/

## Quality acceptance

Every canonical entity, relation, and event must:
- reference supporting claims,
- have confidence,
- have status,
- be reconstructable from artifacts.

## UX acceptance

The UI/dashboard should expose:
- source counts
- entity/event/relation counts
- unresolved conflicts
- low-confidence areas
- unresolved placeholders
- schema candidates
- recent changelog summary
