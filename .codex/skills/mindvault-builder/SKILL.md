# mindvault-builder

Reusable repository skill for MindVault tasks.

## Conventions
- Keep artifact layers separate: raw, extracted, canonical, governance.
- Never promote raw text directly to canonical facts.
- Canonical artifacts must include supporting claim IDs and confidence.
- Governance must expose conflicts, placeholders, and schema queue.

## Artifact naming
- Use `<layer>/<artifact>.json` with stable plural names.
- Use `snapshots/<run_id>.json` and `snapshots/<run_id>_changelog.json`.
- Write run traces to `trace/<run_id>.json`.

## Architecture reminders
- Python handles runtime orchestration, validation, persistence, rendering.
- Business intelligence should remain inspectable in policies/prompts/artifacts.
- Keep adapters source-specific and explicit.

## Governance quality bar
- No hidden conflict resolution.
- Track unresolved placeholders.
- Include confidence summaries for claims/entities/relations.

## Schema evolution
- New schema ideas enter `extracted/schema_candidates.json`.
- Promotion path goes through `governance/schema_candidate_queue.json`.
- Never add canonical schema fields silently.
