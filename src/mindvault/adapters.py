from __future__ import annotations

from .contracts import Chunk, make_id


def _split_lines(text: str) -> list[str]:
    return [line.strip() for line in text.splitlines() if line.strip()]


def adapt_chat(source_id: str, text: str) -> list[Chunk]:
    chunks: list[Chunk] = []
    for idx, line in enumerate(_split_lines(text)):
        speaker = "unknown"
        content = line
        if ":" in line:
            maybe_speaker, maybe_content = line.split(":", 1)
            if maybe_speaker and maybe_content:
                speaker = maybe_speaker.strip()
                content = maybe_content.strip()
        chunks.append(
            Chunk(
                id=make_id("chk"),
                source_id=source_id,
                chunk_type="chat_turn",
                text=content,
                context_hints={"speaker": speaker},
                sequence_index=idx,
            )
        )
    return chunks


def adapt_webpage(source_id: str, text: str) -> list[Chunk]:
    chunks: list[Chunk] = []
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    for idx, para in enumerate(paragraphs):
        chunks.append(
            Chunk(
                id=make_id("chk"),
                source_id=source_id,
                chunk_type="web_paragraph",
                text=para,
                context_hints={"format": "paragraph"},
                sequence_index=idx,
            )
        )
    return chunks


def adapt_document(source_id: str, text: str) -> list[Chunk]:
    chunks: list[Chunk] = []
    for idx, line in enumerate(_split_lines(text)):
        chunk_type = "heading" if line.startswith("#") else "doc_line"
        chunks.append(
            Chunk(
                id=make_id("chk"),
                source_id=source_id,
                chunk_type=chunk_type,
                text=line.lstrip("# "),
                context_hints={"markdown": True},
                sequence_index=idx,
            )
        )
    return chunks


def route_adapter(source_type: str):
    if source_type == "chat_text":
        return adapt_chat
    if source_type == "webpage_text":
        return adapt_webpage
    if source_type == "document_markdown":
        return adapt_document
    raise ValueError(f"Unsupported source_type: {source_type}")
