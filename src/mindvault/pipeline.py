from __future__ import annotations

from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
import json

from .adapters import route_adapter
from .contracts import make_id, now_iso, read_json, sha256_text, to_jsonable, validate_required, write_json
from .extraction import extract_from_chunks
from .resolution import REVIEW_FIELDS, build_governance, merge_canonical
from .taxonomy import build_taxonomy_ontology

REQUIRED_DIRS = [
    "config",
    "raw",
    "extracted",
    "canonical",
    "governance",
    "snapshots",
    "reports",
    "visuals",
    "trace",
]

DEFAULT_INTENT = {
    "goal": "Build a balanced general-purpose knowledge base for this workspace.",
    "focus": [],
    "ignore": [],
    "preferred_entity_types": [],
    "preferred_relation_types": [],
    "report_preferences": {
        "include_intent_summary": True,
    },
}

DEFAULT_MERGE_POLICY = {
    "review_low_confidence_entity_merge": True,
    "entity_merge_min_confidence": 0.65,
    "review_aliases": True,
    "placeholder_review_enabled": True,
    "schema_auto_promote_min_evidence": 99,
}


def _ensure_dirs(workspace: Path) -> None:
    for dirname in REQUIRED_DIRS:
        (workspace / dirname).mkdir(parents=True, exist_ok=True)


def _load_sources(input_dir: Path) -> list[dict]:
    sources = []
    for path in sorted(input_dir.glob("*.json")):
        with open(path, "r", encoding="utf-8") as f:
            sources.append(json.load(f))
    return sources


def _load_workspace_intent(workspace: Path) -> dict:
    intent_path = workspace / "config" / "intent.json"
    existing = read_json(str(intent_path), default={})
    merged = {**DEFAULT_INTENT, **existing}
    if not isinstance(merged.get("report_preferences"), dict):
        merged["report_preferences"] = dict(DEFAULT_INTENT["report_preferences"])
    write_json(str(intent_path), merged)
    return merged


def _load_merge_policy(workspace: Path) -> dict:
    policy_path = workspace / "config" / "merge_policy.json"
    existing = read_json(str(policy_path), default={})
    merged = {**DEFAULT_MERGE_POLICY, **existing}
    write_json(str(policy_path), merged)
    return merged


def _get_or_create_alias_map(workspace: Path) -> dict:
    alias_map = read_json(str(workspace / "canonical" / "alias_map.json"), default={})
    if not alias_map:
        alias_map = {"aliases": []}
    alias_map.setdefault("aliases", [])
    return alias_map


def _get_or_create_identity_candidates(workspace: Path) -> list[dict]:
    return read_json(str(workspace / "governance" / "identity_candidates.json"), default=[])


def _get_or_create_merge_blocks(workspace: Path) -> list[dict]:
    return read_json(str(workspace / "governance" / "merge_blocks.json"), default=[])


def _record_snapshot(workspace: Path, run_id: str, canonical: dict, changelog: dict) -> None:
    snapshot = {
        "run_id": run_id,
        "created_at": now_iso(),
        "canonical": canonical,
    }
    write_json(str(workspace / "snapshots" / f"{run_id}.json"), snapshot)
    write_json(str(workspace / "snapshots" / f"{run_id}_changelog.json"), changelog)


def _decision_summary(review_queue: list[dict], review_decisions: list[dict]) -> dict:
    queue_counts = {"pending": 0, "accepted": 0, "rejected": 0, "deferred": 0}
    by_type: dict[str, int] = {}
    for item in review_queue:
        status = item.get("status", "pending")
        if status in queue_counts:
            queue_counts[status] += 1
        by_type[item["type"]] = by_type.get(item["type"], 0) + 1

    effect_counts = {
        "review_items_resolved": 0,
        "merges_accepted": 0,
        "aliases_accepted": 0,
        "conflicts_resolved": 0,
        "schema_promotions_accepted": 0,
        "placeholders_deprecated": 0,
        "review_items_deferred": 0,
        "merge_blocks_created": 0,
        "identity_candidates_resolved": 0,
        "taxonomy_candidates_promoted": 0,
        "taxonomy_candidates_rejected": 0,
    }
    for decision in review_decisions:
        value = decision.get("decision")
        if value in {"accepted", "rejected"}:
            effect_counts["review_items_resolved"] += 1
        if value == "deferred":
            effect_counts["review_items_deferred"] += 1
        for effect in decision.get("applied_effects", []):
            name = effect.get("effect")
            if name in {"entity_created_from_review", "entity_merged_from_review"}:
                effect_counts["merges_accepted"] += 1
            elif name == "alias_accepted":
                effect_counts["aliases_accepted"] += 1
            elif name == "conflict_resolved":
                effect_counts["conflicts_resolved"] += 1
            elif name == "schema_promoted":
                effect_counts["schema_promotions_accepted"] += 1
            elif name == "placeholder_deprecated":
                effect_counts["placeholders_deprecated"] += 1
            elif name == "merge_block_created":
                effect_counts["merge_blocks_created"] += 1
            elif name in {"identity_candidate_resolved", "identity_candidate_rejected"}:
                effect_counts["identity_candidates_resolved"] += 1
            elif name == "taxonomy_candidate_promoted":
                effect_counts["taxonomy_candidates_promoted"] += 1
            elif name == "taxonomy_candidate_rejected":
                effect_counts["taxonomy_candidates_rejected"] += 1

    return {"queue_counts": queue_counts, "by_type": by_type, "effects": effect_counts}


def _build_changelog(
    prev: dict,
    curr: dict,
    review_queue: list[dict],
    review_decisions: list[dict],
    taxonomy_metrics: dict,
) -> dict:
    review_summary = _decision_summary(review_queue, review_decisions)
    return {
        "created_at": now_iso(),
        "entity_delta": len(curr.get("entities", [])) - len(prev.get("entities", [])),
        "relation_delta": len(curr.get("relations", [])) - len(prev.get("relations", [])),
        "event_delta": len(curr.get("events", [])) - len(prev.get("events", [])),
        "review_outcomes": review_summary["effects"],
        "taxonomy_nodes_added": taxonomy_metrics.get("taxonomy_nodes_added", 0),
        "ontology_patterns_added": taxonomy_metrics.get("ontology_patterns_added", 0),
        "taxonomy_candidates_created": taxonomy_metrics.get("taxonomy_candidates_created", 0),
        "taxonomy_candidates_promoted": review_summary["effects"].get("taxonomy_candidates_promoted", 0),
        "taxonomy_candidates_rejected": review_summary["effects"].get("taxonomy_candidates_rejected", 0),
        "summary": "Canonical layer updated from extracted candidates and governance checks.",
    }


def _render_dashboard(
    workspace: Path,
    run_id: str,
    stats: dict,
    changelog: dict,
    governance: dict,
    intent: dict,
    review_decisions: list[dict],
    alias_map: dict,
    identity_candidates: list[dict],
    merge_blocks: list[dict],
    taxonomy: dict,
    ontology: dict,
    taxonomy_candidates: list[dict],
) -> None:
    intent_section = ""
    if intent.get("report_preferences", {}).get("include_intent_summary", True):
        intent_section = (
            "\n## Workspace Intent\n"
            f"- Goal: {intent['goal']}\n"
            f"- Focus: {', '.join(intent['focus']) or 'none'}\n"
            f"- Ignore: {', '.join(intent['ignore']) or 'none'}\n"
            f"- Preferred entity types: {', '.join(intent['preferred_entity_types']) or 'none'}\n"
            f"- Preferred relation types: {', '.join(intent['preferred_relation_types']) or 'none'}\n"
        )

    review_counts = {"pending": 0, "accepted": 0, "rejected": 0, "deferred": 0}
    review_type_counts: dict[str, int] = {}
    for item in governance["review_queue"]:
        status = item.get("status", "pending")
        if status in review_counts:
            review_counts[status] += 1
        review_type_counts[item["type"]] = review_type_counts.get(item["type"], 0) + 1

    type_lines = "\n".join([f"- {review_type}: {count}" for review_type, count in sorted(review_type_counts.items())])
    if not type_lines:
        type_lines = "- none"

    recent_decisions = review_decisions[-5:]
    recent_lines = "\n".join(
        [
            f"- {item['decided_at']}: {item['review_item_id']} -> {item['decision']} ({item['status']})"
            for item in recent_decisions
        ]
    )
    if not recent_lines:
        recent_lines = "- none"

    md = f"""# MindVault Dashboard

- Run ID: `{run_id}`
- Timestamp: {datetime.now(timezone.utc).isoformat()}
{intent_section}
## Knowledge State
- Sources: {stats['sources']}
- Chunks: {stats['chunks']}
- Claims: {stats['claims']}
- Entities: {stats['entities']}
- Relations: {stats['relations']}
- Events: {stats['events']}

## Governance State
- Conflicts: {len(governance['conflicts'])}
- Placeholders: {len(governance['placeholders'])}
- Schema Queue: {len(governance['schema_candidate_queue'])}
- Claim confidence (avg): {governance['confidence_scoring_results']['claims_avg']}

## Review Summary
- Pending reviews: {review_counts['pending']}
- Accepted reviews: {review_counts['accepted']}
- Rejected reviews: {review_counts['rejected']}
- Deferred reviews: {review_counts['deferred']}

### Review counts by type
{type_lines}

### Recent decisions
{recent_lines}

## Identity Memory
- Alias entries: {len(alias_map.get('aliases', []))}
- Unresolved identity candidates: {len([c for c in identity_candidates if c.get('status') == 'pending'])}
- Merge blocks: {len(merge_blocks)}

## Taxonomy & Ontology
- Taxonomy nodes: {len(taxonomy.get('nodes', []))}
- Ontology patterns: {len(ontology.get('entries', []))}
- Pending taxonomy candidates: {len([item for item in taxonomy_candidates if item.get('status') == 'pending'])}
- Recently promoted taxonomy candidates: {len([item for item in taxonomy_candidates if item.get('status') == 'accepted'])}

## Recent Changelog
- Entity delta: {changelog['entity_delta']}
- Relation delta: {changelog['relation_delta']}
- Event delta: {changelog['event_delta']}
- Review items resolved: {changelog['review_outcomes']['review_items_resolved']}
- Merges accepted: {changelog['review_outcomes']['merges_accepted']}
- Aliases accepted: {changelog['review_outcomes']['aliases_accepted']}
- Conflicts resolved: {changelog['review_outcomes']['conflicts_resolved']}
- Schema promotions accepted: {changelog['review_outcomes']['schema_promotions_accepted']}
- Placeholders deprecated: {changelog['review_outcomes']['placeholders_deprecated']}
- Review items deferred: {changelog['review_outcomes']['review_items_deferred']}
- Merge blocks created: {changelog['review_outcomes']['merge_blocks_created']}
- Identity candidates resolved: {changelog['review_outcomes']['identity_candidates_resolved']}
- Taxonomy nodes added: {changelog['taxonomy_nodes_added']}
- Ontology patterns added: {changelog['ontology_patterns_added']}
- Taxonomy candidates created: {changelog['taxonomy_candidates_created']}
- Taxonomy candidates promoted: {changelog['taxonomy_candidates_promoted']}
- Taxonomy candidates rejected: {changelog['taxonomy_candidates_rejected']}
"""
    (workspace / "reports" / "dashboard.md").write_text(md, encoding="utf-8")
    write_json(str(workspace / "visuals" / "knowledge_graph.json"), {"nodes": stats["entities"], "edges": stats["relations"]})


def run_pipeline(workspace_dir: str, input_dir: str) -> dict:
    workspace = Path(workspace_dir)
    _ensure_dirs(workspace)
    run_id = datetime.now(timezone.utc).strftime("run_%Y%m%d_%H%M%S")

    trace = {
        "run_id": run_id,
        "events": [],
    }
    intent = _load_workspace_intent(workspace)
    merge_policy = _load_merge_policy(workspace)
    trace["events"].append({"stage": "intent", "at": now_iso(), "goal": intent["goal"]})
    trace["events"].append(
        {"stage": "policy", "at": now_iso(), "entity_merge_min_confidence": merge_policy["entity_merge_min_confidence"]}
    )

    sources_raw = _load_sources(Path(input_dir))
    trace["events"].append({"stage": "ingress", "count": len(sources_raw), "at": now_iso()})

    source_records = []
    chunks = []
    for src in sources_raw:
        text = src["text"]
        source_id = make_id("src")
        source_record = {
            "id": source_id,
            "workspace_id": src.get("workspace_id", "sample"),
            "source_type": src["source_type"],
            "origin": src.get("origin", "local"),
            "ingested_at": now_iso(),
            "author": src.get("author", "unknown"),
            "metadata": src.get("metadata", {}),
            "raw_content_hash": sha256_text(text),
            "raw_text": text,
        }
        source_records.append(source_record)
        adapter = route_adapter(src["source_type"])
        chunks.extend([asdict(chunk) for chunk in adapter(source_id, text)])

    trace["events"].append({"stage": "adapter", "count": len(chunks), "at": now_iso()})

    from .contracts import Chunk

    typed_chunks = [Chunk(**chunk) for chunk in chunks]
    workspace_id = source_records[0]["workspace_id"] if source_records else "sample"
    claims, entity_candidates, relation_candidates, event_candidates, schema_candidates = extract_from_chunks(
        workspace_id=workspace_id, chunks=typed_chunks, intent=intent
    )

    trace["events"].append({"stage": "extraction", "count": len(claims), "at": now_iso()})

    prev_canonical = read_json(str(workspace / "canonical" / "current.json"), default={})
    alias_map = _get_or_create_alias_map(workspace)
    identity_candidates = _get_or_create_identity_candidates(workspace)
    merge_blocks = _get_or_create_merge_blocks(workspace)

    canonical, review_items, identity_candidates = merge_canonical(
        claims,
        entity_candidates,
        relation_candidates,
        event_candidates,
        prev_canonical,
        intent,
        merge_policy,
        workspace_id,
        alias_map,
        identity_candidates,
        merge_blocks,
    )
    existing_taxonomy = read_json(str(workspace / "canonical" / "taxonomy.json"), default={"nodes": []})
    existing_ontology = read_json(str(workspace / "canonical" / "ontology.json"), default={"entries": []})
    existing_taxonomy_candidates = read_json(str(workspace / "governance" / "taxonomy_candidates.json"), default=[])

    taxonomy, ontology, taxonomy_candidates, taxonomy_review_items, taxonomy_metrics = build_taxonomy_ontology(
        canonical,
        claims,
        schema_candidates,
        existing_taxonomy,
        existing_ontology,
        existing_taxonomy_candidates,
        workspace_id,
    )
    canonical["taxonomy"] = taxonomy
    canonical["ontology"] = ontology

    governance = build_governance(claims, canonical, schema_candidates, review_items, workspace_id, merge_policy)
    governance["review_queue"].extend(taxonomy_review_items)
    review_decisions = read_json(str(workspace / "governance" / "review_decisions.json"), default=[])
    changelog = _build_changelog(
        prev_canonical,
        canonical,
        governance["review_queue"],
        review_decisions,
        taxonomy_metrics,
    )

    validation_errors = []
    validation_errors.extend(
        validate_required(to_jsonable(claims), ["id", "claim_text", "source_ref", "confidence", "status"], "claims")
    )
    validation_errors.extend(
        validate_required(canonical["entities"], ["id", "name", "supporting_claims", "confidence", "status"], "entities")
    )
    validation_errors.extend(validate_required(governance["conflicts"], ["id", "status", "reason"], "conflicts"))
    validation_errors.extend(validate_required(governance["review_queue"], REVIEW_FIELDS, "review_queue"))
    validation_errors.extend(
        validate_required(taxonomy.get("nodes", []), ["id", "name", "node_type", "status", "created_at", "updated_at"], "taxonomy")
    )
    validation_errors.extend(
        validate_required(ontology.get("entries", []), ["id", "subject_type", "relation_type", "object_type", "status"], "ontology")
    )
    validation_errors.extend(
        validate_required(
            taxonomy_candidates,
            ["id", "candidate_kind", "candidate_name", "evidence_count", "source_count", "status", "created_at", "updated_at"],
            "taxonomy_candidates",
        )
    )

    write_json(str(workspace / "raw" / "sources.json"), source_records)
    write_json(str(workspace / "extracted" / "chunks.json"), chunks)
    write_json(str(workspace / "extracted" / "claims.json"), to_jsonable(claims))
    write_json(str(workspace / "extracted" / "entity_candidates.json"), to_jsonable(entity_candidates))
    write_json(str(workspace / "extracted" / "relation_candidates.json"), to_jsonable(relation_candidates))
    write_json(str(workspace / "extracted" / "event_candidates.json"), to_jsonable(event_candidates))
    write_json(str(workspace / "extracted" / "schema_candidates.json"), to_jsonable(schema_candidates))

    write_json(str(workspace / "canonical" / "current.json"), canonical)
    write_json(str(workspace / "canonical" / "taxonomy.json"), taxonomy)
    write_json(str(workspace / "canonical" / "ontology.json"), ontology)
    write_json(str(workspace / "canonical" / "alias_map.json"), alias_map)

    write_json(str(workspace / "governance" / "conflicts.json"), governance["conflicts"])
    write_json(str(workspace / "governance" / "placeholders.json"), governance["placeholders"])
    write_json(str(workspace / "governance" / "schema_candidate_queue.json"), governance["schema_candidate_queue"])
    write_json(str(workspace / "governance" / "confidence_scoring_results.json"), governance["confidence_scoring_results"])
    write_json(str(workspace / "governance" / "review_queue.json"), governance["review_queue"])
    write_json(str(workspace / "governance" / "review_decisions.json"), review_decisions)
    write_json(str(workspace / "governance" / "taxonomy_candidates.json"), taxonomy_candidates)
    write_json(str(workspace / "governance" / "identity_candidates.json"), identity_candidates)
    write_json(str(workspace / "governance" / "merge_blocks.json"), merge_blocks)

    _record_snapshot(workspace, run_id, canonical, changelog)

    stats = {
        "sources": len(source_records),
        "chunks": len(chunks),
        "claims": len(claims),
        "entities": len(canonical["entities"]),
        "relations": len(canonical["relations"]),
        "events": len(canonical["events"]),
        "alias_entries": len(alias_map.get("aliases", [])),
        "identity_candidates": len(identity_candidates),
        "merge_blocks": len(merge_blocks),
        "taxonomy_nodes": len(taxonomy.get("nodes", [])),
        "ontology_patterns": len(ontology.get("entries", [])),
        "pending_taxonomy_candidates": len([item for item in taxonomy_candidates if item.get("status") == "pending"]),
    }

    _render_dashboard(
        workspace,
        run_id,
        stats,
        changelog,
        governance,
        intent,
        review_decisions,
        alias_map,
        identity_candidates,
        merge_blocks,
        taxonomy,
        ontology,
        taxonomy_candidates,
    )
    trace["events"].append({"stage": "render", "at": now_iso(), "stats": stats})
    write_json(str(workspace / "trace" / f"{run_id}.json"), trace)

    result = {
        "run_id": run_id,
        "stats": stats,
        "intent": intent,
        "validation_errors": validation_errors,
    }
    write_json(str(workspace / "reports" / "run_result.json"), result)
    return result
