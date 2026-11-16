#!/usr/bin/env python
"""Run the frozen VF baseline on selected local or remote WFDB records."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.evaluation.reporting import write_figures
from src.evaluation.vf_evaluator import evaluate_physionet, save_report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("dataset", choices=("cudb", "vfdb"))
    parser.add_argument("records", nargs="+", help="WFDB record identifiers, e.g. cu01 or 418")
    parser.add_argument("--local-root", help="Directory containing local .hea/.dat/.atr files")
    parser.add_argument("--channel", type=int, default=0)
    parser.add_argument("--window-seconds", type=float, default=4.0)
    parser.add_argument("--overlap", type=float, default=0.0)
    parser.add_argument("--output", default="data/processed/vf_evaluation")
    args = parser.parse_args()
    report = evaluate_physionet(args.dataset, args.records, local_root=args.local_root, channel=args.channel, window_seconds=args.window_seconds, overlap=args.overlap)
    json_path, csv_path = save_report(report, args.output)
    figures = write_figures(report, args.output)
    print(f"Saved report: {json_path}")
    print(f"Saved segments: {csv_path}")
    print("Saved figures:")
    for figure in figures:
        print(f"  {figure}")
    print(report.metrics)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
