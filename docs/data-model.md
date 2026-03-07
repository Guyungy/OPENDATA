# Data Model

## Design rule

MindVault must not directly convert raw text into canonical fact.

The required progression is:

raw source -> chunk -> claim/candidate -> resolution -> canonical knowledge

## Core object types

### 1. Source
Represents an ingested source material.

Fields:
- id
- workspace_id
- source_type
- origin
- ingested_at
- author
- metadata
- raw_content_hash

### 2. Chunk
Represents a normalized segment of a source.

Fields:
- id
- source_id
- chunk_type
- text
- context_hints
- sequence_index

### 3. Claim
Represents a statement extracted from source material.

Fields:
- id
- workspace_id
- subject
- predicate
- object
- claim_text
- claim_type
- source_ref
- speaker
- claim_time
- confidence
- verdict
- status

Claim types:
- fact
- opinion
- rumor
- ad
- uncertain
- historical

Verdicts:
- unverified
- likely
- conflicting
- deprecated
- verified

### 4. EntityCandidate
Represents a possible entity before canonical merge.

Fields:
- id
- candidate_type
- candidate_name
- aliases
- extracted_attributes
- supporting_claims
- confidence

### 5. RelationCandidate
Represents a possible relation before canonical merge.

Fields:
- id
- from_candidate
- to_candidate
- relation_type
- supporting_claims
- confidence

### 6. EventCandidate
Represents a possible event before canonical merge.

Fields:
- id
- event_type
- title
- participants
- time_range
- location
- supporting_claims
- confidence

### 7. Entity
Represents a canonical long-lived object.

Fields:
- id
- type
- name
- aliases
- attributes
- supporting_claims
- source_refs
- confidence
- created_at
- updated_at
- status

### 8. Relation
Represents a canonical relation.

Fields:
- id
- from_entity_id
- to_entity_id
- relation_type
- supporting_claims
- source_refs
- confidence
- valid_time
- status

### 9. Event
Represents a canonical event.

Fields:
- id
- event_type
- title
- participants
- time_range
- location
- supporting_claims
- source_refs
- confidence
- status

### 10. Insight
Represents a generated summary derived from canonical knowledge.

Fields:
- id
- title
- text
- based_on
- confidence
- created_at

### 11. Placeholder
Represents important but missing knowledge.

Fields:
- id
- target_type
- target_id
- field
- status
- first_detected_at
- last_updated_at
- fill_confidence
- supporting_claims

Placeholder status:
- missing
- inferred
- pending_verification
- filled
- deprecated

### 12. SchemaCandidate
Represents a possible new field, entity type, or relation type.

Fields:
- id
- candidate_kind
- candidate_name
- evidence_count
- source_count
- proposed_value_type
- similarity_to_existing
- status

Candidate kinds:
- entity_type
- relation_type
- attribute
- taxonomy_node

## Canonical storage rule

Only resolved and accepted knowledge may enter canonical storage.

Everything else remains in extracted or governance layers.


### 13. ReviewItem
Represents a governance decision requiring human steering.

Fields:
- id
- type
- workspace_id
- status
- priority
- target_ids
- reason
- supporting_artifacts
- supporting_claims
- confidence
- suggested_action
- created_at
- updated_at

Review item types:
- entity_merge
- alias
- conflict
- schema_promotion
- placeholder_relevance

Review item lifecycle statuses:
- pending
- accepted
- rejected
- deferred

### 14. ReviewDecision
Represents an applied human decision for a review item.

Fields:
- id
- review_item_id
- workspace_id
- decision
- decided_at
- decided_by
- rationale
- applied_effects
- status

Decision values:
- accepted
- rejected
- deferred

Storage artifacts:
- governance/review_decisions.json
- governance/review_outcomes.json
