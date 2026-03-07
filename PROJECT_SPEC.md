# MindVault

## What this project is

MindVault is an AI-first self-growing knowledge operating system.

It is not just a database generator, not just a summarizer, and not just a RAG app.

Its purpose is to continuously ingest heterogeneous source materials, transform them into structured and governable knowledge, evolve its schema and taxonomy over time, and present the results through searchable, inspectable, and reviewable knowledge views.

## Core product goal

MindVault should:
1. accept many kinds of source materials,
2. automatically extract knowledge candidates,
3. automatically build and evolve a canonical knowledge base,
4. preserve evidence and uncertainty,
5. surface conflicts and missing information,
6. allow human steering through review and policy,
7. improve over time through feedback loops.

## Non-goals

MindVault is not:
- a single-shot summary bot,
- a fixed-schema CRUD app,
- a chat-first assistant,
- a pure vector database wrapper,
- a system that assumes all extracted content is factual.

## Design philosophy

1. Humans steer. Agents execute.
2. Raw source material is never overwritten.
3. Claims come before facts.
4. Canonical knowledge must be evidence-backed.
5. Schema growth must be controlled, not automatic chaos.
6. The system must be inspectable and governable.
7. Every important artifact must be versioned.
8. The repository should act as the system of record for architecture and behavior.

## End-state vision

MindVault should become a continuously running knowledge system that:
- ingests arbitrary source materials,
- normalizes and extracts information,
- proposes schema and taxonomy growth,
- builds a canonical knowledge layer,
- tracks confidence and conflict,
- supports review queues,
- produces reports, graphs, timelines, and structured exports.
