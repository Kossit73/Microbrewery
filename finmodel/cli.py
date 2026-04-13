from __future__ import annotations

import argparse
import json
from pathlib import Path

from .defaults import build_default_model


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the microbrewery financial model")
    parser.add_argument("--section", choices=["all", "assumptions", "schedules", "results", "income_statement", "free_cash_flow", "valuation"], default="all")
    parser.add_argument("--output", type=Path, help="Optional JSON output path")
    args = parser.parse_args()

    model = build_default_model()
    results = model.run_full_model().yearly
    if args.section == "all":
        payload = results
    elif args.section in {"assumptions", "schedules", "results"}:
        payload = {args.section: results[args.section]}
    else:
        payload = {args.section: results["results"][args.section]}

    if args.output:
        args.output.write_text(json.dumps(payload, indent=2))
    else:
        print(json.dumps(payload, indent=2))


if __name__ == "__main__":
    main()
