# Roadmap

This roadmap organizes MindVault delivery into small, complete milestones.
Each milestone should keep the repository runnable, produce reviewable artifacts,
and include validation + documentation updates.

## Milestone 1: Ingestion + Workspace Artifact Store

- Build/maintain input ingestion for multiple source classes.
- Persist immutable raw source records.
- Produce initial workspace artifact folders and contracts.
- Validate workspace structure and source registration.

## Milestone 2: Claims + Candidate Extraction Layer

- Generate chunks, claims, and extraction candidates.
- Keep extracted artifacts separate from canonical artifacts.
- Add schema checks for extracted outputs.
- Validate extraction outputs with sample input fixtures.

## Milestone 3: Canonical Merge + Provenance

- Resolve entity/relation/event candidates into canonical objects.
- Preserve supporting claims and source references.
- Block direct raw-text-to-canonical shortcuts.
- Validate canonical output contracts and provenance coverage.

## Milestone 4: Governance Queues + Conflict Auditing

- Surface unresolved conflicts to governance artifacts.
- Track low-confidence records and placeholder fields.
- Add explicit review queues for merge/schema uncertainty.
- Validate conflict and placeholder artifact generation.

## Milestone 5: Schema Evolution Workflow

- Produce schema candidates from repeated extraction patterns.
- Add promotion rules with explicit thresholds.
- Persist schema-candidate governance queue.
- Validate candidate lifecycle and promotion behavior.

## Milestone 6: Snapshots + Changelog + Trace

- Ensure every run records snapshots, changelogs, and traces.
- Preserve history; do not overwrite previous snapshots.
- Add run-level metadata and summary reports.
- Validate reproducibility from artifacts.

## Milestone 7: Dashboard + Inspectable Views

- Render governance-oriented dashboard outputs.
- Expose source, knowledge, and unresolved-review counts.
- Export basic graph/report artifacts.
- Validate dashboard generation in sample workspace.

## Milestone 8: Continuous Operation Baseline

- Add watched input folders and/or scheduled execution.
- Keep queue processing explicit and inspectable.
- Write artifacts for recurring runs.
- Validate continuous mode on sample sources.

## Milestone 9: Policy + Steering Controls

- Externalize mutable decision logic to prompts/policies where possible.
- Keep runtime core focused on orchestration and contracts.
- Add review pathways for uncertain merge/classification decisions.
- Validate policy-driven behavior changes.

## Milestone 10: Hardening + Acceptance Closure

- Verify all acceptance criteria and artifact contracts.
- Improve test coverage for critical workflows.
- Finalize operator docs and examples.
- Produce release-ready milestone summary.
