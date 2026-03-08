from __future__ import annotations

import json
from pathlib import Path

from mindvault.pipeline import run_pipeline
from mindvault.review import apply_review_decision


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
        "canonical/alias_map.json",
        "canonical/taxonomy.json",
        "canonical/ontology.json",
        "governance/conflicts.json",
        "governance/review_queue.json",
        "governance/review_decisions.json",
        "governance/taxonomy_candidates.json",
        "governance/identity_candidates.json",
        "governance/merge_blocks.json",
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


def test_accept_entity_merge_updates_canonical_and_review_status(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    (workspace / "governance").mkdir(parents=True)
    (workspace / "canonical").mkdir(parents=True)
    (workspace / "extracted").mkdir(parents=True)

    (workspace / "canonical" / "current.json").write_text(
        json.dumps({"entities": [], "relations": [], "events": [], "insights": [], "schema": {}, "taxonomy": {}}),
        encoding="utf-8",
    )
    (workspace / "extracted" / "entity_candidates.json").write_text(
        json.dumps(
            [
                {
                    "id": "entc_1",
                    "candidate_type": "organization",
                    "candidate_name": "Acme",
                    "aliases": [],
                    "extracted_attributes": {},
                    "supporting_claims": ["clm_1"],
                    "confidence": 0.72,
                }
            ]
        ),
        encoding="utf-8",
    )
    (workspace / "governance" / "review_queue.json").write_text(
        json.dumps(
            [
                {
                    "id": "rev_1",
                    "type": "entity_merge",
                    "workspace_id": "w",
                    "status": "pending",
                    "priority": "high",
                    "target_ids": ["entc_1"],
                    "reason": "low_confidence_entity_merge",
                    "supporting_artifacts": [],
                    "supporting_claims": ["clm_1"],
                    "confidence": 0.72,
                    "suggested_action": "review",
                    "created_at": "2026-01-01T00:00:00+00:00",
                    "updated_at": "2026-01-01T00:00:00+00:00",
                }
            ]
        ),
        encoding="utf-8",
    )

    apply_review_decision(str(workspace), "rev_1", "accepted", "analyst", "looks right")

    canonical = json.loads((workspace / "canonical" / "current.json").read_text(encoding="utf-8"))
    assert canonical["entities"][0]["name"] == "Acme"
    queue = json.loads((workspace / "governance" / "review_queue.json").read_text(encoding="utf-8"))
    assert queue[0]["status"] == "accepted"


def test_reject_alias_prevents_alias_application_and_records_decision(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    (workspace / "governance").mkdir(parents=True)
    (workspace / "canonical").mkdir(parents=True)
    (workspace / "extracted").mkdir(parents=True)

    (workspace / "canonical" / "current.json").write_text(
        json.dumps(
            {
                "entities": [{"id": "ent_1", "name": "Acme", "aliases": [], "attributes": {}, "supporting_claims": []}],
                "relations": [],
                "events": [],
                "insights": [],
                "schema": {},
                "taxonomy": {},
            }
        ),
        encoding="utf-8",
    )
    (workspace / "extracted" / "entity_candidates.json").write_text(
        json.dumps([{"id": "entc_2", "aliases": ["ACME Corp"]}]),
        encoding="utf-8",
    )
    (workspace / "governance" / "review_queue.json").write_text(
        json.dumps(
            [
                {
                    "id": "rev_2",
                    "type": "alias",
                    "workspace_id": "w",
                    "status": "pending",
                    "priority": "medium",
                    "target_ids": ["ent_1", "entc_2"],
                    "reason": "alias_update_requires_review",
                    "supporting_artifacts": [],
                    "supporting_claims": [],
                    "confidence": 0.6,
                    "suggested_action": "review",
                    "created_at": "2026-01-01T00:00:00+00:00",
                    "updated_at": "2026-01-01T00:00:00+00:00",
                }
            ]
        ),
        encoding="utf-8",
    )

    apply_review_decision(str(workspace), "rev_2", "rejected", "analyst", "not same alias")

    canonical = json.loads((workspace / "canonical" / "current.json").read_text(encoding="utf-8"))
    assert canonical["entities"][0]["aliases"] == []
    alias_map = json.loads((workspace / "canonical" / "alias_map.json").read_text(encoding="utf-8"))
    assert alias_map["aliases"] == []
    merge_blocks = json.loads((workspace / "governance" / "merge_blocks.json").read_text(encoding="utf-8"))
    assert merge_blocks


def test_accept_schema_promotion_updates_canonical_schema(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    (workspace / "governance").mkdir(parents=True)
    (workspace / "canonical").mkdir(parents=True)

    (workspace / "canonical" / "current.json").write_text(
        json.dumps({"entities": [], "relations": [], "events": [], "insights": [], "schema": {"entity_types": [], "relation_types": [], "fields": []}, "taxonomy": {}}),
        encoding="utf-8",
    )
    (workspace / "governance" / "schema_candidate_queue.json").write_text(
        json.dumps([{"id": "schc_1", "candidate_kind": "relation", "candidate_name": "partnered_with", "status": "pending_review"}]),
        encoding="utf-8",
    )
    (workspace / "governance" / "review_queue.json").write_text(
        json.dumps(
            [
                {
                    "id": "rev_3",
                    "type": "schema_promotion",
                    "workspace_id": "w",
                    "status": "pending",
                    "priority": "medium",
                    "target_ids": ["schc_1"],
                    "reason": "schema_candidate_requires_review",
                    "supporting_artifacts": [],
                    "supporting_claims": [],
                    "confidence": 0.6,
                    "suggested_action": "review",
                    "created_at": "2026-01-01T00:00:00+00:00",
                    "updated_at": "2026-01-01T00:00:00+00:00",
                }
            ]
        ),
        encoding="utf-8",
    )

    apply_review_decision(str(workspace), "rev_3", "accepted", "analyst", "promote it")

    schema = json.loads((workspace / "canonical" / "current.json").read_text(encoding="utf-8"))["schema"]
    assert "partnered_with" in schema["relation_types"]


def test_accept_conflict_review_updates_resolution(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    (workspace / "governance").mkdir(parents=True)
    (workspace / "canonical").mkdir(parents=True)

    (workspace / "canonical" / "current.json").write_text(
        json.dumps(
            {
                "entities": [{"id": "ent_1", "name": "acme", "attributes": {}, "aliases": [], "supporting_claims": [], "confidence": 0.8, "status": "active"}],
                "relations": [],
                "events": [],
                "insights": [],
                "schema": {},
                "taxonomy": {},
            }
        ),
        encoding="utf-8",
    )
    (workspace / "governance" / "conflicts.json").write_text(
        json.dumps([{"id": "conf_1", "subject": "acme", "predicate": "valuation", "objects": ["10m", "20m"], "status": "open", "reason": "multiple_object_values"}]),
        encoding="utf-8",
    )
    (workspace / "governance" / "review_queue.json").write_text(
        json.dumps(
            [
                {
                    "id": "rev_4",
                    "type": "conflict",
                    "workspace_id": "w",
                    "status": "pending",
                    "priority": "high",
                    "target_ids": ["conf_1"],
                    "reason": "multiple_object_values",
                    "supporting_artifacts": [],
                    "supporting_claims": [],
                    "confidence": 0.5,
                    "suggested_action": "review",
                    "created_at": "2026-01-01T00:00:00+00:00",
                    "updated_at": "2026-01-01T00:00:00+00:00",
                }
            ]
        ),
        encoding="utf-8",
    )

    apply_review_decision(str(workspace), "rev_4", "accepted", "analyst", "pick conservative", resolution_value="10m")

    conflicts = json.loads((workspace / "governance" / "conflicts.json").read_text(encoding="utf-8"))
    assert conflicts[0]["status"] == "resolved"
    canonical = json.loads((workspace / "canonical" / "current.json").read_text(encoding="utf-8"))
    assert canonical["entities"][0]["attributes"]["valuation"] == "10m"


def test_deferred_decision_updates_review_status_without_canonical_mutation(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    (workspace / "governance").mkdir(parents=True)
    (workspace / "canonical").mkdir(parents=True)

    original = {"entities": [{"id": "ent_1", "type": "organization", "name": "Acme", "aliases": [], "supporting_claims": [], "confidence": 0.8, "status": "active"}], "relations": [], "events": [], "insights": [], "schema": {}, "taxonomy": {}}
    (workspace / "canonical" / "current.json").write_text(json.dumps(original), encoding="utf-8")
    (workspace / "governance" / "review_queue.json").write_text(
        json.dumps(
            [
                {
                    "id": "rev_5",
                    "type": "entity_merge",
                    "workspace_id": "w",
                    "status": "pending",
                    "priority": "high",
                    "target_ids": ["missing_candidate"],
                    "reason": "low_confidence_entity_merge",
                    "supporting_artifacts": [],
                    "supporting_claims": [],
                    "confidence": 0.4,
                    "suggested_action": "review",
                    "created_at": "2026-01-01T00:00:00+00:00",
                    "updated_at": "2026-01-01T00:00:00+00:00",
                }
            ]
        ),
        encoding="utf-8",
    )
    (workspace / "extracted" ).mkdir(parents=True)
    (workspace / "extracted" / "entity_candidates.json").write_text("[]", encoding="utf-8")

    apply_review_decision(str(workspace), "rev_5", "deferred", "analyst", "wait for more evidence")

    queue = json.loads((workspace / "governance" / "review_queue.json").read_text(encoding="utf-8"))
    assert queue[0]["status"] == "deferred"
    canonical_after = json.loads((workspace / "canonical" / "current.json").read_text(encoding="utf-8"))
    assert canonical_after == original


def test_accepted_alias_review_updates_alias_map(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    (workspace / "governance").mkdir(parents=True)
    (workspace / "canonical").mkdir(parents=True)
    (workspace / "extracted").mkdir(parents=True)

    (workspace / "canonical" / "current.json").write_text(
        json.dumps({"entities": [{"id": "ent_1", "type": "organization", "name": "Acme", "aliases": [], "supporting_claims": [], "confidence": 0.8, "status": "active"}], "relations": [], "events": [], "insights": [], "schema": {}, "taxonomy": {}}),
        encoding="utf-8",
    )
    (workspace / "extracted" / "entity_candidates.json").write_text(
        json.dumps([{"id": "entc_1", "aliases": ["ACME Corp"], "candidate_name": "Acme", "candidate_type": "organization", "supporting_claims": []}]),
        encoding="utf-8",
    )
    (workspace / "governance" / "review_queue.json").write_text(
        json.dumps([{"id": "rev_alias", "type": "alias", "workspace_id": "w", "status": "pending", "priority": "medium", "target_ids": ["ent_1", "entc_1"], "reason": "alias_update_requires_review", "supporting_artifacts": [], "supporting_claims": [], "confidence": 0.7, "suggested_action": "review", "created_at": "2026-01-01T00:00:00+00:00", "updated_at": "2026-01-01T00:00:00+00:00", "blocked_candidate_names": ["Acme"]}]),
        encoding="utf-8",
    )

    apply_review_decision(str(workspace), "rev_alias", "accepted", "analyst", "same entity")
    alias_map = json.loads((workspace / "canonical" / "alias_map.json").read_text(encoding="utf-8"))
    assert alias_map["aliases"][0]["canonical_entity_id"] == "ent_1"
    assert "ACME Corp" in alias_map["aliases"][0]["aliases"]


def test_rejected_entity_merge_creates_merge_block_and_prevents_silent_merge(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    input_dir = tmp_path / "inputs"
    (workspace / "governance").mkdir(parents=True)
    (workspace / "canonical").mkdir(parents=True)
    (workspace / "extracted").mkdir(parents=True)
    (workspace / "config").mkdir(parents=True)
    input_dir.mkdir()

    (workspace / "canonical" / "current.json").write_text(
        json.dumps({"entities": [{"id": "ent_1", "type": "organization", "name": "Acme", "aliases": [], "supporting_claims": [], "confidence": 0.8, "status": "active"}], "relations": [], "events": [], "insights": [], "schema": {}, "taxonomy": {}}),
        encoding="utf-8",
    )
    (workspace / "extracted" / "entity_candidates.json").write_text(
        json.dumps([{"id": "entc_1", "candidate_name": "Acme", "candidate_type": "organization", "aliases": ["ACME Corp"], "extracted_attributes": {}, "supporting_claims": [], "confidence": 0.8}]),
        encoding="utf-8",
    )
    (workspace / "governance" / "review_queue.json").write_text(
        json.dumps([{"id": "rev_merge", "type": "entity_merge", "workspace_id": "w", "status": "pending", "priority": "high", "target_ids": ["ent_1", "entc_1"], "reason": "manual", "supporting_artifacts": [], "supporting_claims": [], "confidence": 0.7, "suggested_action": "review", "created_at": "2026-01-01T00:00:00+00:00", "updated_at": "2026-01-01T00:00:00+00:00", "blocked_candidate_names": ["Acme"]}]),
        encoding="utf-8",
    )

    apply_review_decision(str(workspace), "rev_merge", "rejected", "analyst", "not same")
    merge_blocks = json.loads((workspace / "governance" / "merge_blocks.json").read_text(encoding="utf-8"))
    assert any(set(block["blocked_entity_ids"]) == {"ent_1", "entc_1"} for block in merge_blocks)

    (workspace / "config" / "merge_policy.json").write_text(json.dumps({"entity_merge_min_confidence": 0.5}), encoding="utf-8")
    (workspace / "canonical" / "alias_map.json").write_text(json.dumps({"aliases": []}), encoding="utf-8")
    (workspace / "governance" / "identity_candidates.json").write_text("[]", encoding="utf-8")
    (input_dir / "one.json").write_text(json.dumps({"workspace_id": "w", "source_type": "chat_text", "text": "Acme signed deal."}), encoding="utf-8")

    run_pipeline(str(workspace), str(input_dir))
    queue = json.loads((workspace / "governance" / "review_queue.json").read_text(encoding="utf-8"))
    assert any(item["reason"] == "merge_blocked_pair_requires_review" for item in queue)


def test_identity_candidate_generated_for_unresolved_ambiguity(tmp_path: Path) -> None:
    input_dir = tmp_path / "inputs"
    workspace = tmp_path / "workspace"
    input_dir.mkdir()
    (workspace / "config").mkdir(parents=True)
    (workspace / "config" / "merge_policy.json").write_text(
        json.dumps({"entity_merge_min_confidence": 0.95, "review_low_confidence_entity_merge": True}),
        encoding="utf-8",
    )
    (input_dir / "one.json").write_text(json.dumps({"workspace_id": "w", "source_type": "chat_text", "text": "Acme announced product."}), encoding="utf-8")

    run_pipeline(str(workspace), str(input_dir))
    identity_candidates = json.loads((workspace / "governance" / "identity_candidates.json").read_text(encoding="utf-8"))
    assert identity_candidates
    assert identity_candidates[0]["status"] == "pending"


def test_alias_map_consulted_in_later_run_for_resolution(tmp_path: Path) -> None:
    input_dir = tmp_path / "inputs"
    workspace = tmp_path / "workspace"
    input_dir.mkdir()
    (workspace / "canonical").mkdir(parents=True)
    (workspace / "governance").mkdir(parents=True)

    (workspace / "canonical" / "current.json").write_text(
        json.dumps({"entities": [{"id": "ent_1", "type": "organization", "name": "Acme", "aliases": [], "supporting_claims": [], "confidence": 0.8, "status": "active"}], "relations": [], "events": [], "insights": [], "schema": {}, "taxonomy": {}}),
        encoding="utf-8",
    )
    (workspace / "canonical" / "alias_map.json").write_text(
        json.dumps({"aliases": [{"canonical_entity_id": "ent_1", "canonical_name": "Acme", "aliases": ["ACME Corp"], "source_refs": ["seed"], "confidence": 0.8, "updated_at": "2026-01-01T00:00:00+00:00"}]}),
        encoding="utf-8",
    )
    (workspace / "governance" / "merge_blocks.json").write_text("[]", encoding="utf-8")
    (workspace / "governance" / "identity_candidates.json").write_text("[]", encoding="utf-8")

    (input_dir / "one.json").write_text(json.dumps({"workspace_id": "w", "source_type": "chat_text", "text": "ACME Corp acquired Beta."}), encoding="utf-8")
    run_pipeline(str(workspace), str(input_dir))
    canonical = json.loads((workspace / "canonical" / "current.json").read_text(encoding="utf-8"))
    acme = next(e for e in canonical["entities"] if e["id"] == "ent_1")
    assert acme.get("aliases", [])


def test_merge_block_avoids_direct_auto_merge(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    input_dir = tmp_path / "inputs"
    input_dir.mkdir()
    (workspace / "canonical").mkdir(parents=True)
    (workspace / "governance").mkdir(parents=True)

    (workspace / "canonical" / "current.json").write_text(
        json.dumps({"entities": [{"id": "ent_1", "type": "organization", "name": "Acme", "aliases": [], "supporting_claims": [], "confidence": 0.9, "status": "active"}], "relations": [], "events": [], "insights": [], "schema": {}, "taxonomy": {}}),
        encoding="utf-8",
    )
    (workspace / "canonical" / "alias_map.json").write_text(json.dumps({"aliases": []}), encoding="utf-8")
    (workspace / "governance" / "identity_candidates.json").write_text("[]", encoding="utf-8")
    (workspace / "governance" / "merge_blocks.json").write_text(
        json.dumps([{"id": "mblk_1", "workspace_id": "w", "blocked_entity_ids": ["ent_1", "entc_blocked"], "reason": "prior reject", "created_from_review_item": "rev_x", "created_at": "2026-01-01T00:00:00+00:00", "updated_at": "2026-01-01T00:00:00+00:00", "blocked_candidate_names": ["Acme"]}]),
        encoding="utf-8",
    )
    (input_dir / "one.json").write_text(json.dumps({"workspace_id": "w", "source_type": "chat_text", "text": "Acme announced launch."}), encoding="utf-8")

    run_pipeline(str(workspace), str(input_dir))
    queue = json.loads((workspace / "governance" / "review_queue.json").read_text(encoding="utf-8"))
    assert any(item["reason"] == "merge_blocked_pair_requires_review" for item in queue)


def test_pipeline_generates_taxonomy_nodes(tmp_path: Path) -> None:
    input_dir = tmp_path / "inputs"
    workspace = tmp_path / "workspace"
    input_dir.mkdir()
    (input_dir / "one.json").write_text(
        json.dumps({"workspace_id": "w-tax", "source_type": "chat_text", "text": "Acme acquired Beta. Acme acquired Gamma."}),
        encoding="utf-8",
    )

    run_pipeline(str(workspace), str(input_dir))

    taxonomy = json.loads((workspace / "canonical" / "taxonomy.json").read_text(encoding="utf-8"))
    assert taxonomy["nodes"]
    assert any(node["node_type"] == "entity_type" for node in taxonomy["nodes"])


def test_uncertain_taxonomy_additions_create_candidates(tmp_path: Path) -> None:
    input_dir = tmp_path / "inputs"
    workspace = tmp_path / "workspace"
    input_dir.mkdir()
    (input_dir / "one.json").write_text(
        json.dumps({"workspace_id": "w-tax-cand", "source_type": "chat_text", "text": "Acme acquired Beta."}),
        encoding="utf-8",
    )

    run_pipeline(str(workspace), str(input_dir))

    taxonomy_candidates = json.loads((workspace / "governance" / "taxonomy_candidates.json").read_text(encoding="utf-8"))
    assert taxonomy_candidates
    assert any(item["status"] == "pending" for item in taxonomy_candidates)


def test_accept_taxonomy_review_promotes_candidate(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    (workspace / "governance").mkdir(parents=True)
    (workspace / "canonical").mkdir(parents=True)

    candidate = {
        "id": "taxcand_1",
        "candidate_kind": "category",
        "candidate_name": "market_signal",
        "proposed_parent": None,
        "evidence_count": 1,
        "source_count": 1,
        "confidence": 0.6,
        "status": "pending",
        "supporting_refs": ["clm_1"],
        "created_at": "2026-01-01T00:00:00+00:00",
        "updated_at": "2026-01-01T00:00:00+00:00",
        "proposed_node": {
            "id": "tax_category_market_signal",
            "name": "market_signal",
            "node_type": "category",
            "parent_id": None,
            "source_refs": ["clm_1"],
            "confidence": 0.6,
            "status": "active",
        },
    }
    (workspace / "governance" / "taxonomy_candidates.json").write_text(json.dumps([candidate]), encoding="utf-8")
    (workspace / "canonical" / "taxonomy.json").write_text(json.dumps({"nodes": []}), encoding="utf-8")
    (workspace / "canonical" / "ontology.json").write_text(json.dumps({"entries": []}), encoding="utf-8")
    (workspace / "canonical" / "current.json").write_text(
        json.dumps({"entities": [], "relations": [], "events": [], "insights": [], "schema": {}, "taxonomy": {}, "ontology": {}}),
        encoding="utf-8",
    )
    (workspace / "governance" / "review_queue.json").write_text(
        json.dumps(
            [
                {
                    "id": "rev_tax_1",
                    "type": "taxonomy_promotion",
                    "workspace_id": "w",
                    "status": "pending",
                    "priority": "medium",
                    "target_ids": ["taxcand_1"],
                    "reason": "taxonomy_candidate_requires_review",
                    "supporting_artifacts": [],
                    "supporting_claims": ["clm_1"],
                    "confidence": 0.6,
                    "suggested_action": "review",
                    "created_at": "2026-01-01T00:00:00+00:00",
                    "updated_at": "2026-01-01T00:00:00+00:00",
                }
            ]
        ),
        encoding="utf-8",
    )

    apply_review_decision(str(workspace), "rev_tax_1", "accepted", "analyst", "looks good")

    taxonomy = json.loads((workspace / "canonical" / "taxonomy.json").read_text(encoding="utf-8"))
    assert any(node["id"] == "tax_category_market_signal" for node in taxonomy["nodes"])
    updated_candidates = json.loads((workspace / "governance" / "taxonomy_candidates.json").read_text(encoding="utf-8"))
    assert updated_candidates[0]["status"] == "accepted"


def test_ontology_artifact_generated_from_relation_patterns(tmp_path: Path) -> None:
    input_dir = tmp_path / "inputs"
    workspace = tmp_path / "workspace"
    input_dir.mkdir()
    (input_dir / "one.json").write_text(
        json.dumps(
            {
                "workspace_id": "w-ont",
                "source_type": "chat_text",
                "text": "Acme acquired Beta. Gamma acquired Delta.",
            }
        ),
        encoding="utf-8",
    )

    run_pipeline(str(workspace), str(input_dir))

    ontology = json.loads((workspace / "canonical" / "ontology.json").read_text(encoding="utf-8"))
    assert ontology["entries"]
    assert ontology["entries"][0]["relation_type"] == "acquired"


def test_dashboard_includes_taxonomy_metrics(tmp_path: Path) -> None:
    input_dir = tmp_path / "inputs"
    workspace = tmp_path / "workspace"
    input_dir.mkdir()
    (input_dir / "one.json").write_text(
        json.dumps({"workspace_id": "w-dashboard", "source_type": "chat_text", "text": "Acme acquired Beta."}),
        encoding="utf-8",
    )

    run_pipeline(str(workspace), str(input_dir))

    dashboard = (workspace / "reports" / "dashboard.md").read_text(encoding="utf-8")
    assert "## Taxonomy & Ontology" in dashboard
    assert "Taxonomy nodes:" in dashboard
    assert "Ontology patterns:" in dashboard
