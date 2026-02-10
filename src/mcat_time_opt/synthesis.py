from __future__ import annotations

from typing import Dict, List, Any

from .analysis import SectionAnalysis


def _round_to_5(seconds: float) -> int:
    return int(round(seconds / 5.0) * 5)


def _best_quartile_row(quartiles) -> Dict[str, Any]:
    best = quartiles.sort_values(["accuracy", "mean_time_sec"], ascending=[False, True]).iloc[0]
    return {
        "quartile": str(best["quartile"]),
        "mean_time_sec": float(best["mean_time_sec"]),
        "accuracy": float(best["accuracy"]),
    }


def synthesize(analyses: Dict[str, SectionAnalysis]) -> Dict[str, Any]:
    section_outputs: Dict[str, Any] = {}
    leak_candidates: List[Dict[str, Any]] = []

    for section, a in analyses.items():
        best_q = _best_quartile_row(a.quartiles)
        q3 = a.quartiles[a.quartiles["quartile"] == "Q3"]
        q4 = a.quartiles[a.quartiles["quartile"] == "Q4"]
        q3_acc = float(q3["accuracy"].iloc[0]) if len(q3) else None
        q4_acc = float(q4["accuracy"].iloc[0]) if len(q4) else None
        diminishing_returns = bool(q3_acc is not None and q4_acc is not None and q4_acc <= q3_acc)

        cap = a.time_cap
        hard_cap_rounded = _round_to_5(cap["hard_cap_sec"])

        if cap["is_cap_justified"]:
            primary_rule = f"Hard stop at {hard_cap_rounded}s in {section}. If unresolved, eliminate and guess immediately."
        else:
            primary_rule = f"Provisional cap at {hard_cap_rounded}s in {section}; monitor next session and tighten only if >cap accuracy stays flat."

        rules = [primary_rule]
        if a.order_drift["front_loading_flag"]:
            rules.append(
                f"No early overspend in {section}. First third average time must stay <= median pace."
            )
        if a.slow_wrong["guardrail_met"]:
            rules.append(
                f"{section}: treat slow+wrong items as execution sinks; cap and move on when setup is unclear by 30s."
            )

        findings = [
            f"{section}: peak quartile accuracy is {best_q['accuracy']:.1%} at ~{best_q['mean_time_sec']:.0f}s ({best_q['quartile']}).",
            f"{section}: accuracy <= cap is {cap['accuracy_below_cap']:.1%} vs > cap {cap['accuracy_above_cap']:.1%}.",
        ]
        if diminishing_returns:
            findings.append(f"{section}: accuracy plateaus/drops from Q3 to Q4, indicating diminishing returns.")

        intervention = max(
            a.slow_wrong["slow_wrong_pct"],
            0.0 if not cap["is_cap_justified"] else (cap["above_cap_count"] / (cap["above_cap_count"] + cap["below_cap_count"])),
        )
        leak_candidates.append(
            {
                "section": section,
                "impact": float(intervention),
                "cap_justified": bool(cap["is_cap_justified"]),
                "slow_wrong_guardrail": bool(a.slow_wrong["guardrail_met"]),
            }
        )

        session_minutes = 35
        questions_target = max(12, int((session_minutes * 60) / hard_cap_rounded))

        section_outputs[section] = {
            "findings": findings,
            "rules": rules,
            "hard_cap_sec": hard_cap_rounded,
            "practice_block": {
                "duration_min": session_minutes,
                "question_target": questions_target,
                "single_rule": primary_rule,
                "review_rule": "Review only the missed trigger for earlier decision; do not fully re-solve.",
                "success_metrics": [
                    "Cap-violation rate decreases",
                    "Time variance narrows",
                ],
            },
        }

    top_leaks = sorted(
        leak_candidates,
        key=lambda x: (x["impact"], x["cap_justified"], x["slow_wrong_guardrail"]),
        reverse=True,
    )[:3]

    return {
        "sections": section_outputs,
        "top_leaks": top_leaks,
        "core_message": "Spending more time did not reliably increase accuracy. Faster decisions are a rational reallocation, not blind guessing.",
    }
