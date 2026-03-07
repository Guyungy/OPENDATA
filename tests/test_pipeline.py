from __future__ import annotations

import json
from pathlib import Path

from mindvault.pipeline import run_pipeline


def test_pipeline_generates_all_artifacts(tmp_path: Path) -> None:
    input_dir = tmp_path / "inputs"
    workspace = tmp_path / "workspace"
    input_dir.mkdir()
    (input_dir / "one.json").write_text(
        json.dumps(
            {
                "workspace_id": "w1",
                "source_type": "chat_text",
                "text": "Alice: Acme acquired Beta Corp.",
            }
        ),
        encoding="utf-8",
    )

    result = run_pipeline(str(workspace), str(input_dir))
    assert result["stats"]["sources"] == 1

    for required in [
        "config/intent.json",
        "config/merge_policy.json",
        "raw/sources.json",
        "extracted/claims.json",
        "canonical/current.json",
        "governance/conflicts.json",
        "governance/review_queue.json",
        "snapshots",
        "reports/dashboard.md",
        "trace",
    ]:
        assert (workspace / required).exists()

    canonical = json.loads((workspace / "canonical" / "current.json").read_text(encoding="utf-8"))
    assert "entities" in canonical
    assert all("supporting_claims" in e for e in canonical["entities"])


def test_intent_changes_canonical_outputs(tmp_path: Path) -> None:
    input_dir = tmp_path / "inputs"
    input_dir.mkdir()
    (input_dir / "one.json").write_text(
        json.dumps(
            {
                "workspace_id": "w1",
                "source_type": "chat_text",
                "text": "Acme acquired Beta. Acme works at Beta.",
            }
        ),
        encoding="utf-8",
    )

    workspace_a = tmp_path / "workspace_a"
    workspace_b = tmp_path / "workspace_b"
    (workspace_a / "config").mkdir(parents=True)
    (workspace_b / "config").mkdir(parents=True)

    (workspace_a / "config" / "intent.json").write_text(
        json.dumps(
            {
                "goal": "Track M&A events",
                "focus": ["acquired"],
                "ignore": ["works at"],
                "preferred_entity_types": ["organization"],
                "preferred_relation_types": ["acquired"],
                "report_preferences": {"include_intent_summary": True},
            }
        ),
        encoding="utf-8",
    )
    (workspace_b / "config" / "intent.json").write_text(
        json.dumps(
            {
                "goal": "Track employment",
                "focus": ["works at"],
                "ignore": ["acquired"],
                "preferred_entity_types": ["person"],
                "preferred_relation_types": ["works_at"],
                "report_preferences": {"include_intent_summary": True},
            }
        ),
        encoding="utf-8",
    )

    run_pipeline(str(workspace_a), str(input_dir))
    run_pipeline(str(workspace_b), str(input_dir))

    canonical_a = json.loads((workspace_a / "canonical" / "current.json").read_text(encoding="utf-8"))
    canonical_b = json.loads((workspace_b / "canonical" / "current.json").read_text(encoding="utf-8"))

    relation_types_a = {relation["relation_type"] for relation in canonical_a["relations"]}
    relation_types_b = {relation["relation_type"] for relation in canonical_b["relations"]}
    assert relation_types_a == {"acquired"}
    assert relation_types_b == {"works_at"}

    dashboard_a = (workspace_a / "reports" / "dashboard.md").read_text(encoding="utf-8")
    assert "## Workspace Intent" in dashboard_a
    assert "Track M&A events" in dashboard_a


def test_low_confidence_entity_merge_enters_review_queue(tmp_path: Path) -> None:
    input_dir = tmp_path / "inputs"
    workspace = tmp_path / "workspace"
    (workspace / "config").mkdir(parents=True)
    input_dir.mkdir()

    (workspace / "config" / "merge_policy.json").write_text(
        json.dumps({"entity_merge_min_confidence": 0.8, "review_low_confidence_entity_merge": True}),
        encoding="utf-8",
    )
    (input_dir / "one.json").write_text(
        json.dumps(
            {
                "workspace_id": "w-review",
                "source_type": "chat_text",
                "text": "Acme announced Beta partnership.",
            }
        ),
        encoding="utf-8",
    )

    run_pipeline(str(workspace), str(input_dir))

    canonical = json.loads((workspace / "canonical" / "current.json").read_text(encoding="utf-8"))
    assert canonical["entities"] == []

    review_queue = json.loads((workspace / "governance" / "review_queue.json").read_text(encoding="utf-8"))
    assert any(item["type"] == "entity_merge" and item["status"] == "pending" for item in review_queue)


def test_conflict_generates_review_item(tmp_path: Path) -> None:
    input_dir = tmp_path / "inputs"
    workspace = tmp_path / "workspace"
    input_dir.mkdir()

    (input_dir / "one.json").write_text(
        json.dumps(
            {
                "workspace_id": "w-conflict",
                "source_type": "chat_text",
                "text": "Acme valuation 10M. Acme valuation 20M.",
            }
        ),
        encoding="utf-8",
    )

    run_pipeline(str(workspace), str(input_dir))

    conflicts = json.loads((workspace / "governance" / "conflicts.json").read_text(encoding="utf-8"))
    assert conflicts

    review_queue = json.loads((workspace / "governance" / "review_queue.json").read_text(encoding="utf-8"))
    assert any(item["type"] == "conflict" for item in review_queue)


def test_schema_candidate_enters_review_queue(tmp_path: Path) -> None:
    input_dir = tmp_path / "inputs"
    workspace = tmp_path / "workspace"
    input_dir.mkdir()

    (input_dir / "one.json").write_text(
        json.dumps(
            {
                "workspace_id": "w-schema",
                "source_type": "chat_text",
                "text": "Acme acquired Beta.",
            }
        ),
        encoding="utf-8",
    )

    run_pipeline(str(workspace), str(input_dir))

    schema_queue = json.loads((workspace / "governance" / "schema_candidate_queue.json").read_text(encoding="utf-8"))
    assert schema_queue

    review_queue = json.loads((workspace / "governance" / "review_queue.json").read_text(encoding="utf-8"))
    assert any(item["type"] == "schema_promotion" for item in review_queue)
