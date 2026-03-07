from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timezone

from .contracts import make_id


def _ts() -> str:
    return datetime.now(timezone.utc).isoformat()


def merge_canonical(claims, entity_candidates, relation_candidates, event_candidates, previous_canonical, intent):
    entities = {e["name"].lower(): e for e in previous_canonical.get("entities", [])}
    relations = previous_canonical.get("relations", [])
    events = previous_canonical.get("events", [])
    preferred_entity_types = set(intent.get("preferred_entity_types", []))

    for candidate in entity_candidates:
        key = candidate.candidate_name.lower()
        intent_aligned = candidate.candidate_type in preferred_entity_types if preferred_entity_types else True
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
    }


def build_governance(claims, canonical, schema_candidates):
    conflicts = []
    buckets = defaultdict(set)
    for claim in claims:
        key = (claim.subject.lower(), claim.predicate.lower())
        buckets[key].add(claim.object.lower())
    for (subject, predicate), objs in buckets.items():
        if len(objs) > 1:
            conflicts.append(
                {
                    "id": make_id("conf"),
                    "subject": subject,
                    "predicate": predicate,
                    "objects": sorted(objs),
                    "status": "open",
                    "reason": "multiple_object_values",
                }
            )

    placeholders = []
    for entity in canonical["entities"]:
        if entity["type"] == "unknown":
            placeholders.append(
                {
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
            "status": "pending_review",
        }
        for c in schema_candidates
    ]

    return {
        "conflicts": conflicts,
        "placeholders": placeholders,
        "schema_candidate_queue": schema_queue,
        "confidence_scoring_results": confidence_results,
    }
