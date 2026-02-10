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
    text = (
        f"{section}: Peak quartile accuracy occurs around {_fmt_sec(float(best['mean_time_sec']))} "
        f"({best['quartile']})."
    )
    if len(q3) and len(q4):
        q3_acc = float(q3["accuracy"].iloc[0])
        q4_acc = float(q4["accuracy"].iloc[0])
        if q4_acc <= q3_acc:
            text += " Accuracy plateaus or drops from Q3 → Q4, so extra time shows diminishing returns."
    return text


def _cap_interpretation(section: str, time_cap: dict) -> str:
    hard_cap = int(round(time_cap["hard_cap_sec"] / 5.0) * 5)
    below = time_cap["accuracy_below_cap"]
    above = time_cap["accuracy_above_cap"]
    if time_cap["is_cap_justified"]:
        return (
            f"{section}: Accuracy at/under cap ({_fmt_pct(below)}) is not worse than above cap "
            f"({_fmt_pct(above)}). Hard cap at {hard_cap}s is empirically justified."
        )
    return (
        f"{section}: Above-cap accuracy ({_fmt_pct(above)}) beats below-cap ({_fmt_pct(below)}), "
        f"so hold a provisional {hard_cap}s cap and re-check next exam."
    )


def _drift_interpretation(section: str, order_drift: dict) -> str:
    thirds = order_drift["thirds"]
    early = thirds["early"]
    middle = thirds["middle"]
    late = thirds["late"]
    if order_drift["front_loading_flag"]:
        return (
            f"{section}: Early pacing is heavier ({_fmt_sec(early['avg_time_sec'])}) than middle "
            f"({_fmt_sec(middle['avg_time_sec'])}) and late ({_fmt_sec(late['avg_time_sec'])}) without accuracy gain. "
            "This supports equalized pacing instead of early overspending."
        )
    return (
        f"{section}: No strong front-loading penalty detected (early {_fmt_sec(early['avg_time_sec'])}, "
        f"late {_fmt_sec(late['avg_time_sec'])}). Maintain steady pacing discipline."
    )


def _slow_wrong_interpretation(section: str, slow_wrong: dict, total_questions: int) -> str:
    slow_wrong_count = slow_wrong["slow_wrong_count"]
    pct = slow_wrong["slow_wrong_pct"]
    if slow_wrong["guardrail_met"]:
        return (
            f"{pct * 100:.0f}% of {section} questions were slow + wrong ({slow_wrong_count}/{total_questions}) — "
            "these are execution sinks, not content wins."
        )
    return (
        f"{section}: slow+wrong is {pct * 100:.0f}% ({slow_wrong_count}/{total_questions}); below action guardrail "
        "(<5 questions), so prioritize caps before deep review."
    )


def render_dashboard() -> None:
    st.set_page_config(page_title="MCAT Time Allocation Optimization Engine", layout="wide")
    st.title("MCAT Time Allocation Optimization Engine")
    st.caption("Execution-first dashboard for one exam: hard caps, pacing drift, and 48–72 hour prescriptions.")

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

    st.subheader("Phase 1 Modules — Graphs + Interpretation")

    for section in sorted(analyses):
        analysis = analyses[section]
        total_sec_q = int((questions_df["section"] == section).sum())
        st.markdown(f"### {section}")

        c1, c2 = st.columns(2)
        with c1:
            st.markdown("**Module 1: Time–Accuracy Curve (quartiles)**")
            quartiles = analysis.quartiles.copy()
            quartiles["accuracy_pct"] = quartiles["accuracy"] * 100
            st.bar_chart(quartiles.set_index("quartile")[["mean_time_sec", "accuracy_pct"]])
            st.info(_time_accuracy_interpretation(section, quartiles))

        with c2:
            st.markdown("**Module 2: Time Cap Derivation**")
            cap = analysis.time_cap
            cap_df = pd.DataFrame(
                {
                    "Band": ["<= cap", "> cap"],
                    "Accuracy (%)": [cap["accuracy_below_cap"] * 100, cap["accuracy_above_cap"] * 100],
                    "Count": [cap["below_cap_count"], cap["above_cap_count"]],
                }
            )
            st.bar_chart(cap_df.set_index("Band")[["Accuracy (%)", "Count"]])
            st.info(_cap_interpretation(section, cap))

        c3, c4 = st.columns(2)
        with c3:
            st.markdown("**Module 3: Question Order Drift**")
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
            st.markdown("**Module 4: Slow–Wrong Execution Sink**")
            slow = analysis.slow_wrong
            threshold = slow["slow_threshold_sec"]
            sink_df = ordered.copy()
            sink_df["is_sink"] = (sink_df["time_spent_sec"] >= threshold) & (~sink_df["is_correct"])
            sink_counts = sink_df["is_sink"].value_counts().rename(index={True: "Slow+Wrong", False: "Other"})
            st.bar_chart(sink_counts)
            st.info(_slow_wrong_interpretation(section, slow, total_sec_q))

    st.subheader("Phase 2 — Ranked Point Leaks")
    leaks_df = pd.DataFrame(synthesis_output["top_leaks"])
    leaks_df["impact_pct"] = leaks_df["impact"] * 100
    st.dataframe(
        leaks_df[["section", "impact_pct", "cap_justified", "slow_wrong_guardrail"]]
        .rename(columns={"impact_pct": "Impact (%)", "cap_justified": "Cap Justified", "slow_wrong_guardrail": "Slow+Wrong Guardrail"}),
        use_container_width=True,
        hide_index=True,
    )

    st.subheader("Per-Section Non-Negotiable Rules")
    for section in sorted(synthesis_output["sections"]):
        with st.expander(f"{section} execution constraints", expanded=True):
            for rule in synthesis_output["sections"][section]["rules"]:
                st.markdown(f"- {rule}")

    st.subheader("Phase 3 — 48–72 Hour Practice Prescriptions")
    for section in sorted(synthesis_output["sections"]):
        pb = synthesis_output["sections"][section]["practice_block"]
        st.markdown(
            f"**{section}:** {pb['duration_min']} min block, {pb['question_target']} questions, one rule enforced: "
            f"_{pb['single_rule']}_"
        )
        st.caption(
            "Review focus: what cue should have triggered a faster decision? Do not fully re-solve. "
            "Success = lower cap violations and lower time variance."
        )

    st.subheader("Recommendations (Qualitative, behavior-hosted)")
    st.markdown(
        "- Treat hard caps as commitment devices, not optional advice.\n"
        "- Preserve cognitive bandwidth: unresolved by 30s setup-recognition → eliminate + move.\n"
        "- Debrief only trigger misses (why you stayed too long), not content rabbit holes.\n"
        "- Judge next sessions by pacing variance and cap violations first; score changes are lagging indicators."
    )

    st.subheader("Phase 4 — Core Message")
    st.success(synthesis_output["core_message"])

    st.subheader("Section Aggregates")
    display_agg = section_aggregates.copy()
    display_agg["accuracy"] = (display_agg["accuracy"] * 100).round(1)
    display_agg = display_agg.rename(columns={"accuracy": "accuracy (%)"})
    st.dataframe(display_agg, use_container_width=True, hide_index=True)


if __name__ == "__main__":
    render_dashboard()
