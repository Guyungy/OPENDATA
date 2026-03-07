from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timezone

from .contracts import make_id


REVIEW_FIELDS = [
    "id",
    "type",
    "workspace_id",
    "status",
    "priority",
    "target_ids",
    "reason",
    "supporting_artifacts",
    "supporting_claims",
    "confidence",
    "suggested_action",
    "created_at",
    "updated_at",
]


def _ts() -> str:
    return datetime.now(timezone.utc).isoformat()


def _new_review_item(
    review_type: str,
    workspace_id: str,
    priority: str,
    target_ids: list[str],
    reason: str,
    supporting_artifacts: list[str],
    supporting_claims: list[str],
    confidence: float,
    suggested_action: str,
) -> dict:
    ts = _ts()
    return {
        "id": make_id("rev"),
        "type": review_type,
        "workspace_id": workspace_id,
        "status": "pending",
        "priority": priority,
        "target_ids": target_ids,
        "reason": reason,
        "supporting_artifacts": supporting_artifacts,
        "supporting_claims": supporting_claims,
        "confidence": round(confidence, 3),
        "suggested_action": suggested_action,
        "created_at": ts,
        "updated_at": ts,
    }


def merge_canonical(
    claims,
    entity_candidates,
    relation_candidates,
    event_candidates,
    previous_canonical,
    intent,
    merge_policy,
    workspace_id,
):
    entities = {e["name"].lower(): e for e in previous_canonical.get("entities", [])}
    relations = previous_canonical.get("relations", [])
    events = previous_canonical.get("events", [])
    preferred_entity_types = set(intent.get("preferred_entity_types", []))
    review_items: list[dict] = []

    for candidate in entity_candidates:
        key = candidate.candidate_name.lower()
        intent_aligned = candidate.candidate_type in preferred_entity_types if preferred_entity_types else True
        requires_review = candidate.confidence < merge_policy.get("entity_merge_min_confidence", 0.6)
        if requires_review and merge_policy.get("review_low_confidence_entity_merge", True):
            review_items.append(
                _new_review_item(
                    review_type="entity_merge",
                    workspace_id=workspace_id,
                    priority="high",
                    target_ids=[candidate.id],
                    reason="low_confidence_entity_merge",
                    supporting_artifacts=["extracted/entity_candidates.json", "canonical/current.json"],
                    supporting_claims=list(candidate.supporting_claims),
                    confidence=candidate.confidence,
                    suggested_action="Require human review before canonicalizing entity merge.",
                )
            )
            continue

        if key not in entities:
            entities[key] = {
                "id": make_id("ent"),
                "type": candidate.candidate_type,
                "name": candidate.candidate_name,
                "aliases": candidate.aliases,
                "attributes": candidate.extracted_attributes,
                "supporting_claims": list(candidate.supporting_claims),
                "source_refs": [],
                "confidence": round(candidate.confidence, 2),
                "created_at": _ts(),
                "updated_at": _ts(),
                "status": "active",
                "intent_alignment": {
                    "goal": intent.get("goal", ""),
                    "preferred_type_match": intent_aligned,
                },
            }
        else:
            entities[key]["supporting_claims"] = sorted(
                set(entities[key].get("supporting_claims", [])) | set(candidate.supporting_claims)
            )
            entities[key]["updated_at"] = _ts()
            entities[key]["intent_alignment"] = {
                "goal": intent.get("goal", ""),
                "preferred_type_match": intent_aligned,
            }
            if candidate.aliases and merge_policy.get("review_aliases", True):
                review_items.append(
                    _new_review_item(
                        review_type="alias",
                        workspace_id=workspace_id,
                        priority="medium",
                        target_ids=[entities[key]["id"], candidate.id],
                        reason="alias_update_requires_review",
                        supporting_artifacts=["canonical/current.json", "extracted/entity_candidates.json"],
                        supporting_claims=list(candidate.supporting_claims),
                        confidence=min(entities[key].get("confidence", 0.5), candidate.confidence),
                        suggested_action="Review alias list before applying to canonical entity.",
                    )
                )

    for relation in relation_candidates:
        from_entity = entities.get(relation.from_candidate.lower())
        to_entity = entities.get(relation.to_candidate.lower())
        if not from_entity or not to_entity:
            continue
        relations.append(
            {
                "id": make_id("rel"),
                "from_entity_id": from_entity["id"],
                "to_entity_id": to_entity["id"],
                "relation_type": relation.relation_type,
                "supporting_claims": relation.supporting_claims,
                "source_refs": [],
                "confidence": relation.confidence,
                "valid_time": "unknown",
                "status": "active",
            }
        )

    for event in event_candidates:
        events.append(
            {
                "id": make_id("evt"),
                "event_type": event.event_type,
                "title": event.title,
                "participants": event.participants,
                "time_range": event.time_range,
                "location": event.location,
                "supporting_claims": event.supporting_claims,
                "source_refs": [],
                "confidence": event.confidence,
                "status": "active",
            }
        )

    insights = [
        {
            "id": make_id("ins"),
            "title": "Run summary",
            "text": (
                f"Goal: {intent.get('goal', 'general')} | Processed {len(claims)} claims "
                f"and produced {len(events)} events."
            ),
            "based_on": [c.id for c in claims[:10]],
            "confidence": 0.6,
            "created_at": _ts(),
        }
    ]

    return {
        "entities": list(entities.values()),
        "relations": relations,
        "events": events,
        "insights": insights,
        "schema": previous_canonical.get("schema", {"entity_types": [], "relation_types": [], "fields": []}),
        "taxonomy": previous_canonical.get("taxonomy", {"nodes": []}),
    }, review_items


def build_governance(claims, canonical, schema_candidates, review_items, workspace_id, merge_policy):
    conflicts = []
    buckets = defaultdict(set)
    conflict_claim_ids = defaultdict(list)
    for claim in claims:
        key = (claim.subject.lower(), claim.predicate.lower())
        buckets[key].add(claim.object.lower())
        conflict_claim_ids[key].append(claim.id)
    for (subject, predicate), objs in buckets.items():
        if len(objs) > 1:
            conflict_id = make_id("conf")
            conflicts.append(
                {
                    "id": conflict_id,
                    "subject": subject,
                    "predicate": predicate,
                    "objects": sorted(objs),
                    "status": "open",
                    "reason": "multiple_object_values",
                }
            )
            review_items.append(
                _new_review_item(
                    review_type="conflict",
                    workspace_id=workspace_id,
                    priority="high",
                    target_ids=[conflict_id],
                    reason="multiple_object_values",
                    supporting_artifacts=["governance/conflicts.json", "extracted/claims.json"],
                    supporting_claims=conflict_claim_ids[(subject, predicate)],
                    confidence=0.4,
                    suggested_action="Resolve conflicting claim objects and set canonical verdict.",
                )
            )

    placeholders = []
    for entity in canonical["entities"]:
        if entity["type"] == "unknown":
            placeholder = {
                "id": make_id("ph"),
                "target_type": "entity",
                "target_id": entity["id"],
                "field": "type",
                "status": "missing",
                "first_detected_at": _ts(),
                "last_updated_at": _ts(),
                "fill_confidence": 0.2,
                "supporting_claims": entity.get("supporting_claims", []),
            }
            placeholders.append(placeholder)
            if merge_policy.get("placeholder_review_enabled", True):
                review_items.append(
                    _new_review_item(
                        review_type="placeholder_relevance",
                        workspace_id=workspace_id,
                        priority="medium",
                        target_ids=[placeholder["id"], entity["id"]],
                        reason="placeholder_aging_or_missing_core_field",
                        supporting_artifacts=["governance/placeholders.json", "canonical/current.json"],
                        supporting_claims=placeholder["supporting_claims"],
                        confidence=placeholder["fill_confidence"],
                        suggested_action="Confirm placeholder is still relevant and prioritize enrichment.",
                    )
                )

    confidence_results = {
        "claims_avg": round(sum(c.confidence for c in claims) / max(1, len(claims)), 3),
        "entities_avg": round(
            sum(e["confidence"] for e in canonical["entities"]) / max(1, len(canonical["entities"])), 3
        ),
        "relations_avg": round(
            sum(r["confidence"] for r in canonical["relations"]) / max(1, len(canonical["relations"])), 3
        ),
    }

    schema_queue = [
        {
            "id": c.id,
            "candidate_kind": c.candidate_kind,
            "candidate_name": c.candidate_name,
            "evidence_count": c.evidence_count,
            "source_count": c.source_count,
            "proposed_value_type": c.proposed_value_type,
            "similarity_to_existing": c.similarity_to_existing,
            "status": "pending_review",
        }
        for c in schema_candidates
    ]

    for schema_candidate in schema_queue:
        if schema_candidate["evidence_count"] >= merge_policy.get("schema_auto_promote_min_evidence", 99):
            continue
        review_items.append(
            _new_review_item(
                review_type="schema_promotion",
                workspace_id=workspace_id,
                priority="medium",
                target_ids=[schema_candidate["id"]],
                reason="schema_candidate_requires_review",
                supporting_artifacts=["extracted/schema_candidates.json", "governance/schema_candidate_queue.json"],
                supporting_claims=[],
                confidence=0.5,
                suggested_action="Review schema candidate and approve or reject promotion.",
            )
        )

    return {
        "conflicts": conflicts,
        "placeholders": placeholders,
        "schema_candidate_queue": schema_queue,
        "confidence_scoring_results": confidence_results,
        "review_queue": review_items,
    }
