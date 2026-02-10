from __future__ import annotations

from pathlib import Path
import re

import pandas as pd
import streamlit as st

DATA_DIR = Path("data/exam_1")
SECTION_FILES = {
    "BB": ("correct_table_BB_test1.csv", "incorrect_table_BB_test1.csv"),
    "CARS": ("correct_table_CARS_test1.csv", "incorrect_table_CARS_test1.csv"),
    "CP": ("correct_table_CP_test1.csv", "incorrect_table_CP_test1.csv"),
    "PSB": ("correct_table_PSB_test1.csv", "incorrect_table_PSB_test1.csv"),
}


def parse_time_to_seconds(value: str) -> int:
    text = str(value).strip().lower()
    if not text:
        return 0

    mins_match = re.search(r"(\d+)\s*min", text)
    secs_match = re.search(r"(\d+)\s*sec", text)

    minutes = int(mins_match.group(1)) if mins_match else 0
    seconds = int(secs_match.group(1)) if secs_match else 0

    if minutes == 0 and seconds == 0 and text.isdigit():
        return int(text)

    return minutes * 60 + seconds


@st.cache_data
def load_exam_data() -> tuple[pd.DataFrame, pd.DataFrame]:
    section_rows = []
    question_rows = []

    for section, (correct_file, incorrect_file) in SECTION_FILES.items():
        correct_path = DATA_DIR / correct_file
        incorrect_path = DATA_DIR / incorrect_file

        correct_df = pd.read_csv(correct_path)
        incorrect_df = pd.read_csv(incorrect_path)

        correct_df["Correctness"] = "correct"
        incorrect_df["Correctness"] = "incorrect"

        combined = pd.concat([correct_df, incorrect_df], ignore_index=True)
        combined["Section"] = section
        combined["time_seconds"] = combined["time_spent"].map(parse_time_to_seconds)

        total_questions = len(combined)
        correct_answers = int((combined["Correctness"] == "correct").sum())
        accuracy = (correct_answers / total_questions) * 100 if total_questions else 0.0
        avg_time = combined["time_seconds"].mean() if total_questions else 0.0

        section_rows.append(
            {
                "Section": section,
                "Questions": total_questions,
                "Correct": correct_answers,
                "Incorrect": total_questions - correct_answers,
                "Accuracy (%)": round(accuracy, 1),
                "Avg Time (sec)": round(avg_time, 1),
            }
        )

        question_rows.append(combined)

    section_df = pd.DataFrame(section_rows).sort_values("Section")
    question_df = pd.concat(question_rows, ignore_index=True)
    return section_df, question_df


def render_dashboard() -> None:
    st.set_page_config(page_title="MCAT Study Helper Dashboard", layout="wide")
    st.title("MCAT Study Helper Dashboard")
    st.caption("Quick visual summary of section performance from exam_1 CSV exports.")

    section_df, question_df = load_exam_data()

    total_questions = int(section_df["Questions"].sum())
    total_correct = int(section_df["Correct"].sum())
    overall_accuracy = (total_correct / total_questions) * 100 if total_questions else 0.0

    kpi_1, kpi_2, kpi_3 = st.columns(3)
    kpi_1.metric("Total Questions", total_questions)
    kpi_2.metric("Total Correct", total_correct)
    kpi_3.metric("Overall Accuracy", f"{overall_accuracy:.1f}%")

    col_1, col_2 = st.columns(2)

    with col_1:
        st.subheader("Accuracy by Section")
        st.bar_chart(section_df.set_index("Section")["Accuracy (%)"])

    with col_2:
        st.subheader("Average Time per Question (seconds)")
        st.bar_chart(section_df.set_index("Section")["Avg Time (sec)"])

    st.subheader("Section Summary")
    st.dataframe(section_df, use_container_width=True)

    st.subheader("Question-level View")
    selected_section = st.selectbox("Filter by section", ["All"] + sorted(SECTION_FILES.keys()))

    filtered = question_df.copy()
    if selected_section != "All":
        filtered = filtered[filtered["Section"] == selected_section]

    st.dataframe(
        filtered[["Section", "Question", "Correctness", "time_spent", "time_seconds"]]
        .sort_values(["Section", "Question"])
        .reset_index(drop=True),
        use_container_width=True,
    )


if __name__ == "__main__":
    render_dashboard()
