# CardioRAG — Day 1 Module Timer Cards
### 5 Poster-Style Countdown Cards for Lab Tasks

> **Purpose**: Post the current card at your table during each lab task. These cards enforce time budgets and prevent source vetting from consuming index-building time.

---

## ⏱️ Card 1: Task 1 — Source Ingestion & License Verification

```
╔══════════════════════════════════════════════════════════════════════════════╗
║  CARD 1 / 5 ── TASK 1: SOURCE INGESTION & LICENSING                         ║
║  ⏱️ TIME ALLOCATED: 30 MINUTES          🎯 TARGET COMPLETION: 10:00        ║
╠══════════════════════════════════════════════════════════════════════════════╣
║                                                                              ║
║  🎯 OBJECTIVES:                                                              ║
║  1. Download official clinical guideline PDFs:                               ║
║     • WHO 2021 Hypertension Guideline (`data/raw/WHO_2021.pdf`)              ║
║     • NICE NG238 Lipid Modification Guideline (`data/raw/NICE_2023.pdf`)     ║
║  2. Confirm source licensing (Open Access / Crown Copyright OGL).            ║
║  3. Verify PDF stream integrity and sha256 checksums.                        ║
║                                                                              ║
║  🛑 HARD STOP GUARDRAIL:                                                     ║
║  Do NOT spend hours reading the guidelines! Verify metadata and move to      ║
║  extraction immediately by 10:00.                                            ║
║                                                                              ║
║  📦 DELIVERABLE:                                                             ║
║  `data/raw/` populated with intact PDFs + verified license checklist.        ║
╚══════════════════════════════════════════════════════════════════════════════╝
```

---

## ⏱️ Card 2: Task 2 — PDF Text Extraction & Header/Footer Sanitization

```
╔══════════════════════════════════════════════════════════════════════════════╗
║  CARD 2 / 5 ── TASK 2: EXTRACTION & MEDICAL CLEANING                        ║
║  ⏱️ TIME ALLOCATED: 45 MINUTES          🎯 TARGET COMPLETION: 10:45        ║
╠══════════════════════════════════════════════════════════════════════════════╣
║                                                                              ║
║  🎯 OBJECTIVES:                                                              ║
║  1. Extract full document text with page tracking using PyMuPDF.             ║
║  2. Extract structured clinical tables using pdfplumber.                     ║
║  3. Strip repetitive header/footer boilerplate and page labels.              ║
║  4. Preserve comparison operators (>=, <=, <, >) and clinical units.         ║
║                                                                              ║
║  🛑 HARD STOP GUARDRAIL:                                                     ║
║  Do NOT alter medical terminology, thresholds, or rewrite sentences.        ║
║  Cleaning must be purely structural.                                         ║
║                                                                              ║
║  📦 DELIVERABLE:                                                             ║
║  Deterministic page text blocks with exact source PDF page boundaries.       ║
╚══════════════════════════════════════════════════════════════════════════════╝
```

---

## ⏱️ Card 3: Task 3 — Guideline Structure Detection & Hierarchy Mapping

```
╔══════════════════════════════════════════════════════════════════════════════╗
║  CARD 3 / 5 ── TASK 3: STRUCTURE & RECOMMENDATION PARSING                   ║
║  ⏱️ TIME ALLOCATED: 60 MINUTES          🎯 TARGET COMPLETION: 11:45        ║
╠══════════════════════════════════════════════════════════════════════════════╣
║                                                                              ║
║  🎯 OBJECTIVES:                                                              ║
║  1. Detect section hierarchy, subheadings, and rationale blocks.             ║
║  2. Parse individual recommendation identifiers (e.g. 1.1.4, 1.6.7).         ║
║  3. Extract recommendation dates (original and amendment years).             ║
║  4. Link cross-references, tables, and algorithms to parent sections.        ║
║                                                                              ║
║  🛑 HARD STOP GUARDRAIL:                                                     ║
║  Ensure 100% ID uniqueness. If an ID format is ambiguous, fall back to       ║
║  deterministic section-based numbering.                                      ║
║                                                                              ║
║  📦 DELIVERABLE:                                                             ║
║  Parsed document hierarchy with classified content blocks.                   ║
╚══════════════════════════════════════════════════════════════════════════════╝
```

---

## ⏱️ Card 4: Task 4 — Semantic Medical Chunking & Clinical Enrichment

```
╔══════════════════════════════════════════════════════════════════════════════╗
║  CARD 4 / 5 ── TASK 4: CHUNKING & CLINICAL METADATA                          ║
║  ⏱️ TIME ALLOCATED: 45 MINUTES          🎯 TARGET COMPLETION: 12:30        ║
╠══════════════════════════════════════════════════════════════════════════════╣
║                                                                              ║
║  🎯 OBJECTIVES:                                                              ║
║  1. Chunk recommendations, rationales, tables, and algorithms cleanly.       ║
║  2. Enforce strict token bounds (50 <= tokens <= 800).                       ║
║  3. Extract clinical metadata: target populations, risk scores (QRISK3),     ║
║     lipid targets, BP thresholds, and drug dosages.                          ║
║  4. Assign clinical priority weights (Priority 1: Active Recommendations).   ║
║                                                                              ║
║  🛑 HARD STOP GUARDRAIL:                                                     ║
║  No orphan sentences or micro-chunks (< 20 tokens). Keep chunks standalone.  ║
║                                                                              ║
║  📦 DELIVERABLE:                                                             ║
║  Fully enriched semantic chunks ready for validation gates.                  ║
╚══════════════════════════════════════════════════════════════════════════════╝
```

---

## ⏱️ Card 5: Task 5 — Validation Gates V1–V6 & Export Pipeline

```
╔══════════════════════════════════════════════════════════════════════════════╗
║  CARD 5 / 5 ── TASK 5: VALIDATION & EXPORT (PRE-LUNCH CUTOFF)                ║
║  ⏱️ TIME ALLOCATED: 30 MINUTES          🎯 TARGET COMPLETION: 13:00        ║
╠══════════════════════════════════════════════════════════════════════════════╣
║                                                                              ║
║  🎯 OBJECTIVES:                                                              ║
║  1. Execute Quality Gates V1–V6 (IDs, Completeness, Bounds, Provenance).     ║
║  2. Emit `data/processed/NICE_2023_chunks.json` and `WHO_2021_chunks.json`.  ║
║  3. Emit vector-ready JSONL files and human QA markdown previews.            ║
║  4. Run automated test suite (`pytest -v`) to confirm 100% pass rate.        ║
║  5. Present Readiness Checklist to Trainer for sign-off before 13:30!        ║
║                                                                              ║
║  🛑 HARD STOP CUTOFF: 13:30 LUNCH CUTOFF                                     ║
║  Trainer sign-off is mandatory before afternoon index-building session!      ║
║                                                                              ║
║  📦 DELIVERABLE:                                                             ║
║  Green test suite + validated chunks + signed Trainer Readiness Checklist.   ║
╚══════════════════════════════════════════════════════════════════════════════╝
```
