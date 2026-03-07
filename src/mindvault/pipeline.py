from __future__ import annotations

from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
import json

from .adapters import route_adapter
from .contracts import make_id, now_iso, read_json, sha256_text, to_jsonable, validate_required, write_json
from .extraction import extract_from_chunks
from .resolution import build_governance, merge_canonical

REQUIRED_DIRS = [
    "raw",
    "extracted",
    "canonical",
    "governance",
    "snapshots",
    "reports",
    "visuals",
    "trace",
]


def _ensure_dirs(workspace: Path) -> None:
    for dirname in REQUIRED_DIRS:
        (workspace / dirname).mkdir(parents=True, exist_ok=True)


def _load_sources(input_dir: Path) -> list[dict]:
    sources = []
    for path in sorted(input_dir.glob("*.json")):
        with open(path, "r", encoding="utf-8") as f:
            sources.append(json.load(f))
    return sources


def _record_snapshot(workspace: Path, run_id: str, canonical: dict, changelog: dict) -> None:
    snapshot = {
        "run_id": run_id,
        "created_at": now_iso(),
        "canonical": canonical,
    }
    write_json(str(workspace / "snapshots" / f"{run_id}.json"), snapshot)
    write_json(str(workspace / "snapshots" / f"{run_id}_changelog.json"), changelog)


def _build_changelog(prev: dict, curr: dict) -> dict:
    return {
        "created_at": now_iso(),
        "entity_delta": len(curr.get("entities", [])) - len(prev.get("entities", [])),
        "relation_delta": len(curr.get("relations", [])) - len(prev.get("relations", [])),
        "event_delta": len(curr.get("events", [])) - len(prev.get("events", [])),
        "summary": "Canonical layer updated from extracted candidates and governance checks.",
    }


def _render_dashboard(workspace: Path, run_id: str, stats: dict, changelog: dict, governance: dict) -> None:
    md = f"""# MindVault Dashboard\n\n- Run ID: `{run_id}`\n- Timestamp: {datetime.now(timezone.utc).isoformat()}\n\n## Knowledge State\n- Sources: {stats['sources']}\n- Chunks: {stats['chunks']}\n- Claims: {stats['claims']}\n- Entities: {stats['entities']}\n- Relations: {stats['relations']}\n- Events: {stats['events']}\n\n## Governance State\n- Conflicts: {len(governance['conflicts'])}\n- Placeholders: {len(governance['placeholders'])}\n- Schema Queue: {len(governance['schema_candidate_queue'])}\n- Claim confidence (avg): {governance['confidence_scoring_results']['claims_avg']}\n\n## Recent Changelog\n- Entity delta: {changelog['entity_delta']}\n- Relation delta: {changelog['relation_delta']}\n- Event delta: {changelog['event_delta']}\n"""
    (workspace / "reports" / "dashboard.md").write_text(md, encoding="utf-8")
    write_json(str(workspace / "visuals" / "knowledge_graph.json"), {"nodes": stats["entities"], "edges": stats["relations"]})


def run_pipeline(workspace_dir: str, input_dir: str) -> dict:
    workspace = Path(workspace_dir)
    _ensure_dirs(workspace)
    run_id = datetime.now(timezone.utc).strftime("run_%Y%m%d_%H%M%S")

    trace = {
        "run_id": run_id,
        "events": [],
    }

    sources_raw = _load_sources(Path(input_dir))
    trace["events"].append({"stage": "ingress", "count": len(sources_raw), "at": now_iso()})

    source_records = []
    chunks = []
    for src in sources_raw:
        text = src["text"]
        source_id = make_id("src")
        source_record = {
            "id": source_id,
            "workspace_id": src.get("workspace_id", "sample"),
            "source_type": src["source_type"],
            "origin": src.get("origin", "local"),
            "ingested_at": now_iso(),
            "author": src.get("author", "unknown"),
            "metadata": src.get("metadata", {}),
            "raw_content_hash": sha256_text(text),
            "raw_text": text,
        }
        source_records.append(source_record)
        adapter = route_adapter(src["source_type"])
        chunks.extend([asdict(chunk) for chunk in adapter(source_id, text)])

    trace["events"].append({"stage": "adapter", "count": len(chunks), "at": now_iso()})

    from .contracts import Chunk

    typed_chunks = [Chunk(**chunk) for chunk in chunks]
    claims, entity_candidates, relation_candidates, event_candidates, schema_candidates = extract_from_chunks(
        workspace_id="sample", chunks=typed_chunks
    )

    trace["events"].append({"stage": "extraction", "count": len(claims), "at": now_iso()})

    prev_canonical = read_json(str(workspace / "canonical" / "current.json"), default={})
    canonical = merge_canonical(claims, entity_candidates, relation_candidates, event_candidates, prev_canonical)
    governance = build_governance(claims, canonical, schema_candidates)
    changelog = _build_changelog(prev_canonical, canonical)

    validation_errors = []
    validation_errors.extend(
        validate_required(to_jsonable(claims), ["id", "claim_text", "source_ref", "confidence", "status"], "claims")
    )
    validation_errors.extend(
        validate_required(canonical["entities"], ["id", "name", "supporting_claims", "confidence", "status"], "entities")
    )
    validation_errors.extend(
        validate_required(governance["conflicts"], ["id", "status", "reason"], "conflicts")
    )

    write_json(str(workspace / "raw" / "sources.json"), source_records)
    write_json(str(workspace / "extracted" / "chunks.json"), chunks)
    write_json(str(workspace / "extracted" / "claims.json"), to_jsonable(claims))
    write_json(str(workspace / "extracted" / "entity_candidates.json"), to_jsonable(entity_candidates))
    write_json(str(workspace / "extracted" / "relation_candidates.json"), to_jsonable(relation_candidates))
    write_json(str(workspace / "extracted" / "event_candidates.json"), to_jsonable(event_candidates))
    write_json(str(workspace / "extracted" / "schema_candidates.json"), to_jsonable(schema_candidates))

    write_json(str(workspace / "canonical" / "current.json"), canonical)

    write_json(str(workspace / "governance" / "conflicts.json"), governance["conflicts"])
    write_json(str(workspace / "governance" / "placeholders.json"), governance["placeholders"])
    write_json(str(workspace / "governance" / "schema_candidate_queue.json"), governance["schema_candidate_queue"])
    write_json(str(workspace / "governance" / "confidence_scoring_results.json"), governance["confidence_scoring_results"])

    _record_snapshot(workspace, run_id, canonical, changelog)

    stats = {
        "sources": len(source_records),
        "chunks": len(chunks),
        "claims": len(claims),
        "entities": len(canonical["entities"]),
        "relations": len(canonical["relations"]),
        "events": len(canonical["events"]),
    }

    _render_dashboard(workspace, run_id, stats, changelog, governance)
    trace["events"].append({"stage": "render", "at": now_iso(), "stats": stats})
    write_json(str(workspace / "trace" / f"{run_id}.json"), trace)

    result = {
        "run_id": run_id,
        "stats": stats,
        "validation_errors": validation_errors,
    }
    write_json(str(workspace / "reports" / "run_result.json"), result)
    return result
