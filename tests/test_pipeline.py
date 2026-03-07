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
        "raw/sources.json",
        "extracted/claims.json",
        "canonical/current.json",
        "governance/conflicts.json",
        "snapshots",
        "reports/dashboard.md",
        "trace",
    ]:
        assert (workspace / required).exists()

    canonical = json.loads((workspace / "canonical" / "current.json").read_text(encoding="utf-8"))
    assert "entities" in canonical
    assert all("supporting_claims" in e for e in canonical["entities"])
