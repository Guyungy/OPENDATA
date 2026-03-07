# Architecture

## Architectural summary

MindVault is composed of six layers:

1. Ingress Layer
2. Adapter Layer
3. Agent Runtime Layer
4. Knowledge Layer
5. Governance Layer
6. Presentation Layer

The system should be AI-first and artifact-driven.

## 1. Ingress Layer

Purpose:
- accept source materials from multiple channels and formats,
- register source metadata,
- store raw inputs safely.

Supported input classes:
- chat logs
- web page text
- markdown/docs
- csv/tabular data
- OCR text
- PDF-extracted text
- manually pasted notes
- API/webhook payloads

Output artifact:
- raw source record

## 2. Adapter Layer

Purpose:
- normalize source-specific structure,
- clean noise,
- segment content into chunks,
- preserve source metadata,
- add parsing hints.

Adapters:
- chat_adapter
- web_adapter
- doc_adapter
- table_adapter
- ocr_adapter
- pdf_text_adapter

Output artifact:
- normalized chunks

## 3. Agent Runtime Layer

Purpose:
- orchestrate AI-driven tasks,
- route artifacts between agents,
- validate outputs,
- store execution traces.

Runtime responsibilities:
- task dispatch
- model routing
- artifact IO
- JSON schema validation
- retries
- execution trace logging

Runtime should be code.
Business reasoning should be in prompts, policies, and agent definitions where possible.

## 4. Knowledge Layer

MindVault stores three major layers of knowledge:

### Raw layer
Original source materials. Immutable.

### Extracted layer
Intermediate AI outputs:
- claims
- entity candidates
- relation candidates
- event candidates
- schema candidates
- taxonomy candidates

### Canonical layer
Current accepted knowledge:
- entities
- relations
- events
- insights
- schema
- taxonomy
- ontology

## 5. Governance Layer

Purpose:
- score confidence
- audit conflicts
- manage placeholders
- control schema evolution
- support review queues
- preserve version history

Governance is mandatory, not optional.

## 6. Presentation Layer

The system should provide at least four views:
1. Source flow view
2. Knowledge view
3. Governance view
4. Working/report view

## Long-term runtime goal

MindVault should evolve from a batch pipeline into a continuously operating knowledge system with:
- ingestion queue
- scheduler/watchers
- review queue
- changelog generation
- automated reporting
