from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Any

import pandas as pd


@dataclass
class SectionAnalysis:
    section: str
    quartiles: pd.DataFrame
    time_cap: Dict[str, Any]
    order_drift: Dict[str, Any]
    slow_wrong: Dict[str, Any]


def _third_metrics(df: pd.DataFrame) -> Dict[str, Dict[str, float]]:
    n = len(df)
    bounds = [0, n // 3, (2 * n) // 3, n]
    labels = ["early", "middle", "late"]
    result = {}
    for i, label in enumerate(labels):
        chunk = df.iloc[bounds[i] : bounds[i + 1]]
        if len(chunk) == 0:
            result[label] = {"avg_time_sec": float("nan"), "accuracy": float("nan")}
        else:
            result[label] = {
                "avg_time_sec": float(chunk["time_spent_sec"].mean()),
                "accuracy": float(chunk["is_correct"].mean()),
            }
    return result


def analyze_section(section_df: pd.DataFrame, rolling_window: int = 8) -> SectionAnalysis:
    section = str(section_df["section"].iloc[0])

    sorted_by_time = section_df.sort_values("time_spent_sec").copy()
    sorted_by_time["quartile"] = pd.qcut(
        sorted_by_time["time_spent_sec"], q=4, labels=["Q1", "Q2", "Q3", "Q4"], duplicates="drop"
    )
    quartiles = (
        sorted_by_time.groupby("quartile", observed=True)
        .agg(
            questions=("question_index", "count"),
            mean_time_sec=("time_spent_sec", "mean"),
            accuracy=("is_correct", "mean"),
        )
        .reset_index()
    )

    median_time = float(section_df["time_spent_sec"].median())
    hard_cap = median_time * 1.2
    below = section_df[section_df["time_spent_sec"] <= hard_cap]
    above = section_df[section_df["time_spent_sec"] > hard_cap]
    acc_below = float(below["is_correct"].mean()) if len(below) else 0.0
    acc_above = float(above["is_correct"].mean()) if len(above) else 0.0

    time_cap = {
        "median_time_sec": median_time,
        "hard_cap_sec": hard_cap,
        "accuracy_below_cap": acc_below,
        "accuracy_above_cap": acc_above,
        "is_cap_justified": acc_above <= acc_below,
        "below_cap_count": int(len(below)),
        "above_cap_count": int(len(above)),
    }

    ordered = section_df.sort_values("question_index").copy()
    window = max(3, min(rolling_window, len(ordered)))
    ordered["rolling_avg_time_sec"] = ordered["time_spent_sec"].rolling(window=window, min_periods=window).mean()
    ordered["rolling_accuracy"] = ordered["is_correct"].rolling(window=window, min_periods=window).mean()
    thirds = _third_metrics(ordered)

    early_time = thirds["early"]["avg_time_sec"]
    middle_time = thirds["middle"]["avg_time_sec"]
    late_time = thirds["late"]["avg_time_sec"]
    early_acc = thirds["early"]["accuracy"]
    late_acc = thirds["late"]["accuracy"]

    order_drift = {
        "rolling_window": window,
        "thirds": thirds,
        "early_minus_late_time_sec": float(early_time - late_time),
        "early_minus_late_accuracy": float(early_acc - late_acc),
        "front_loading_flag": bool(early_time > middle_time and early_time > late_time and early_acc <= late_acc),
    }

    slow_threshold = float(section_df["time_spent_sec"].quantile(0.75))
    slow_wrong_df = section_df[(section_df["time_spent_sec"] >= slow_threshold) & (~section_df["is_correct"])]
    slow_wrong = {
        "slow_threshold_sec": slow_threshold,
        "slow_wrong_count": int(len(slow_wrong_df)),
        "slow_wrong_pct": float(len(slow_wrong_df) / len(section_df)),
        "guardrail_met": bool(len(slow_wrong_df) >= 5),
    }

    return SectionAnalysis(
        section=section,
        quartiles=quartiles,
        time_cap=time_cap,
        order_drift=order_drift,
        slow_wrong=slow_wrong,
    )


def run_analysis(questions_df: pd.DataFrame, rolling_window: int = 8) -> Dict[str, SectionAnalysis]:
    analyses: Dict[str, SectionAnalysis] = {}
    for section, section_df in questions_df.groupby("section"):
        analyses[section] = analyze_section(section_df.copy(), rolling_window=rolling_window)
    return analyses
