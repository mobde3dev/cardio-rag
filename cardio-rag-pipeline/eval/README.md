# CardioRAG Evaluation Test Sets & Benchmark

This directory contains medically verified evaluation test sets and evaluation tooling for the CardioRAG pipeline, benchmarked against **WHO 2021** and **NICE NG238 (2023)** clinical guidelines.

---

## 📁 Files in `eval/`

| File | Description | Target Guideline |
| :--- | :--- | :--- |
| [`Day2_Evaluation_Test_Set.csv`](file:///d:/AI/cardiorag/eval/Day2_Evaluation_Test_Set.csv) | **Module 3 Standard Test Set** (8 verified questions with blank columns for evaluation) | WHO 2021 |
| [`Day2_Evaluation_Test_Set_completed.csv`](file:///d:/AI/cardiorag/eval/Day2_Evaluation_Test_Set_completed.csv) | Populated Day 2 test set with retrieval metrics (`Found?`, `P@k`, `Top_Retrieved_Chunk`, `Top_BM25_Score`) | WHO 2021 |
| [`WHO_2021_Evaluation_Test_Set.csv`](file:///d:/AI/cardiorag/eval/WHO_2021_Evaluation_Test_Set.csv) | Extended WHO test set with exact chunk IDs, ground truth clinical answers, and section metadata | WHO 2021 |
| [`NICE_2023_Evaluation_Test_Set.csv`](file:///d:/AI/cardiorag/eval/NICE_2023_Evaluation_Test_Set.csv) | 8 verified clinical questions + refusal test for NICE 2023 lipid & CVD risk guidelines | NICE NG238 (2023) |
| [`CardioRAG_Master_Evaluation_Test_Set.csv`](file:///d:/AI/cardiorag/eval/CardioRAG_Master_Evaluation_Test_Set.csv) | **Master Unified Benchmark** (16 questions covering both guidelines + out-of-scope refusals) | WHO 2021 & NICE 2023 |
| [`evaluate_retrieval.py`](file:///d:/AI/cardiorag/eval/evaluate_retrieval.py) | Automated Python evaluation engine (BM25 + Medical Expansion + Refusal Detection) | Automated Runner |

---

## 📋 WHO 2021 Day 2 Evaluation Test Set Details

All 8 rows and page references are verified directly against `data/raw/WHO_2021.pdf` and `data/processed/WHO_2021_chunks.json`:

| # | Question | Expected Source | Expected Chunk ID | Out of Scope? |
| :-: | :--- | :--- | :--- | :-: |
| 1 | What BP threshold should trigger starting medication? | Recommendation 1, Page 3 | `WHO03_3.1_REC_001` / `WHO03_0_REC_001` | No |
| 2 | What is the target BP for a patient with known CVD? | Section 3.6, Page 9 | `WHO03_3.6_REC_002` / `WHO03_0_REC_009` | No |
| 3 | Can nurses or pharmacists prescribe treatment? | Section 3.8, Page 10 | `WHO03_3.8_REC_001` / `WHO03_0_REC_013` | No |
| 4 | What's the recommended breast cancer screening interval? | Not covered — expect refusal | `None` / `OUT_OF_SCOPE` | **Yes (Refusal)** |
| 5 | Are laboratory tests required before starting pharmacological treatment? | Recommendation 2, Page 5 | `WHO03_3.2_REC_001` / `WHO03_0_REC_004` | No |
| 6 | When should cardiovascular disease risk assessment be conducted? | Recommendation 3, Page 6 | `WHO03_3.3_REC_001` / `WHO03_0_REC_005` | No |
| 7 | Which drug classes are recommended as first-line agents for hypertension? | Recommendation 4, Page 7 | `WHO03_3.4_REC_001` / `WHO03_0_REC_006` | No |
| 8 | When is combination therapy recommended as initial treatment? | Recommendation 5, Page 8 | `WHO03_3.5_REC_001` / `WHO03_0_REC_007` | No |

---

## 📋 NICE NG238 (2023) Evaluation Test Set Details

All 8 rows and page references are verified directly against `data/raw/NICE_2023.pdf` and `data/processed/NICE_2023_chunks.json`:

| # | Question | Expected Source | Expected Chunk ID | Out of Scope? |
| :-: | :--- | :--- | :--- | :-: |
| 1 | What risk assessment tool is recommended for calculating 10-year CVD risk? | Recommendation 1.1.7, Page 5 | `NICE3_1.1.7_REC` / `NICE3_1.1.4_REC` | No |
| 2 | At what 10-year CVD risk threshold should atorvastatin 20 mg be offered for primary prevention? | Recommendation 1.6.7, Page 21 | `NICE3_1.6.7_REC` | No |
| 3 | What statin and dose is recommended for secondary prevention of CVD? | Recommendation 1.7.2, Page 26 | `NICE3_1.7.2_REC` | No |
| 4 | What is the target lipid level for secondary prevention of CVD? | Recommendation 1.7.1, Page 26 | `NICE3_1.7.1_REC` | No |
| 5 | What statin treatment is recommended for adults with chronic kidney disease (CKD)? | Recommendation 1.8.1, Page 35 | `NICE3_1.8.1_REC` | No |
| 6 | Should aspirin be routinely offered for primary prevention of CVD? | Recommendation 1.2.1, Page 13 | `NICE3_1.2.1_REC` | No |
| 7 | What treatment is recommended if statins are contraindicated or not tolerated? | Recommendation 1.10.1, Page 38 | `NICE3_1.10.1_REC` | No |
| 8 | What is the recommended antibiotic regimen for acute appendicitis? | Not covered — expect refusal | `None` / `OUT_OF_SCOPE` | **Yes (Refusal)** |

---

## 🚀 How to Run Automated Evaluation

Run the evaluation script from the project root:

```bash
python eval/evaluate_retrieval.py
```

### Metrics Computed:
- **Hit Rate (Found? %)**: Percentage of in-scope clinical queries where at least one ground truth chunk was retrieved within top-$k$.
- **Mean Precision@k ($P@k$)**: Proportion of relevant chunks among the top-$k$ retrieved chunks.
- **MRR (Mean Reciprocal Rank)**: Position penalty metric $\frac{1}{\text{rank}}$ of the first relevant chunk retrieved.
- **Out-of-Scope Refusal Accuracy**: Accuracy of recognizing queries not covered by the guideline and correctly triggering refusal without hallucination.
