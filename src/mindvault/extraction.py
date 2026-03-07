from __future__ import annotations

import re
from collections import Counter

from .contracts import (
    Claim,
    Chunk,
    EntityCandidate,
    EventCandidate,
    RelationCandidate,
    SchemaCandidate,
    make_id,
    now_iso,
)


RELATION_TRIGGERS = [(" works at ", "works_at"), (" acquired ", "acquired")]


def _claim_type(text: str) -> str:
    lower = text.lower()
    if any(token in lower for token in ["rumor", "maybe", "uncertain"]):
        return "uncertain"
    if "think" in lower or "opinion" in lower:
        return "opinion"
    return "fact"


def _extract_entities(text: str) -> list[str]:
    candidates = re.findall(r"\b[A-Z][a-zA-Z0-9]{2,}\b", text)
    return sorted(set(candidates))


def extract_from_chunks(workspace_id: str, chunks: list[Chunk]):
    claims: list[Claim] = []
    entity_candidates: dict[str, EntityCandidate] = {}
    relation_candidates: list[RelationCandidate] = []
    event_candidates: list[EventCandidate] = []
    schema_counter: Counter[str] = Counter()

    for chunk in chunks:
        sentence_parts = [p.strip() for p in re.split(r"[.!?]", chunk.text) if p.strip()]
        for part in sentence_parts:
            tokens = part.split()
            subject = tokens[0] if tokens else "unknown"
            predicate = "mentions"
            obj = " ".join(tokens[1:4]) if len(tokens) > 1 else ""
            claim = Claim(
                id=make_id("clm"),
                workspace_id=workspace_id,
                subject=subject,
                predicate=predicate,
                object=obj,
                claim_text=part,
                claim_type=_claim_type(part),
                source_ref={"source_id": chunk.source_id, "chunk_id": chunk.id},
                speaker=chunk.context_hints.get("speaker", "unknown"),
                claim_time=now_iso(),
                confidence=0.5 if "uncertain" in part.lower() else 0.75,
                verdict="unverified",
                status="active",
            )
            claims.append(claim)
            for name in _extract_entities(part):
                existing = entity_candidates.get(name.lower())
                if existing is None:
                    existing = EntityCandidate(
                        id=make_id("entc"),
                        candidate_type="organization" if name.endswith("Inc") else "unknown",
                        candidate_name=name,
                        confidence=0.6,
                    )
                    entity_candidates[name.lower()] = existing
                existing.supporting_claims.append(claim.id)
                schema_counter["entity:unknown"] += 1

            for phrase, relation_type in RELATION_TRIGGERS:
                if phrase in part:
                    left, right = part.split(phrase, 1)
                    a = left.strip().split()[-1]
                    b = right.strip().split()[0]
                    relation_candidates.append(
                        RelationCandidate(
                            id=make_id("relc"),
                            from_candidate=a,
                            to_candidate=b,
                            relation_type=relation_type,
                            supporting_claims=[claim.id],
                            confidence=0.7,
                        )
                    )
                    schema_counter[f"relation:{relation_type}"] += 1

            if any(k in part.lower() for k in ["launch", "announced", "released"]):
                participants = _extract_entities(part)
                event_candidates.append(
                    EventCandidate(
                        id=make_id("evc"),
                        event_type="announcement",
                        title=part[:80],
                        participants=participants,
                        time_range="unknown",
                        location="unknown",
                        supporting_claims=[claim.id],
                        confidence=0.65,
                    )
                )
                schema_counter["event:announcement"] += 1

    schema_candidates = [
        SchemaCandidate(
            id=make_id("schc"),
            candidate_kind=kind.split(":")[0],
            candidate_name=kind.split(":", 1)[1],
            evidence_count=count,
            source_count=max(1, len(chunks)),
            proposed_value_type="string",
            similarity_to_existing=0.2,
            status="pending_review",
        )
        for kind, count in schema_counter.items()
    ]

    return claims, list(entity_candidates.values()), relation_candidates, event_candidates, schema_candidates
