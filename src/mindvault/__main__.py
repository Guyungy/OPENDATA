from __future__ import annotations

import argparse
import json

from .pipeline import run_pipeline
from .review import apply_review_decision


def main() -> None:
    parser = argparse.ArgumentParser(description="MindVault pipeline runtime")
    sub = parser.add_subparsers(dest="command", required=True)

    run_cmd = sub.add_parser("run", help="Run ingestion/extraction/canonical/governance pipeline")
    run_cmd.add_argument("--workspace", required=True, help="Workspace directory")
    run_cmd.add_argument("--input-dir", required=True, help="Input directory containing source JSON")

    review_cmd = sub.add_parser("review", help="Apply a decision to a review queue item")
    review_cmd.add_argument("--workspace", required=True, help="Workspace directory")
    review_cmd.add_argument("--review-item", required=True, help="Review item id")
    review_cmd.add_argument("--decision", required=True, choices=["accepted", "rejected", "deferred"])
    review_cmd.add_argument("--decided-by", required=True, help="Reviewer identity")
    review_cmd.add_argument("--rationale", required=True, help="Decision rationale")
    review_cmd.add_argument("--resolution-value", help="Optional chosen value for conflict resolution")

    args = parser.parse_args()
    if args.command == "run":
        result = run_pipeline(args.workspace, args.input_dir)
        print(json.dumps(result, indent=2))
    elif args.command == "review":
        result = apply_review_decision(
            workspace_dir=args.workspace,
            review_item_id=args.review_item,
            decision=args.decision,
            decided_by=args.decided_by,
            rationale=args.rationale,
            resolution_value=args.resolution_value,
        )
        print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
