# Codex Operating Playbook

Use this playbook to guide milestone-driven development.

## Repository source of truth

Before coding, always read:
- `PROJECT_SPEC.md`
- `AGENTS.md`
- `docs/architecture.md`
- `docs/data-model.md`
- `docs/workflows.md`
- `docs/acceptance.md`
- `docs/roadmap.md`

Treat repository docs as the source of truth.

## Global execution rules

- Work in small, complete milestones.
- Keep the repository runnable after every milestone.
- Prefer explicit artifacts and validation over hidden logic.
- Do not convert uncertain extracted text directly into canonical facts.
- Preserve provenance for canonical knowledge.
- Route uncertainty to review queues instead of silently guessing.
- Update docs when behavior changes.
- Run tests/validation before finishing.

## Suggested control prompt

```text
You are developing MindVault as an AI-first self-growing knowledge operating system.

Before coding:
1. Read PROJECT_SPEC.md, AGENTS.md, docs/architecture.md, docs/data-model.md, docs/workflows.md, docs/acceptance.md, and docs/roadmap.md.
2. Treat repository docs as the source of truth.
3. Inspect the current repository before making changes.

Execution rules:
- Work in small complete milestones.
- Keep the repository runnable after each milestone.
- Prefer explicit artifacts, validation, and governance over hidden logic.
- Do not convert raw text directly into canonical facts.
- Preserve provenance for all canonical knowledge.
- Surface uncertainty in review queues instead of silently guessing.
- Update README and docs when behavior changes.
- Run tests or validation before finishing.

For each task:
- restate the goal briefly in implementation terms,
- make the smallest coherent change,
- implement code and docs,
- run validation,
- generate or update sample artifacts,
- summarize what changed, what passed, and what remains.

A milestone is not complete unless:
- code is implemented,
- docs are updated,
- tests or validation pass,
- sample outputs are generated where relevant.
```

## Single-task template

```text
Task: [task name]

Goal:
[one-sentence goal]

Scope:
- [module/artifact change 1]
- [module/artifact change 2]
- [new artifact]

Inputs:
- [input files/folders]
- [existing docs]

Requirements:
- [requirement 1]
- [requirement 2]
- [requirement 3]

Validation:
- [tests to run]
- [outputs to generate]
- [JSON contracts to satisfy]

Done when:
- [completion condition 1]
- [completion condition 2]
- [completion condition 3]

Also update:
- README.md
- docs/status.md
```

## Review-queue policy for uncertainty

When uncertain, write to governance queues instead of promoting to canonical:
- schema uncertainty -> `governance/schema_candidate_queue.json`
- entity merge uncertainty -> explicit merge review queue artifact
- claim conflicts -> `governance/conflicts.json`
- missing/uncertain fields -> `governance/placeholders.json`
