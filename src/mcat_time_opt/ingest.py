from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re
from typing import Dict, List, Tuple

import pandas as pd


TIME_RE = re.compile(
    r"^\s*(?:(?P<mins>\d+)\s*min(?:ute)?s?)?\s*(?:(?P<secs>\d+)\s*sec(?:ond)?s?)?\s*$",
    re.IGNORECASE,
)

FILE_RE = re.compile(r"^(correct|incorrect)_table_([A-Z]+)_test\d+\.csv$", re.IGNORECASE)


@dataclass
class IngestResult:
    questions_df: pd.DataFrame
    section_aggregates: pd.DataFrame



def parse_time_spent_to_seconds(value: str) -> float:
    """Parse strings like '2 mins 1 sec', '38 secs', '1 min' into float seconds."""
    if pd.isna(value):
        raise ValueError("time_spent cannot be null")
    text = str(value).strip()
    match = TIME_RE.match(text)
    if not match:
        raise ValueError(f"Invalid time_spent format: {value!r}")
    mins = int(match.group("mins") or 0)
    secs = int(match.group("secs") or 0)
    total = mins * 60 + secs
    if total < 0:
        raise ValueError(f"time_spent must be >= 0: {value!r}")
    if total == 0:
        total = 1
    return float(total)


def _parse_file_metadata(path: Path) -> Tuple[str, bool]:
    match = FILE_RE.match(path.name)
    if not match:
        raise ValueError(f"Unexpected file naming format: {path.name}")
    correctness, section = match.groups()
    return section.upper(), correctness.lower() == "correct"


def _load_single_file(path: Path) -> pd.DataFrame:
    section, is_correct = _parse_file_metadata(path)
    df = pd.read_csv(path)

    required = {"Question", "Correctness", "time_spent"}
    missing = required.difference(df.columns)
    if missing:
        raise ValueError(f"{path.name} missing columns: {sorted(missing)}")

    out = pd.DataFrame(
        {
            "question_index": pd.to_numeric(df["Question"], errors="raise").astype(int),
            "is_correct": is_correct,
            "time_spent_sec": df["time_spent"].apply(parse_time_spent_to_seconds).astype(float),
            "section": section,
        }
    )
    return out


def load_exam_data(input_dir: str | Path) -> IngestResult:
    """Load and normalize all section CSVs in an exam folder."""
    directory = Path(input_dir)
    csv_paths = sorted(directory.glob("*.csv"))
    if not csv_paths:
        raise ValueError(f"No CSV files found in {directory}")

    rows: List[pd.DataFrame] = []
    for path in csv_paths:
        rows.append(_load_single_file(path))

    questions_df = pd.concat(rows, ignore_index=True).sort_values(["section", "question_index"]).reset_index(drop=True)

    if questions_df["time_spent_sec"].isna().any():
        raise ValueError("Found null values in time_spent_sec")
    if (questions_df["time_spent_sec"] <= 0).any():
        raise ValueError("Found non-positive values in time_spent_sec")

    dupes = questions_df.duplicated(subset=["section", "question_index"], keep=False)
    if dupes.any():
        dup_rows = questions_df.loc[dupes, ["section", "question_index"]].drop_duplicates().to_dict("records")
        raise ValueError(f"Found duplicate (section, question_index): {dup_rows}")

    section_aggregates = (
        questions_df.groupby("section", as_index=False)
        .agg(
            total_questions=("question_index", "count"),
            mean_time_sec=("time_spent_sec", "mean"),
            median_time_sec=("time_spent_sec", "median"),
            accuracy=("is_correct", "mean"),
        )
        .sort_values("section")
        .reset_index(drop=True)
    )

    return IngestResult(questions_df=questions_df, section_aggregates=section_aggregates)
