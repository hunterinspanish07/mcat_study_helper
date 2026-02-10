from __future__ import annotations

from pathlib import Path
from typing import Dict, Any

import pandas as pd


def _fmt_pct(v: float) -> str:
    return f"{v:.1%}"


def _fmt_sec(v: float) -> str:
    return f"{v:.0f}s"


def build_markdown_report(section_aggregates: pd.DataFrame, synthesis_output: Dict[str, Any]) -> str:
    lines = ["# MCAT Time Allocation Optimization Report (Exam 1)", ""]

    lines.extend(["## Top 3 Findings", ""])
    for i, leak in enumerate(synthesis_output["top_leaks"], start=1):
        lines.append(
            f"{i}. **{leak['section']}**: high-impact timing leak (impact index {leak['impact']:.1%}); cap justified={leak['cap_justified']}."
        )
    lines.append("")

    lines.extend(["## Per-Section Time Rules", ""])
    for _, row in section_aggregates.sort_values("section").iterrows():
        section = row["section"]
        out = synthesis_output["sections"][section]
        lines.append(f"### {section}")
        lines.append(f"- Questions: {int(row['total_questions'])}")
        lines.append(f"- Accuracy: {_fmt_pct(float(row['accuracy']))}")
        lines.append(f"- Median time: {_fmt_sec(float(row['median_time_sec']))}")
        lines.append(f"- Hard cap: {_fmt_sec(float(out['hard_cap_sec']))}")
        lines.append("- Findings:")
        for finding in out["findings"]:
            lines.append(f"  - {finding}")
        lines.append("- Rules:")
        for rule in out["rules"]:
            lines.append(f"  - {rule}")
        lines.append("")

    lines.extend(["## 2–3 Day Plan", ""])
    for section in sorted(synthesis_output["sections"]):
        pb = synthesis_output["sections"][section]["practice_block"]
        lines.append(f"### {section} Next Session")
        lines.append(
            f"- Block: {pb['duration_min']} minutes, {pb['question_target']} questions, {synthesis_output['sections'][section]['hard_cap_sec']}s cap"
        )
        lines.append(f"- Enforced rule: {pb['single_rule']}")
        lines.append(f"- Review: {pb['review_rule']}")
        lines.append("- Success metrics:")
        for metric in pb["success_metrics"]:
            lines.append(f"  - {metric}")
        lines.append("")

    lines.extend(["## Core Message", "", synthesis_output["core_message"], ""])

    return "\n".join(lines)


def write_report(path: str | Path, content: str) -> None:
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(content)
