# MCAT Time Allocation Optimization Engine — Project Definition (v1)

## Project Goal
Build a lightweight, reliable analysis engine that ingests **one exam's section data** and outputs **behavior-changing time-management rules** plus a **48–72 hour practice plan**.

The focus is execution optimization:
- Faster, more rational decisions
- Hard time caps
- Reduced time variance
- Elimination of “more time always helps” thinking

Not in scope for v1:
- Content mastery diagnosis
- Machine learning
- Multi-exam trend modeling

---

## Why this project now
You already have actionable timing data in `data/exam_1`. This project turns that data into strict rules you can execute tomorrow.

Primary success criterion: outputs must make next-session behavior measurably different.

---

## Available Data (Current Reality)
Data is in section-specific CSVs split by correctness buckets, e.g.:
- `correct_table_CP_test1.csv`
- `incorrect_table_CP_test1.csv`
(and similarly for CARS, BB, PSB).

Observed schema in each file:
- `Question`
- `Correctness`
- `time_spent`

Important implementation note:
- `time_spent` is currently a **string duration** (e.g., `"2 mins 1 sec"`, `"38 secs"`), not numeric seconds.
- Correct and incorrect responses are in separate files and must be merged per section.

---

## Product Outputs (v1)
Single human-readable report (Markdown) containing:
1. **Top 3 findings** across sections
2. **Per-section hard time rules**
3. **48–72 hour practice prescription** (session blocks + success metrics)
4. **One anxiety reframe message** grounded in observed data

Optional structured artifact (recommended):
- JSON summary for downstream automation/UI later

---

## Execution Plan

### Phase 0 — Ingestion & Normalization (first)
Create a robust loader that:
1. Reads all section files from `data/exam_1`
2. Parses section labels (`CP`, `CARS`, `BB`, `PSB`) from filenames
3. Converts `time_spent` strings into `time_spent_sec: float`
4. Normalizes to canonical fields:
   - `question_index` (int)
   - `is_correct` (bool)
   - `time_spent_sec` (float)
   - `section` (str)
5. Merges correct + incorrect rows into one per-section table
6. Validates:
   - no null times
   - `time_spent_sec > 0`
   - unique `(section, question_index)`

Deliverables:
- `questions_df` runtime DataFrame
- section summary stats (N, mean/median time, accuracy)

---

### Phase 1 — Core Analysis Modules (strict order)

#### Module 1: Time–Accuracy Curve
Per section:
- sort by `time_spent_sec`
- split into quartiles (fastest→slowest)
- compute quartile mean time + accuracy
- detect diminishing returns (Q3→Q4 plateau/drop)
- identify peak-accuracy time band

#### Module 2: Time Cap Derivation
Per section:
- `hard_cap = median_time * 1.2`
- compare accuracy for `<= hard_cap` vs `> hard_cap`
- if above-cap accuracy does not improve, cap is justified

#### Module 3: Question Order Drift
Per section:
- rolling window (size 7–10) over question order
- rolling average time and accuracy
- compare early/middle/late thirds for front-loading pattern

#### Module 4: Slow–Wrong Identification
Per section:
- `slow_threshold = p75(time_spent_sec)`
- detect rows that are both slow and wrong
- report only if count >= 5

---

### Phase 2 — Synthesis Engine
No new analytics. Only ranking and converting insights to action.

1. Rank point leaks by:
   - % questions affected
   - strength of evidence (flat/negative return)
2. Emit section-specific non-negotiable execution rules, e.g.:
   - “Hard stop at 80s in CP. Guess immediately.”
   - “First 20 questions must average <= median time.”

---

### Phase 3 — Practice Prescription (48–72h)
For each section requiring intervention:
- Session duration: 30–45 min
- Question count: derived from cap × session duration
- One enforced rule per session (no stacking)
- Review only trigger-recognition failures (no full re-solves)
- Success metrics:
  - lower cap violation rate
  - reduced time variance

---

### Phase 4 — Report Generation
Generate one Markdown report with fixed layout:
1. Top 3 Findings
2. Per-Section Time Rules
3. 2–3 Day Plan
4. Core Message / Anxiety Reframe

Tone requirement:
- precise, direct, constraint-focused
- no speculative psychology

---

### Phase 5 — Extension Hooks (document only)
Mark TODO hooks for:
- multi-exam aggregation
- cap stabilization across exams
- topic/time interaction once topic tags exist

---

## Technical Architecture (minimal)
Suggested package layout:
- `src/mcat_time_opt/ingest.py`
- `src/mcat_time_opt/analysis.py`
- `src/mcat_time_opt/synthesis.py`
- `src/mcat_time_opt/report.py`
- `src/mcat_time_opt/cli.py`

CLI contract (initial):
- input dir (`data/exam_1`)
- output report path (`outputs/report_exam_1.md`)

No database, no services, no UI needed for v1.

---

## Decision Rules & Guardrails
- Ship only findings that can alter next practice behavior
- Prefer hard thresholds over nuanced prose
- Do not infer causality beyond observed timing-performance relationships
- If evidence is weak in a section, explicitly state low confidence and avoid over-prescription

---

## Definition of Done (v1)
- Ingestion handles current raw duration strings + split correctness files
- All four analysis modules run per section without manual edits
- Report generated with clear section caps and practice plan
- At least one explicit justification per section for speeding decisions or equalized pacing

---

## Immediate Next Build Steps
1. Implement duration parser (`"X mins Y secs"` → seconds)
2. Build ingestion/merge pipeline for split correct/incorrect files
3. Implement Module 1 + Module 2 first (highest impact)
4. Add Module 3 + Module 4
5. Generate first report from `exam_1`
6. Review output quality and tighten rule wording

---

## Open Questions
1. Should `PSB` be labeled as `PS` in all output, or keep `PSB` exactly as in filenames?
2. For rolling windows, do you prefer fixed size `7` or auto-select between `7–10` based on section length?
3. For cap rounding in final rules, do you want nearest **5 sec**, **10 sec**, or exact seconds?
4. Should we emit both Markdown and JSON now, or Markdown only for the first iteration?

