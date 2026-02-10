from __future__ import annotations

import argparse
import json
from pathlib import Path

from .analysis import run_analysis
from .ingest import load_exam_data
from .report import build_markdown_report, write_report
from .synthesis import synthesize


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="MCAT time allocation optimization engine")
    parser.add_argument("--input-dir", default="data/exam_1", help="Directory containing exam CSV files")
    parser.add_argument("--report-path", default="outputs/report_exam_1.md", help="Markdown report output path")
    parser.add_argument("--json-path", default="outputs/report_exam_1.json", help="JSON output path")
    parser.add_argument("--rolling-window", type=int, default=8, help="Rolling window size for drift analysis")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    ingest_result = load_exam_data(args.input_dir)
    analyses = run_analysis(ingest_result.questions_df, rolling_window=args.rolling_window)
    synthesis_output = synthesize(analyses)

    report_md = build_markdown_report(ingest_result.section_aggregates, synthesis_output)
    write_report(args.report_path, report_md)

    json_payload = {
        "section_aggregates": ingest_result.section_aggregates.to_dict(orient="records"),
        "analysis": {
            sec: {
                "section": obj.section,
                "quartiles": obj.quartiles.to_dict(orient="records"),
                "time_cap": obj.time_cap,
                "order_drift": obj.order_drift,
                "slow_wrong": obj.slow_wrong,
            }
            for sec, obj in analyses.items()
        },
        "synthesis": synthesis_output,
    }
    Path(args.json_path).parent.mkdir(parents=True, exist_ok=True)
    Path(args.json_path).write_text(json.dumps(json_payload, indent=2))

    print(f"Wrote markdown report: {args.report_path}")
    print(f"Wrote JSON summary: {args.json_path}")


if __name__ == "__main__":
    main()
