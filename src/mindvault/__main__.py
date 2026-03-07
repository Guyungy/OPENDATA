from __future__ import annotations

import argparse
import json

from .pipeline import run_pipeline


def main() -> None:
    parser = argparse.ArgumentParser(description="MindVault pipeline runtime")
    sub = parser.add_subparsers(dest="command", required=True)

    run_cmd = sub.add_parser("run", help="Run ingestion/extraction/canonical/governance pipeline")
    run_cmd.add_argument("--workspace", required=True, help="Workspace directory")
    run_cmd.add_argument("--input-dir", required=True, help="Input directory containing source JSON")

    args = parser.parse_args()
    if args.command == "run":
        result = run_pipeline(args.workspace, args.input_dir)
        print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
