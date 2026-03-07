# AGENTS.md

## Agent operating rules

You are building MindVault, an AI-first self-growing knowledge operating system.

Before making changes:
1. Read PROJECT_SPEC.md and all docs in /docs.
2. Treat repository docs as the source of truth.
3. Prefer legibility over hidden cleverness.
4. Keep the project runnable after every milestone.
5. Do not collapse raw, extracted, and canonical knowledge into one layer.
6. Do not treat uncertain source text as canonical fact without an explicit claim-resolution step.
7. Add tests or validation artifacts for important behavior.
8. Update README and docs when architecture changes.

## Execution style

- Work incrementally.
- Make small but complete milestones.
- Preserve backward compatibility when reasonable.
- Prefer explicit data contracts and JSON schemas.
- Prefer declarative agent definitions and prompts where behavior is expected to evolve.
- Keep Python for runtime, storage, orchestration, and validation.
- Keep business intelligence in prompts, policies, and reviewable artifacts when possible.

## Required development loop

For each milestone:
1. inspect the repository,
2. design the smallest coherent change,
3. implement code and docs,
4. run tests or validation,
5. produce or update example output artifacts,
6. summarize what changed and what remains.

## Quality bar

A feature is not complete unless it has:
- a clear input contract,
- a clear output contract,
- persistence or artifact generation where appropriate,
- at least one validation path,
- documentation.

## Forbidden shortcuts

Do not:
- merge extraction logic and canonical merge logic into one opaque step,
- silently invent fields without recording schema evolution,
- discard source provenance,
- overwrite previous snapshots,
- hide conflicts instead of surfacing them,
- hardcode business-specific assumptions into the runtime core.
