from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from .contracts import make_id, read_json, write_json

DECISION_VALUES = {"accepted", "rejected", "deferred"}
REVIEW_STATUS_VALUES = {"pending", "accepted", "rejected", "deferred"}

REVIEW_DECISION_FIELDS = [
    "id",
    "review_item_id",
    "workspace_id",
    "decision",
    "decided_at",
    "decided_by",
    "rationale",
    "applied_effects",
    "status",
]


def _ts() -> str:
    return datetime.now(timezone.utc).isoformat()


def _read_workspace_json(workspace: Path, relative_path: str, default):
    return read_json(str(workspace / relative_path), default=default)


def _write_workspace_json(workspace: Path, relative_path: str, payload) -> None:
    write_json(str(workspace / relative_path), payload)


def _get_or_create_alias_map(workspace: Path) -> dict:
    alias_map = _read_workspace_json(workspace, "canonical/alias_map.json", default={"aliases": []})
    alias_map.setdefault("aliases", [])
    return alias_map


def _get_or_create_identity_candidates(workspace: Path) -> list[dict]:
    return _read_workspace_json(workspace, "governance/identity_candidates.json", default=[])


def _get_or_create_merge_blocks(workspace: Path) -> list[dict]:
    return _read_workspace_json(workspace, "governance/merge_blocks.json", default=[])


def _upsert_canonical_schema_files(workspace: Path, canonical: dict) -> None:
    _write_workspace_json(workspace, "canonical/schema.json", canonical.get("schema", {}))


def _resolve_identity_candidates(
    candidates: list[dict],
    workspace_id: str,
    candidate_ids: list[str],
    canonical_entity_id: str | None,
    status: str,
) -> list[str]:
    resolved_ids: list[str] = []
    if not candidate_ids:
        return resolved_ids
    candidate_id_set = set(candidate_ids)
    for item in candidates:
        if item.get("workspace_id") != workspace_id:
            continue
        if item.get("status") not in {"pending", "deferred"}:
            continue
        ids = set(item.get("candidate_entity_ids", []))
        if not ids.intersection(candidate_id_set):
            continue
        if canonical_entity_id and canonical_entity_id not in item.get("possible_canonical_entity_ids", []):
            item["possible_canonical_entity_ids"] = sorted(
                set(item.get("possible_canonical_entity_ids", [])) | {canonical_entity_id}
            )
        item["status"] = status
        item["updated_at"] = _ts()
        resolved_ids.append(item["id"])
    return resolved_ids


def _upsert_alias_entry(
    alias_map: dict,
    canonical_entity_id: str,
    canonical_name: str,
    aliases: list[str],
    source_ref: str,
    confidence: float,
) -> None:
    entry = next((a for a in alias_map["aliases"] if a.get("canonical_entity_id") == canonical_entity_id), None)
    if entry is None:
        entry = {
            "canonical_entity_id": canonical_entity_id,
            "canonical_name": canonical_name,
            "aliases": [],
            "source_refs": [],
            "confidence": round(confidence, 3),
            "updated_at": _ts(),
        }
        alias_map["aliases"].append(entry)

    entry["canonical_name"] = canonical_name
    entry["aliases"] = sorted(set(entry.get("aliases", [])) | set(aliases))
    entry["source_refs"] = sorted(set(entry.get("source_refs", [])) | {source_ref})
    entry["confidence"] = round(max(entry.get("confidence", 0.0), confidence), 3)
    entry["updated_at"] = _ts()


def _create_merge_block(
    merge_blocks: list[dict],
    workspace_id: str,
    blocked_entity_ids: list[str],
    reason: str,
    review_item_id: str,
    blocked_candidate_names: list[str] | None = None,
) -> dict:
    block_key = tuple(sorted(blocked_entity_ids))
    blocked_candidate_names = blocked_candidate_names or []
    existing = next((b for b in merge_blocks if tuple(sorted(b.get("blocked_entity_ids", []))) == block_key), None)
    if existing:
        existing["reason"] = reason
        existing["updated_at"] = _ts()
        existing["blocked_candidate_names"] = sorted(
            set(existing.get("blocked_candidate_names", [])) | set(blocked_candidate_names)
        )
        return existing

    block = {
        "id": make_id("mblk"),
        "workspace_id": workspace_id,
        "blocked_entity_ids": sorted(blocked_entity_ids),
        "reason": reason,
        "created_from_review_item": review_item_id,
        "blocked_candidate_names": sorted(blocked_candidate_names),
        "created_at": _ts(),
        "updated_at": _ts(),
    }
    merge_blocks.append(block)
    return block


def _apply_entity_merge_decision(workspace: Path, review_item: dict, decision: str) -> list[dict]:
    entity_candidates = _read_workspace_json(workspace, "extracted/entity_candidates.json", default=[])
    canonical = _read_workspace_json(workspace, "canonical/current.json", default={})
    entities = canonical.get("entities", [])
    identity_candidates = _get_or_create_identity_candidates(workspace)
    merge_blocks = _get_or_create_merge_blocks(workspace)
    workspace_id = review_item.get("workspace_id", "unknown")

    candidate = next((item for item in entity_candidates if item["id"] in review_item.get("target_ids", [])), None)

    if decision != "accepted":
        blocked_ids = [target for target in review_item.get("target_ids", []) if target.startswith("ent")]
        if candidate:
            blocked_ids.append(candidate["id"])
        blocked_ids = sorted(set(blocked_ids))
        if len(blocked_ids) >= 2:
            block = _create_merge_block(
                merge_blocks,
                workspace_id,
                blocked_ids,
                reason="rejected_entity_merge",
                review_item_id=review_item["id"],
                blocked_candidate_names=[candidate.get("candidate_name", "")] if candidate else [],
            )
            rejected = _resolve_identity_candidates(
                identity_candidates,
                workspace_id,
                [candidate["id"]] if candidate else [],
                None,
                "rejected",
            )
            _write_workspace_json(workspace, "governance/identity_candidates.json", identity_candidates)
            _write_workspace_json(workspace, "governance/merge_blocks.json", merge_blocks)
            effects = [{"effect": "merge_block_created", "merge_block_id": block["id"]}]
            if rejected:
                effects.append({"effect": "identity_candidate_rejected", "identity_candidate_ids": rejected})
            return effects
        return [{"effect": "entity_merge_skipped", "reason": f"decision={decision}"}]

    if candidate is None:
        return [{"effect": "entity_merge_missing_candidate"}]

    key = candidate["candidate_name"].lower()
    existing = next((entity for entity in entities if entity["name"].lower() == key), None)
    if existing is None:
        created = {
            "id": make_id("ent"),
            "type": candidate["candidate_type"],
            "name": candidate["candidate_name"],
            "aliases": list(candidate.get("aliases", [])),
            "attributes": dict(candidate.get("extracted_attributes", {})),
            "supporting_claims": list(candidate.get("supporting_claims", [])),
            "source_refs": [],
            "confidence": round(candidate.get("confidence", 0.0), 2),
            "created_at": _ts(),
            "updated_at": _ts(),
            "status": "active",
        }
        entities.append(created)
        canonical_entity_id = created["id"]
        effect = "entity_created_from_review"
    else:
        existing["supporting_claims"] = sorted(
            set(existing.get("supporting_claims", [])) | set(candidate.get("supporting_claims", []))
        )
        existing["aliases"] = sorted(set(existing.get("aliases", [])) | set(candidate.get("aliases", [])))
        existing["updated_at"] = _ts()
        canonical_entity_id = existing["id"]
        effect = "entity_merged_from_review"

    alias_map = _get_or_create_alias_map(workspace)
    if candidate.get("aliases"):
        _upsert_alias_entry(
            alias_map,
            canonical_entity_id,
            candidate["candidate_name"],
            list(candidate.get("aliases", [])),
            source_ref=f"review:{review_item['id']}",
            confidence=round(candidate.get("confidence", 0.0), 3),
        )

    resolved = _resolve_identity_candidates(
        identity_candidates,
        workspace_id,
        [candidate["id"]],
        canonical_entity_id,
        "accepted",
    )

    canonical["entities"] = entities
    _write_workspace_json(workspace, "canonical/current.json", canonical)
    _write_workspace_json(workspace, "canonical/alias_map.json", alias_map)
    _write_workspace_json(workspace, "governance/identity_candidates.json", identity_candidates)
    _write_workspace_json(workspace, "governance/merge_blocks.json", merge_blocks)
    effects = [{"effect": effect, "candidate_id": candidate["id"]}]
    if resolved:
        effects.append({"effect": "identity_candidate_resolved", "identity_candidate_ids": resolved})
    return effects


def _apply_alias_decision(workspace: Path, review_item: dict, decision: str) -> list[dict]:
    canonical = _read_workspace_json(workspace, "canonical/current.json", default={})
    entities = canonical.get("entities", [])
    entity = next((item for item in entities if item["id"] == review_item["target_ids"][0]), None)
    if entity is None:
        return [{"effect": "alias_target_entity_missing"}]

    entity_candidates = _read_workspace_json(workspace, "extracted/entity_candidates.json", default=[])
    candidate = next((item for item in entity_candidates if item["id"] in review_item["target_ids"]), None)
    aliases = list(candidate.get("aliases", [])) if candidate else []
    alias_map = _get_or_create_alias_map(workspace)
    identity_candidates = _get_or_create_identity_candidates(workspace)
    merge_blocks = _get_or_create_merge_blocks(workspace)
    workspace_id = review_item.get("workspace_id", "unknown")

    effects: list[dict] = []
    if decision == "accepted":
        entity["aliases"] = sorted(set(entity.get("aliases", [])) | set(aliases))
        _upsert_alias_entry(
            alias_map,
            entity["id"],
            entity.get("name", "unknown"),
            aliases,
            source_ref=f"review:{review_item['id']}",
            confidence=review_item.get("confidence", 0.5),
        )
        resolved = _resolve_identity_candidates(
            identity_candidates,
            workspace_id,
            [candidate["id"]] if candidate else [],
            entity["id"],
            "accepted",
        )
        effects.append({"effect": "alias_accepted", "aliases": aliases})
        if resolved:
            effects.append({"effect": "identity_candidate_resolved", "identity_candidate_ids": resolved})
    elif decision == "rejected":
        blocked_ids = sorted(set([entity["id"]] + ([candidate["id"]] if candidate else [])))
        block = _create_merge_block(
            merge_blocks,
            workspace_id,
            blocked_ids,
            reason="rejected_alias_review",
            review_item_id=review_item["id"],
            blocked_candidate_names=[candidate.get("candidate_name", "")] if candidate else [],
        )
        rejected = _resolve_identity_candidates(
            identity_candidates,
            workspace_id,
            [candidate["id"]] if candidate else [],
            entity["id"],
            "rejected",
        )
        effects.append({"effect": "alias_rejected_recorded", "aliases": aliases})
        effects.append({"effect": "merge_block_created", "merge_block_id": block["id"]})
        if rejected:
            effects.append({"effect": "identity_candidate_rejected", "identity_candidate_ids": rejected})
    else:
        effects.append({"effect": "alias_deferred", "aliases": aliases})

    _write_workspace_json(workspace, "canonical/current.json", canonical)
    _write_workspace_json(workspace, "canonical/alias_map.json", alias_map)
    _write_workspace_json(workspace, "governance/identity_candidates.json", identity_candidates)
    _write_workspace_json(workspace, "governance/merge_blocks.json", merge_blocks)
    return effects


def _apply_conflict_decision(workspace: Path, review_item: dict, decision: str, resolution_value: str | None) -> list[dict]:
    conflicts = _read_workspace_json(workspace, "governance/conflicts.json", default=[])
    conflict = next((item for item in conflicts if item["id"] in review_item["target_ids"]), None)
    if conflict is None:
        return [{"effect": "conflict_missing"}]

    if decision == "accepted":
        chosen = resolution_value or (conflict.get("objects") or ["unknown"])[0]
        conflict["status"] = "resolved"
        conflict["resolved_at"] = _ts()
        conflict["resolution"] = {"selected_object": chosen}

        canonical = _read_workspace_json(workspace, "canonical/current.json", default={})
        for entity in canonical.get("entities", []):
            if entity.get("name", "").lower() == conflict.get("subject"):
                entity.setdefault("attributes", {})[conflict["predicate"]] = chosen
                entity["updated_at"] = _ts()
        _write_workspace_json(workspace, "canonical/current.json", canonical)
        effect = "conflict_resolved"
    elif decision == "rejected":
        conflict["status"] = "open"
        effect = "conflict_left_unresolved"
    else:
        effect = "conflict_deferred"

    _write_workspace_json(workspace, "governance/conflicts.json", conflicts)
    return [{"effect": effect, "conflict_id": conflict["id"]}]


def _apply_schema_decision(workspace: Path, review_item: dict, decision: str) -> list[dict]:
    schema_queue = _read_workspace_json(workspace, "governance/schema_candidate_queue.json", default=[])
    candidate = next((item for item in schema_queue if item["id"] in review_item["target_ids"]), None)
    if candidate is None:
        return [{"effect": "schema_candidate_missing"}]

    canonical = _read_workspace_json(workspace, "canonical/current.json", default={})
    schema = canonical.setdefault("schema", {"entity_types": [], "relation_types": [], "fields": []})

    if decision == "accepted":
        candidate["status"] = "promoted"
        kind = candidate.get("candidate_kind")
        if kind == "entity":
            schema["entity_types"] = sorted(set(schema.get("entity_types", [])) | {candidate["candidate_name"]})
        elif kind == "relation":
            schema["relation_types"] = sorted(set(schema.get("relation_types", [])) | {candidate["candidate_name"]})
        else:
            schema["fields"] = sorted(set(schema.get("fields", [])) | {candidate["candidate_name"]})
        effect = "schema_promoted"
    elif decision == "rejected":
        candidate["status"] = "rejected"
        effect = "schema_rejected"
    else:
        candidate["status"] = "pending_review"
        effect = "schema_deferred"

    _write_workspace_json(workspace, "canonical/current.json", canonical)
    _write_workspace_json(workspace, "governance/schema_candidate_queue.json", schema_queue)
    _upsert_canonical_schema_files(workspace, canonical)
    return [{"effect": effect, "schema_candidate_id": candidate["id"]}]


def _apply_placeholder_decision(workspace: Path, review_item: dict, decision: str) -> list[dict]:
    placeholders = _read_workspace_json(workspace, "governance/placeholders.json", default=[])
    placeholder = next((item for item in placeholders if item["id"] in review_item["target_ids"]), None)
    if placeholder is None:
        return [{"effect": "placeholder_missing"}]

    if decision == "accepted":
        suggested = review_item.get("suggested_action", "").lower()
        if "deprecat" in suggested:
            placeholder["status"] = "deprecated"
            effect = "placeholder_deprecated"
        elif "fill" in suggested:
            placeholder["status"] = "filled"
            effect = "placeholder_filled"
        else:
            placeholder["status"] = "pending_verification"
            effect = "placeholder_kept_active"
        placeholder["last_updated_at"] = _ts()
    elif decision == "rejected":
        effect = "placeholder_preserved"
    else:
        effect = "placeholder_deferred"

    _write_workspace_json(workspace, "governance/placeholders.json", placeholders)
    return [{"effect": effect, "placeholder_id": placeholder["id"]}]


def _build_review_outcome_counts(review_queue: list[dict], decisions: list[dict]) -> dict:
    counts = {"pending": 0, "accepted": 0, "rejected": 0, "deferred": 0}
    by_type: dict[str, int] = {}
    for item in review_queue:
        status = item.get("status", "pending")
        if status in counts:
            counts[status] += 1
        by_type[item["type"]] = by_type.get(item["type"], 0) + 1
    recent_identity_decisions = [
        decision
        for decision in decisions
        if any(
            effect.get("effect") in {"alias_accepted", "alias_rejected_recorded", "merge_block_created"}
            for effect in decision.get("applied_effects", [])
        )
    ][-5:]
    return {
        "counts": counts,
        "by_type": by_type,
        "recent_decisions": decisions[-5:],
        "recent_identity_decisions": recent_identity_decisions,
    }


def _update_review_outputs(workspace: Path, review_queue: list[dict], decisions: list[dict]) -> None:
    summary = _build_review_outcome_counts(review_queue, decisions)
    _write_workspace_json(workspace, "governance/review_outcomes.json", summary)

    dashboard_path = workspace / "reports" / "dashboard.md"
    if dashboard_path.exists():
        existing = dashboard_path.read_text(encoding="utf-8")
    else:
        existing = "# MindVault Dashboard\n"

    alias_map = _get_or_create_alias_map(workspace)
    identity_candidates = _get_or_create_identity_candidates(workspace)
    merge_blocks = _get_or_create_merge_blocks(workspace)

    section = [
        "\n## Review Decision Outcomes",
        f"- Pending: {summary['counts']['pending']}",
        f"- Accepted: {summary['counts']['accepted']}",
        f"- Rejected: {summary['counts']['rejected']}",
        f"- Deferred: {summary['counts']['deferred']}",
        "\n### Recent decisions",
    ]
    for item in summary["recent_decisions"]:
        section.append(f"- {item['decided_at']}: {item['review_item_id']} -> {item['decision']} ({item['status']})")
    if not summary["recent_decisions"]:
        section.append("- none")

    section.extend(
        [
            "\n## Identity Memory Summary",
            f"- Alias entries: {len(alias_map.get('aliases', []))}",
            f"- Unresolved identity candidates: {len([c for c in identity_candidates if c.get('status') == 'pending'])}",
            f"- Merge blocks: {len(merge_blocks)}",
            "\n### Recent identity decisions",
        ]
    )
    for item in summary["recent_identity_decisions"]:
        section.append(f"- {item['decided_at']}: {item['review_item_id']} -> {item['decision']}")
    if not summary["recent_identity_decisions"]:
        section.append("- none")

    marker = "\n## Review Decision Outcomes"
    if marker in existing:
        existing = existing.split(marker, 1)[0].rstrip() + "\n"
    dashboard_path.parent.mkdir(parents=True, exist_ok=True)
    dashboard_path.write_text(existing + "\n".join(section) + "\n", encoding="utf-8")


def apply_review_decision(
    workspace_dir: str,
    review_item_id: str,
    decision: str,
    decided_by: str,
    rationale: str,
    resolution_value: str | None = None,
) -> dict:
    if decision not in DECISION_VALUES:
        raise ValueError(f"Invalid decision: {decision}")

    workspace = Path(workspace_dir)
    review_queue = _read_workspace_json(workspace, "governance/review_queue.json", default=[])
    review_item = next((item for item in review_queue if item["id"] == review_item_id), None)
    if review_item is None:
        raise ValueError(f"Review item not found: {review_item_id}")
    if review_item.get("status") != "pending":
        raise ValueError(f"Review item is not pending: {review_item_id}")

    applied_effects: list[dict]
    review_type = review_item.get("type")
    if review_type == "entity_merge":
        applied_effects = _apply_entity_merge_decision(workspace, review_item, decision)
    elif review_type == "alias":
        applied_effects = _apply_alias_decision(workspace, review_item, decision)
    elif review_type == "conflict":
        applied_effects = _apply_conflict_decision(workspace, review_item, decision, resolution_value)
    elif review_type == "schema_promotion":
        applied_effects = _apply_schema_decision(workspace, review_item, decision)
    elif review_type == "placeholder_relevance":
        applied_effects = _apply_placeholder_decision(workspace, review_item, decision)
    else:
        applied_effects = [{"effect": "unsupported_review_type", "type": review_type}]

    review_item["status"] = decision
    review_item["updated_at"] = _ts()
    review_item["decided_at"] = _ts()
    review_item["decided_by"] = decided_by
    _write_workspace_json(workspace, "governance/review_queue.json", review_queue)

    decision_record = {
        "id": make_id("rdec"),
        "review_item_id": review_item_id,
        "workspace_id": review_item.get("workspace_id", "unknown"),
        "decision": decision,
        "decided_at": _ts(),
        "decided_by": decided_by,
        "rationale": rationale,
        "applied_effects": applied_effects,
        "status": "applied",
    }
    decisions = _read_workspace_json(workspace, "governance/review_decisions.json", default=[])
    decisions.append(decision_record)
    _write_workspace_json(workspace, "governance/review_decisions.json", decisions)
    _update_review_outputs(workspace, review_queue, decisions)

    return decision_record
