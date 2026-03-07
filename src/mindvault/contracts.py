from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any
import hashlib
import json
import uuid


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def make_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:12]}"


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


@dataclass
class SourceRecord:
    id: str
    workspace_id: str
    source_type: str
    origin: str
    ingested_at: str
    author: str
    metadata: dict[str, Any]
    raw_content_hash: str
    raw_text: str


@dataclass
class Chunk:
    id: str
    source_id: str
    chunk_type: str
    text: str
    context_hints: dict[str, Any]
    sequence_index: int


@dataclass
class Claim:
    id: str
    workspace_id: str
    subject: str
    predicate: str
    object: str
    claim_text: str
    claim_type: str
    source_ref: dict[str, Any]
    speaker: str
    claim_time: str
    confidence: float
    verdict: str
    status: str


@dataclass
class EntityCandidate:
    id: str
    candidate_type: str
    candidate_name: str
    aliases: list[str] = field(default_factory=list)
    extracted_attributes: dict[str, Any] = field(default_factory=dict)
    supporting_claims: list[str] = field(default_factory=list)
    confidence: float = 0.0


@dataclass
class RelationCandidate:
    id: str
    from_candidate: str
    to_candidate: str
    relation_type: str
    supporting_claims: list[str]
    confidence: float


@dataclass
class EventCandidate:
    id: str
    event_type: str
    title: str
    participants: list[str]
    time_range: str
    location: str
    supporting_claims: list[str]
    confidence: float


@dataclass
class SchemaCandidate:
    id: str
    candidate_kind: str
    candidate_name: str
    evidence_count: int
    source_count: int
    proposed_value_type: str
    similarity_to_existing: float
    status: str


def to_jsonable(items: list[Any]) -> list[dict[str, Any]]:
    return [asdict(item) if not isinstance(item, dict) else item for item in items]


def write_json(path: str, payload: Any) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)


def read_json(path: str, default: Any) -> Any:
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return default


def validate_required(records: list[dict[str, Any]], required_fields: list[str], label: str) -> list[str]:
    errors: list[str] = []
    for i, record in enumerate(records):
        for field_name in required_fields:
            if field_name not in record:
                errors.append(f"{label}[{i}] missing {field_name}")
    return errors
