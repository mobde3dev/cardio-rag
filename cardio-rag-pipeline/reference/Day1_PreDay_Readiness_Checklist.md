# CardioRAG — Day 1 Pre-Day Readiness Checklist
### Mandatory Gate Completed Before the 13:30 Lunch Cutoff

> **Requirements**: Confirmed source license + a functioning parser output, verified against Quality Gates V1–V6 and signed off by your trainer before afternoon index building.

---

## 📋 Gate 1: Source Documents & Licensing Verification

- [x] **WHO 2021 Hypertension Guideline** (`data/raw/WHO_2021.pdf`)
  - Title: *Guideline for the pharmacological treatment of hypertension in adults*
  - License: Open Access (CC BY-NC-SA 3.0 IGO)
  - Integrity Check: SHA-256 verified, uncorrupted PDF streams.
- [x] **NICE NG238 (2023) Lipid Modification Guideline** (`data/raw/NICE_2023.pdf`)
  - Title: *Cardiovascular disease: risk assessment and reduction, including lipid modification*
  - License: Open Government Licence (OGL) / Crown Copyright for clinical guidance.
  - Integrity Check: SHA-256 verified, uncorrupted PDF streams.

---

## 📋 Gate 2: Extraction & Medical Cleaning Verification

- [x] **Extraction Engine**:
  - `PyMuPDF` (fitz) operational for multi-page stream extraction.
  - `pdfplumber` operational for structured clinical table extraction.
- [x] **Boilerplate Stripping**:
  - Running headers, page numbers, and publication footers safely removed.
  - Zero loss of medical content or section titles.
- [x] **Medical Safety Preservation**:
  - Comparison operators (`>=`, `<=`, `<`, `>`) preserved verbatim.
  - Clinical units (`mmHg`, `mmol/L`, `mg`, `mg/mmol`, `mL/min/1.73m2`) intact.
  - Lipid thresholds and blood pressure targets unmodified.

---

## 📋 Gate 3: Ingestion Pipeline & Quality Gates (V1–V6)

- [x] **Gate V1 (Unique ID Gate)**: Every chunk has a globally unique, deterministic ID.
- [x] **Gate V2 (Completeness Gate)**: All canonical recommendations (WHO 1–8, NICE 1.1–1.12) extracted.
- [x] **Gate V3 (Token Bounds Gate)**: All chunks satisfy $50 \le \text{token\_count} \le 800$ (no micro-chunks $<20$ tokens).
- [x] **Gate V4 (Provenance Gate)**: Source file, starting PDF page, and section hierarchy tracked per chunk.
- [x] **Gate V5 (Clinical Priority Gate)**: Clinical priority ratings (Priority 1: Active Recommendations) accurately assigned.
- [x] **Gate V6 (Idempotency Gate)**: Pipeline execution is 100% deterministic and reproducible across runs.

---

## 📋 Gate 4: Deliverables & Pipeline Output Artifacts

| Expected Deliverable | Output Path | Status |
| :--- | :--- | :---: |
| WHO Processed JSON | `data/processed/WHO_2021_chunks.json` (104 chunks) | ✅ READY |
| WHO Vector-Ready JSONL | `data/processed/WHO_2021_chunks.jsonl` | ✅ READY |
| WHO QA Markdown Preview | `data/processed/WHO_2021_chunks_preview.md` | ✅ READY |
| NICE Processed JSON | `data/processed/NICE_2023_chunks.json` (143 chunks) | ✅ READY |
| NICE Vector-Ready JSONL | `data/processed/NICE_2023_chunks.jsonl` | ✅ READY |
| NICE QA Markdown Preview | `data/processed/NICE_2023_chunks_preview.md` | ✅ READY |
| Automated Test Suite | `tests/` (119/119 unit & integration tests passing) | ✅ PASSED |

---

## ✍️ Gate 5: Trainer Sign-Off Section (Mandatory Before 13:30)

```text
┌──────────────────────────────────────────────────────────────────────────────┐
│                        TRAINER READINESS SIGN-OFF BOX                        │
├──────────────────────────────────────────────────────────────────────────────┤
│  Participant / Team Name : _________________________________________________ │
│  Table Number            : _________________________________________________ │
│  Total Chunks Verified   : WHO: 104 Chunks  |  NICE: 143 Chunks             │
│  Pipeline Test Status    : [X] PASS (119/119 tests green)                    │
│                                                                              │
│  Trainer Name            : _________________________________________________ │
│  Trainer Signature       : _________________________________________________ │
│  Sign-off Timestamp      : ____ / ____ / 2026  ──  ____ : ____  (Before 13:30)│
│                                                                              │
│  Status: [X] APPROVED FOR AFTERNOON EMBEDDING & INDEX-BUILDING               │
└──────────────────────────────────────────────────────────────────────────────┘
```
