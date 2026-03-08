# Workflows

## Primary build workflow

The primary MindVault workflow is:

1. ingest source
2. adapt and normalize
3. create chunks
4. parse claims and candidates
5. classify claim types
6. score confidence
7. resolve entities
8. deduplicate candidates
9. build relations and events
10. propose schema/taxonomy changes
11. merge canonical knowledge
12. audit conflicts
13. update placeholders
14. create changelog and snapshot
15. generate insights and reports
16. render dashboard/graph/export artifacts

## Runtime execution principle

MindVault should be built around agent loops with explicit artifacts.

Every major stage should:
- read input artifacts,
- produce output artifacts,
- validate output structure,
- preserve provenance.

## Review queue workflow

The system must support a human steering loop for:
- unresolved entity merges
- unresolved conflicts
- schema candidate promotion
- taxonomy candidate promotion
- placeholder relevance review

## Version workflow

Every run must produce:
- updated canonical state
- snapshot
- changelog
- trace
- optional report summary

## Continuous mode target

Later versions should support:
- watched input folders
- scheduled ingestion
- queue processing
- recurring summaries


## Review consumption workflow

The governance loop is closed through explicit review decisions:

1. read `governance/review_queue.json`
2. apply a decision (`accepted`, `rejected`, `deferred`) to one review item
3. persist decision record in `governance/review_decisions.json`
4. update review item status and `updated_at` in `governance/review_queue.json`
5. apply effects to canonical/governance artifacts by review type:
   - `entity_merge`: create/merge canonical entity when accepted
   - `alias`: update alias map on acceptance, persist rejection blocks on reject
   - `conflict`: resolve conflict and selected canonical value when accepted
   - `schema_promotion`: promote or reject schema candidate lifecycle state
   - `taxonomy_promotion`: promote or reject taxonomy/ontology candidate lifecycle state
   - `placeholder_relevance`: apply placeholder lifecycle action or preserve/defer
6. write review outcome summary artifact (`governance/review_outcomes.json`)
7. reflect outcomes in dashboard/changelog artifacts

This flow is available through CLI:
- `python -m mindvault review --workspace <workspace> --review-item <id> --decision <accepted|rejected|deferred> --decided-by <actor> --rationale <text>`


## Identity memory workflow

Identity continuity is persisted across runs using three explicit artifacts:
- `canonical/alias_map.json`
- `governance/identity_candidates.json`
- `governance/merge_blocks.json`

Resolution behavior:
1. read alias map, identity candidates, and merge blocks at run start
2. use alias map matches to improve canonical entity matching
3. if confidence is insufficient, add/refresh identity candidates instead of silently canonicalizing
4. if a merge block applies, downgrade automatic merge into review item (`merge_blocked_pair_requires_review`)
5. persist updated identity artifacts every run

Review consumption behavior:
- accepted `entity_merge` and `alias` decisions resolve matching identity candidates
- accepted `alias` decisions update canonical alias map entries
- rejected `entity_merge`/`alias` decisions can create merge blocks to prevent repeated silent retries
