# MCAT Time Allocation Optimization Report (Exam 1)

## Top 3 Findings

1. **PSB**: high-impact timing leak (impact index 40.7%); cap justified=True.
2. **BB**: high-impact timing leak (impact index 33.9%); cap justified=True.
3. **CP**: high-impact timing leak (impact index 13.6%); cap justified=False.

## Per-Section Time Rules

### BB
- Questions: 59
- Accuracy: 30.5%
- Median time: 62s
- Hard cap: 75s
- Findings:
  - BB: peak quartile accuracy is 37.5% at ~16s (Q1).
  - BB: accuracy <= cap is 33.3% vs > cap 25.0%.
  - BB: accuracy plateaus/drops from Q3 to Q4, indicating diminishing returns.
- Rules:
  - Hard stop at 75s in BB. If unresolved, eliminate and guess immediately.
  - BB: treat slow+wrong items as execution sinks; cap and move on when setup is unclear by 30s.

### CARS
- Questions: 53
- Accuracy: 32.1%
- Median time: 54s
- Hard cap: 65s
- Findings:
  - CARS: peak quartile accuracy is 46.2% at ~269s (Q4).
  - CARS: accuracy <= cap is 29.4% vs > cap 36.8%.
- Rules:
  - Provisional cap at 65s in CARS; monitor next session and tighten only if >cap accuracy stays flat.
  - CARS: treat slow+wrong items as execution sinks; cap and move on when setup is unclear by 30s.

### CP
- Questions: 59
- Accuracy: 35.6%
- Median time: 49s
- Hard cap: 60s
- Findings:
  - CP: peak quartile accuracy is 46.7% at ~224s (Q4).
  - CP: accuracy <= cap is 28.1% vs > cap 44.4%.
- Rules:
  - Provisional cap at 60s in CP; monitor next session and tighten only if >cap accuracy stays flat.
  - CP: treat slow+wrong items as execution sinks; cap and move on when setup is unclear by 30s.

### PSB
- Questions: 59
- Accuracy: 39.0%
- Median time: 62s
- Hard cap: 75s
- Findings:
  - PSB: peak quartile accuracy is 46.7% at ~11s (Q1).
  - PSB: accuracy <= cap is 40.0% vs > cap 37.5%.
  - PSB: accuracy plateaus/drops from Q3 to Q4, indicating diminishing returns.
- Rules:
  - Hard stop at 75s in PSB. If unresolved, eliminate and guess immediately.
  - PSB: treat slow+wrong items as execution sinks; cap and move on when setup is unclear by 30s.

## 2–3 Day Plan

### BB Next Session
- Block: 35 minutes, 28 questions, 75s cap
- Enforced rule: Hard stop at 75s in BB. If unresolved, eliminate and guess immediately.
- Review: Review only the missed trigger for earlier decision; do not fully re-solve.
- Success metrics:
  - Cap-violation rate decreases
  - Time variance narrows

### CARS Next Session
- Block: 35 minutes, 32 questions, 65s cap
- Enforced rule: Provisional cap at 65s in CARS; monitor next session and tighten only if >cap accuracy stays flat.
- Review: Review only the missed trigger for earlier decision; do not fully re-solve.
- Success metrics:
  - Cap-violation rate decreases
  - Time variance narrows

### CP Next Session
- Block: 35 minutes, 35 questions, 60s cap
- Enforced rule: Provisional cap at 60s in CP; monitor next session and tighten only if >cap accuracy stays flat.
- Review: Review only the missed trigger for earlier decision; do not fully re-solve.
- Success metrics:
  - Cap-violation rate decreases
  - Time variance narrows

### PSB Next Session
- Block: 35 minutes, 28 questions, 75s cap
- Enforced rule: Hard stop at 75s in PSB. If unresolved, eliminate and guess immediately.
- Review: Review only the missed trigger for earlier decision; do not fully re-solve.
- Success metrics:
  - Cap-violation rate decreases
  - Time variance narrows

## Core Message

Spending more time did not reliably increase accuracy. Faster decisions are a rational reallocation, not blind guessing.
