# CardioRAG — Templates Directory

This directory contains evaluation and benchmarking templates for the CardioRAG system.

---

## 📊 [`Day2_Retrieval_Scorecard_Template.xlsx`](file:///d:/AI/cardiorag/templates/Day2_Retrieval_Scorecard_Template.xlsx)

A working Excel scorecard with live formulas and conditional formatting designed to keep retrieval numbers honest.

### Features:
1. **Live Excel Formulas**:
   - **Precision@5** (`Column K`): Calculates $\frac{\sum \text{Chunk 1..5}}{5}$ automatically (or evaluates out-of-scope refusal accuracy).
   - **Hit@5 / Found?** (`Column L`): Automatically evaluates `YES`, `NO`, `Refusal Pass`, or `Refusal Fail`.
   - **First Hit Rank** (`Column M`): Identifies the rank of the first relevant chunk ($1 \dots 5$).
   - **Reciprocal Rank** (`Column N`): Computes $\frac{1}{\text{rank}}$ for Mean Reciprocal Rank (MRR).
2. **KPI Summary Header Cards**:
   - **Team Average Precision@5**: `=AVERAGE(K9:K24)`
   - **Overall Hit Rate (Found? %)**: `=COUNTIF(L9:L24, "YES")/(COUNTA(C9:C24)-COUNTIF(D9:D24, "*expect refusal*"))`
   - **Refusal Accuracy %**: `=COUNTIF(L9:L24, "Refusal Pass")/COUNTIF(D9:D24, "*expect refusal*")`
   - **Mean Reciprocal Rank (MRR)**: `=AVERAGE(N9:N24)`
3. **Conditional Formatting**:
   - 🔴 **Red Flag**: Highlights weak questions in red where $\text{Precision@5} < 20\%$, `Hit@5 = NO`, or `Refusal Fail`.
   - 🟢 **Green Flag**: Highlights strong retrieval ($\ge 40\%$) and verified hits.
4. **Sheet 2: Facilitator Spot-Check Log**:
   - Dedicated audit log sheet for in-person facilitator verification.

---

## 🛠️ Generator Script:
- [`generate_scorecard_template.py`](file:///d:/AI/cardiorag/templates/generate_scorecard_template.py): Python script to rebuild or customize the `.xlsx` template.
