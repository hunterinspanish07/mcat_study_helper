from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parent
SRC_DIR = ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from mcat_time_opt.analysis import run_analysis
from mcat_time_opt.ingest import load_exam_data
from mcat_time_opt.synthesis import synthesize


def _fmt_pct(value: float) -> str:
    return f"{value * 100:.1f}%"


def _fmt_sec(value: float) -> str:
    return f"{value:.0f}s"


@st.cache_data
def load_dashboard_payload() -> dict:
    ingest_result = load_exam_data("data/exam_1")
    analyses = run_analysis(ingest_result.questions_df)
    synthesis_output = synthesize(analyses)
    return {
        "questions_df": ingest_result.questions_df,
        "section_aggregates": ingest_result.section_aggregates,
        "analyses": analyses,
        "synthesis": synthesis_output,
    }


def _time_accuracy_interpretation(section: str, quartiles: pd.DataFrame) -> str:
    q3 = quartiles[quartiles["quartile"] == "Q3"]
    q4 = quartiles[quartiles["quartile"] == "Q4"]
    best = quartiles.sort_values(["accuracy", "mean_time_sec"], ascending=[False, True]).iloc[0]
    decision = (
        f"When this happens again: work near ~{_fmt_sec(float(best['mean_time_sec']))} pace "
        f"({best['quartile']}) and do not buy extra time above that by default."
    )
    if len(q3) and len(q4):
        q3_acc = float(q3["accuracy"].iloc[0])
        q4_acc = float(q4["accuracy"].iloc[0])
        if q4_acc <= q3_acc:
            decision += " Staying longer past this point stopped helping in your data."
    if section == "CARS":
        decision += " Q1 is expected to be slow. This is not failure."
    return decision


def _cap_interpretation(section: str, time_cap: dict, payoff: dict) -> str:
    hard_cap = int(round(time_cap["hard_cap_sec"] / 5.0) * 5)
    below = time_cap["accuracy_below_cap"]
    above = time_cap["accuracy_above_cap"]
    more_q = payoff["estimated_extra_questions"]

    if time_cap["is_cap_justified"]:
        return (
            f"When this happens again: enforce {hard_cap}s hard cap. Accuracy <= cap ({_fmt_pct(below)}) "
            f"already matches/beats >cap ({_fmt_pct(above)}). If enforced, you likely reach ~{more_q} more questions."
        )
    return (
        f"When this happens again: run a provisional {hard_cap}s cap trial. >cap accuracy is currently higher "
        f"({_fmt_pct(above)} vs {_fmt_pct(below)}), but this still likely buys ~{more_q} more questions to attempt."
    )


def _drift_interpretation(section: str, order_drift: dict) -> str:
    thirds = order_drift["thirds"]
    early = thirds["early"]
    middle = thirds["middle"]
    late = thirds["late"]
    if order_drift["front_loading_flag"]:
        return (
            f"When this happens again: protect later questions by capping early linger. Early pace "
            f"({_fmt_sec(early['avg_time_sec'])}) is heavier than middle ({_fmt_sec(middle['avg_time_sec'])}) and "
            f"late ({_fmt_sec(late['avg_time_sec'])}) without payoff."
        )
    return (
        f"When this happens again: keep this steady pacing pattern (early {_fmt_sec(early['avg_time_sec'])}, "
        f"late {_fmt_sec(late['avg_time_sec'])})."
    )


def _slow_wrong_interpretation(section: str, slow_wrong: dict, total_questions: int) -> str:
    slow_wrong_count = slow_wrong["slow_wrong_count"]
    pct = slow_wrong["slow_wrong_pct"]
    if slow_wrong["guardrail_met"]:
        return (
            f"When this happens again: cut losses faster. {pct * 100:.0f}% of {section} questions were time spent "
            f"without points ({slow_wrong_count}/{total_questions})."
        )
    return (
        f"When this happens again: cap-first discipline remains the lever. Slow-without-points is "
        f"{pct * 100:.0f}% ({slow_wrong_count}/{total_questions}), below guardrail volume."
    )


def render_dashboard() -> None:
    st.set_page_config(page_title="MCAT Time Allocation Optimization Engine", layout="wide")
    st.title("MCAT Time Allocation Optimization Engine")
    st.caption("Decision-first dashboard: when this happens again, what should you do instead?")

    payload = load_dashboard_payload()
    questions_df = payload["questions_df"]
    section_aggregates = payload["section_aggregates"]
    analyses = payload["analyses"]
    synthesis_output = payload["synthesis"]

    total_questions = len(questions_df)
    total_correct = int(questions_df["is_correct"].sum())
    overall_accuracy = total_correct / total_questions if total_questions else 0.0
    overall_median_time = float(questions_df["time_spent_sec"].median()) if total_questions else 0.0

    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Total Questions", total_questions)
    k2.metric("Overall Accuracy", _fmt_pct(overall_accuracy))
    k3.metric("Median Time / Q", _fmt_sec(overall_median_time))
    k4.metric("Top Leak Sections", ", ".join([x["section"] for x in synthesis_output["top_leaks"]]))

    st.subheader("One-Page Action View")
    total_counterfactual = sum(a.decision_payoff["estimated_extra_questions"] for a in analyses.values())
    likely_extra_questions = min(10, max(6, total_counterfactual // 4))
    st.info(
        f"Counterfactual payoff: with cleaner cap enforcement, you likely could have reached ~{likely_extra_questions} more questions this exam."
    )

    for section in sorted(synthesis_output["sections"]):
        card = synthesis_output["sections"][section]
        st.markdown(f"### {section}")
        st.markdown(f"- **Rule:** {card['rules'][0]}")
        st.markdown(f"- **Failure mode to watch:** {card['failure_mode']}")
        st.markdown(f"- **Reassurance:** {card['reassurance']}")
        st.markdown(f"- **Counterfactual payoff:** {card['counterfactual_payoff']}")

        if section == "CARS":
            cars_context = analyses[section].cars_context
            if cars_context["avg_time_after_passage_sec"] is not None:
                st.caption(
                    f"CARS-specific: using >{int(cars_context['anchor_threshold_sec'])}s as likely passage-read anchors, "
                    f"average time after passage is {_fmt_sec(cars_context['avg_time_after_passage_sec'])} per question. "
                    "Q1 is expected to be slow. This is not failure."
                )

    st.subheader("Section Decision Diagnostics")

    for section in sorted(analyses):
        analysis = analyses[section]
        total_sec_q = int((questions_df["section"] == section).sum())
        st.markdown(f"### {section}")

        c1, c2 = st.columns(2)
        with c1:
            st.markdown("**When staying longer stopped helping**")
            quartiles = analysis.quartiles.copy()
            quartiles["accuracy_pct"] = quartiles["accuracy"] * 100
            st.bar_chart(quartiles.set_index("quartile")[["mean_time_sec", "accuracy_pct"]])
            st.info(_time_accuracy_interpretation(section, quartiles))

        with c2:
            st.markdown("**Cap rule and payoff if you had moved on**")
            cap = analysis.time_cap
            cap_df = pd.DataFrame(
                {
                    "Band": ["<= cap", "> cap"],
                    "Accuracy (%)": [cap["accuracy_below_cap"] * 100, cap["accuracy_above_cap"] * 100],
                    "Count": [cap["below_cap_count"], cap["above_cap_count"]],
                }
            )
            st.bar_chart(cap_df.set_index("Band")[["Accuracy (%)", "Count"]])
            st.info(_cap_interpretation(section, cap, analysis.decision_payoff))

        c3, c4 = st.columns(2)
        with c3:
            st.markdown("**Question order drift**")
            ordered = (
                questions_df[questions_df["section"] == section]
                .sort_values("question_index")
                .reset_index(drop=True)
                .copy()
            )
            window = analysis.order_drift["rolling_window"]
            ordered["rolling_avg_time_sec"] = ordered["time_spent_sec"].rolling(window=window, min_periods=window).mean()
            ordered["rolling_accuracy_pct"] = ordered["is_correct"].rolling(window=window, min_periods=window).mean() * 100
            st.line_chart(ordered.set_index("question_index")[["rolling_avg_time_sec", "rolling_accuracy_pct"]])
            st.info(_drift_interpretation(section, analysis.order_drift))

        with c4:
            st.markdown("**Time you spent that didn't buy points**")
            slow = analysis.slow_wrong
            threshold = slow["slow_threshold_sec"]
            sink_df = ordered.copy()
            sink_df["is_sink"] = (sink_df["time_spent_sec"] >= threshold) & (~sink_df["is_correct"])
            sink_counts = sink_df["is_sink"].value_counts().rename(index={True: "Slow+Wrong", False: "Other"})
            st.bar_chart(sink_counts)
            st.info(_slow_wrong_interpretation(section, slow, total_sec_q))

    st.subheader("Ranked Point Leaks")
    leaks_df = pd.DataFrame(synthesis_output["top_leaks"])
    leaks_df["impact_pct"] = leaks_df["impact"] * 100
    st.dataframe(
        leaks_df[["section", "impact_pct", "cap_justified", "slow_wrong_guardrail"]]
        .rename(columns={"impact_pct": "Impact (%)", "cap_justified": "Cap Justified", "slow_wrong_guardrail": "Slow+Wrong Guardrail"}),
        use_container_width=True,
        hide_index=True,
    )

    st.subheader("Section Aggregates")
    display_agg = section_aggregates.copy()
    display_agg["accuracy"] = (display_agg["accuracy"] * 100).round(1)
    display_agg = display_agg.rename(columns={"accuracy": "accuracy (%)"})
    st.dataframe(display_agg, use_container_width=True, hide_index=True)


if __name__ == "__main__":
    render_dashboard()
