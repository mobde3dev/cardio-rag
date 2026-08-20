# CardioRAG — Day 2 Facilitator Spot-Check Protocol
### Mandatory Verification Protocol to Ensure Retrieval Integrity & Combat Metric Drift

> **Core Objective**: A facilitator personally audits and verifies at least one real query per team live in person before the end of Day 2. Self-reported numbers can drift — this protocol guarantees that all reported Precision@5, Hit Rate, and MRR metrics reflect actual, reproducible retriever performance.

---

## 🎯 Why Spot-Checks Exist (Anti-Drift Philosophy)

In RAG evaluation benchmarks, self-reported metrics often suffer from:
1. **Subjective Grading Bias**: Teams marking partially related chunks as relevant ($1$) when they lack the required clinical recommendation.
2. **Hardcoded / Overfitted Retrievers**: Retrievers tuned specifically on exact strings rather than generalized semantic search.
3. **Out-of-Scope Hallucination**: Failing to refuse questions not covered by the guideline (e.g. breast cancer in hypertension guideline).

---

## 📋 The 5-Step In-Person Audit Workflow

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                       5-STEP LIVE SPOT-CHECK WORKFLOW                       │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│   [ Step 1: Random Query Selection ]                                        │
│   ──► Facilitator randomly selects 1 in-scope query and 1 refusal query     │
│       from the team's scorecard.                                            │
│                                                                             │
│   [ Step 2: Live In-Person Execution ]                                      │
│   ──► The participant executes the retrieval script live in terminal/IDE    │
│       directly in front of the facilitator.                                 │
│                                                                             │
│   [ Step 3: Provenance & Chunk Metadata Audit ]                             │
│   ──► Facilitator inspects top-5 retrieved chunks:                          │
│       • Checks chunk_id and PDF page provenance against data/raw/           │
│       • Confirms no truncated or fabricated chunk boundaries                │
│                                                                             │
│   [ Step 4: Independent Relevance Verification ]                            │
│   ──► Facilitator independently grades chunk relevance (0/1) against        │
│       the clinical ground truth recommendation.                             │
│                                                                             │
│   [ Step 5: Delta Evaluation & Official Sign-off ]                          │
│   ──► Facilitator compares Reported P@5 vs Verified Live P@5:               │
│       • Delta <= 10% ──► PASS (Signed off on Scorecard & Protocol)          │
│       • Delta > 10%  ──► AUDIT FAILED (Team must re-score and re-evaluate)  │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## ⚖️ Audit Rubric & Discrepancy Rules

| Metric / Check | Tolerance Threshold | Action on Failure |
| :--- | :--- | :--- |
| **Precision@5 Delta** | $|\text{Reported} - \text{Verified}| \le 0.10$ | Re-grade entire scorecard under facilitator supervision |
| **Hit@5 Alignment** | 100% agreement on Top-1 / Top-3 | Invalidate question score |
| **Refusal Verification** | 100% refusal for out-of-scope queries | Immediate failure of refusal test |
| **Chunk Provenance** | 100% traceable to `data/raw/*.pdf` | Disqualify chunk index |

---

## ✍️ Official Facilitator Spot-Check Certification Sheet

```text
┌──────────────────────────────────────────────────────────────────────────────┐
│                    FACILITATOR LIVE SPOT-CHECK SIGN-OFF BOX                  │
├──────────────────────────────────────────────────────────────────────────────┤
│  Team / Table Number     : _________________________________________________ │
│  Participant Name(s)     : _________________________________________________ │
│                                                                              │
│  [AUDIT QUERY 1 — IN-SCOPE]                                                  │
│  Selected Query ID       : [  ] WHO_01..07   /   [  ] NICE_01..07            │
│  Query Text              : _________________________________________________ │
│  Reported Precision@5    : _________ %     Verified Live P@5 : _________ %   │
│  Top Chunk ID Retrieved  : _________________________________________________ │
│  Relevance Verified?     : [  ] YES (Matches Guideline)   [  ] NO (Irrelevant)│
│                                                                              │
│  [AUDIT QUERY 2 — OUT-OF-SCOPE REFUSAL]                                      │
│  Selected Refusal Query  : [  ] WHO_08 (Breast Cancer) / [  ] NICE_08 (Appx) │
│  Refusal Triggered Live? : [  ] YES (Clean Refusal)       [  ] NO (Hallucinated)│
│                                                                              │
│  [FINAL VERIFICATION DECISION]                                               │
│  Discrepancy Delta (Δ)   : _________ %  (Must be <= 10%)                     │
│  Audit Outcome           : [  ] PASSED & CERTIFIED     [  ] RE-EVALUATION REQ │
│                                                                              │
│  Facilitator Name        : _________________________________________________ │
│  Facilitator Signature   : _________________________________________________ │
│  Audit Timestamp         : ____ / ____ / 2026  ──  ____ : ____               │
└──────────────────────────────────────────────────────────────────────────────┘
```
