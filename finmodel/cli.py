from __future__ import annotations

import argparse
import json
from pathlib import Path

from .defaults import build_default_model


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the microbrewery financial model")
    parser.add_argument("--section", choices=["all", "income_statement", "free_cash_flow", "valuation"], default="all")
    parser.add_argument("--output", type=Path, help="Optional JSON output path")
    args = parser.parse_args()

    model = build_default_model()
    results = model.run_full_model().yearly
    payload = results if args.section == "all" else {args.section: results[args.section]}

    if args.output:
        args.output.write_text(json.dumps(payload, indent=2))
    else:
        print(json.dumps(payload, indent=2))


if __name__ == "__main__":
    main()
