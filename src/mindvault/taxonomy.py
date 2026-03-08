from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timezone
import re


ALLOWED_NODE_TYPES = {"entity_type", "relation_group", "category", "tag_cluster"}
ALLOWED_NODE_STATUSES = {"active", "candidate", "deprecated"}
ALLOWED_CANDIDATE_KINDS = {"entity_type", "relation_group", "category", "tag_cluster", "ontology_pattern"}
ALLOWED_CANDIDATE_STATUSES = {"pending", "accepted", "rejected", "deferred"}


RELATION_GROUP_MAP = {
    "acquired": "ownership_change",
    "works_at": "employment",
    "announced": "announcement",
    "released": "announcement",
    "mentions": "general",
}


def _ts() -> str:
    return datetime.now(timezone.utc).isoformat()


def _slug(value: str) -> str:
    normalized = re.sub(r"[^a-z0-9]+", "_", value.lower()).strip("_")
    return normalized or "unknown"


def _taxonomy_node_id(node_type: str, name: str) -> str:
    return f"tax_{node_type}_{_slug(name)}"


def _ontology_id(subject_type: str, relation_type: str, object_type: str) -> str:
    return f"ont_{_slug(subject_type)}_{_slug(relation_type)}_{_slug(object_type)}"


def _candidate_id(kind: str, name: str, parent: str | None = None) -> str:
    root = f"{kind}_{name}_{parent or 'none'}"
    return f"taxcand_{_slug(root)}"


def _review_item_id(kind: str, name: str) -> str:
    return f"taxrev_{_slug(f'{kind}_{name}') }"


def _upsert_node(existing_nodes: dict[str, dict], payload: dict) -> dict:
    now = _ts()
    current = existing_nodes.get(payload["id"])
    if current:
        payload["created_at"] = current.get("created_at", now)
        payload["updated_at"] = now
    else:
        payload["created_at"] = now
        payload["updated_at"] = now
    payload["node_type"] = payload["node_type"] if payload["node_type"] in ALLOWED_NODE_TYPES else "category"
    payload["status"] = payload["status"] if payload["status"] in ALLOWED_NODE_STATUSES else "candidate"
    existing_nodes[payload["id"]] = payload
    return payload


def build_taxonomy_ontology(
    canonical: dict,
    claims: list,
    schema_candidates: list,
    existing_taxonomy: dict,
    existing_ontology: dict,
    existing_candidates: list[dict],
    workspace_id: str,
) -> tuple[dict, dict, list[dict], list[dict], dict]:
    taxonomy_nodes = {node["id"]: node for node in existing_taxonomy.get("nodes", [])}
    ontology_entries = {entry["id"]: entry for entry in existing_ontology.get("entries", [])}
    candidates = {item["id"]: item for item in existing_candidates}

    added_taxonomy = 0
    added_ontology = 0
    created_candidates = 0

    relation_group_claims: defaultdict[str, list[str]] = defaultdict(list)
    for claim in claims:
        relation_group_claims["general"].append(claim.id)

    entity_types: defaultdict[str, list[dict]] = defaultdict(list)
    for entity in canonical.get("entities", []):
        entity_types[entity.get("type", "unknown")].append(entity)

    for entity_type, members in entity_types.items():
        node_id = _taxonomy_node_id("entity_type", entity_type)
        source_refs = sorted({claim_id for member in members for claim_id in member.get("supporting_claims", [])})
        confidence = round(sum(member.get("confidence", 0.5) for member in members) / max(1, len(members)), 3)

        should_promote = len(members) >= 2 or node_id in taxonomy_nodes
        if should_promote:
            before = taxonomy_nodes.get(node_id)
            node = _upsert_node(
                taxonomy_nodes,
                {
                    "id": node_id,
                    "name": entity_type,
                    "node_type": "entity_type",
                    "parent_id": None,
                    "source_refs": source_refs,
                    "confidence": confidence,
                    "status": "active",
                },
            )
            if before is None and node["status"] == "active":
                added_taxonomy += 1
        else:
            candidate_id = _candidate_id("entity_type", entity_type)
            if candidate_id not in candidates:
                now = _ts()
                candidates[candidate_id] = {
                    "id": candidate_id,
                    "candidate_kind": "entity_type",
                    "candidate_name": entity_type,
                    "proposed_parent": None,
                    "evidence_count": len(members),
                    "source_count": len(source_refs),
                    "confidence": confidence,
                    "status": "pending",
                    "supporting_refs": source_refs,
                    "proposed_node": {
                        "id": node_id,
                        "name": entity_type,
                        "node_type": "entity_type",
                        "parent_id": None,
                        "source_refs": source_refs,
                        "confidence": confidence,
                        "status": "active",
                    },
                    "created_at": now,
                    "updated_at": now,
                }
                created_candidates += 1

    relation_groups: defaultdict[str, list[dict]] = defaultdict(list)
    for relation in canonical.get("relations", []):
        group_name = RELATION_GROUP_MAP.get(relation.get("relation_type", ""), relation.get("relation_type", "other"))
        relation_groups[group_name].append(relation)

    for group_name, members in relation_groups.items():
        node_id = _taxonomy_node_id("relation_group", group_name)
        source_refs = sorted({claim_id for member in members for claim_id in member.get("supporting_claims", [])})
        confidence = round(sum(member.get("confidence", 0.5) for member in members) / max(1, len(members)), 3)
        before = taxonomy_nodes.get(node_id)
        node = _upsert_node(
            taxonomy_nodes,
            {
                "id": node_id,
                "name": group_name,
                "node_type": "relation_group",
                "parent_id": None,
                "source_refs": source_refs,
                "confidence": confidence,
                "status": "active",
            },
        )
        if before is None and node["status"] == "active":
            added_taxonomy += 1

    for schema in schema_candidates:
        if schema.candidate_kind != "attribute":
            continue
        node_name = schema.candidate_name
        node_id = _taxonomy_node_id("category", node_name)
        if node_id in taxonomy_nodes:
            continue
        candidate_id = _candidate_id("category", node_name)
        if candidate_id in candidates:
            continue
        now = _ts()
        candidates[candidate_id] = {
            "id": candidate_id,
            "candidate_kind": "category",
            "candidate_name": node_name,
            "proposed_parent": None,
            "evidence_count": schema.evidence_count,
            "source_count": schema.source_count,
            "confidence": round(max(0.2, min(0.9, schema.evidence_count / 5)), 3),
            "status": "pending",
            "supporting_refs": [],
            "created_at": now,
            "updated_at": now,
            "proposed_node": {
                "id": node_id,
                "name": node_name,
                "node_type": "category",
                "parent_id": None,
                "source_refs": [],
                "confidence": round(max(0.2, min(0.9, schema.evidence_count / 5)), 3),
                "status": "active",
            },
        }
        created_candidates += 1

    entity_by_id = {entity["id"]: entity for entity in canonical.get("entities", [])}
    pattern_buckets: defaultdict[tuple[str, str, str], dict] = defaultdict(lambda: {"supporting_refs": [], "scores": []})
    for relation in canonical.get("relations", []):
        subject = entity_by_id.get(relation.get("from_entity_id"), {})
        obj = entity_by_id.get(relation.get("to_entity_id"), {})
        pattern = (
            subject.get("type", "unknown"),
            relation.get("relation_type", "related_to"),
            obj.get("type", "unknown"),
        )
        bucket = pattern_buckets[pattern]
        bucket["supporting_refs"].extend(relation.get("supporting_claims", []))
        bucket["scores"].append(relation.get("confidence", 0.5))

    for (subject_type, relation_type, object_type), details in pattern_buckets.items():
        entry_id = _ontology_id(subject_type, relation_type, object_type)
        supporting_refs = sorted(set(details["supporting_refs"]))
        confidence = round(sum(details["scores"]) / max(1, len(details["scores"])), 3)
        should_promote = len(details["scores"]) >= 2 or entry_id in ontology_entries
        if should_promote:
            now = _ts()
            current = ontology_entries.get(entry_id)
            ontology_entries[entry_id] = {
                "id": entry_id,
                "subject_type": subject_type,
                "relation_type": relation_type,
                "object_type": object_type,
                "supporting_refs": supporting_refs,
                "confidence": confidence,
                "status": "active",
                "created_at": current.get("created_at", now) if current else now,
                "updated_at": now,
            }
            if current is None:
                added_ontology += 1
        else:
            name = f"{subject_type}:{relation_type}:{object_type}"
            candidate_id = _candidate_id("ontology_pattern", name)
            if candidate_id not in candidates:
                now = _ts()
                candidates[candidate_id] = {
                    "id": candidate_id,
                    "candidate_kind": "ontology_pattern",
                    "candidate_name": name,
                    "proposed_parent": None,
                    "evidence_count": len(details["scores"]),
                    "source_count": len(supporting_refs),
                    "confidence": confidence,
                    "status": "pending",
                    "supporting_refs": supporting_refs,
                    "proposed_entry": {
                        "id": entry_id,
                        "subject_type": subject_type,
                        "relation_type": relation_type,
                        "object_type": object_type,
                        "supporting_refs": supporting_refs,
                        "confidence": confidence,
                        "status": "active",
                    },
                    "created_at": now,
                    "updated_at": now,
                }
                created_candidates += 1

    taxonomy_payload = {"nodes": sorted(taxonomy_nodes.values(), key=lambda x: x["id"])}
    ontology_payload = {"entries": sorted(ontology_entries.values(), key=lambda x: x["id"])}
    candidate_payload = sorted(candidates.values(), key=lambda x: x["id"])

    review_items = []
    for item in candidate_payload:
        if item.get("status") != "pending":
            continue
        review_items.append(
            {
                "id": _review_item_id(item["candidate_kind"], item["id"]),
                "type": "taxonomy_promotion",
                "workspace_id": workspace_id,
                "status": "pending",
                "priority": "medium",
                "target_ids": [item["id"]],
                "reason": "taxonomy_candidate_requires_review",
                "supporting_artifacts": ["governance/taxonomy_candidates.json", "canonical/current.json"],
                "supporting_claims": item.get("supporting_refs", []),
                "confidence": item.get("confidence", 0.5),
                "suggested_action": "Review taxonomy/ontology candidate and accept, reject, or defer.",
                "created_at": _ts(),
                "updated_at": _ts(),
            }
        )

    metrics = {
        "taxonomy_nodes_added": added_taxonomy,
        "ontology_patterns_added": added_ontology,
        "taxonomy_candidates_created": created_candidates,
    }

    return taxonomy_payload, ontology_payload, candidate_payload, review_items, metrics
