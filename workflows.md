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
