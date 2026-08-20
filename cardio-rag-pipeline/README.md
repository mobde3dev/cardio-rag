# CardioRAG — Medical Guideline PDF Parsing & Chunking Pipeline

A modular Python pipeline that converts clinical guideline documents into high-quality, medically verified RAG chunks with rich clinical metadata.

Supported Guidelines:
1. **NICE Guideline NG238 (2023)** — *Cardiovascular disease: risk assessment and reduction, including lipid modification* (`data/raw/NICE_2023.pdf`)
2. **WHO Guideline (2021)** — *Guideline for the pharmacological treatment of hypertension in adults* (`data/raw/WHO_2021.pdf`)

---

## Overview

This pipeline acts as the **deterministic ingestion layer** for the CardioRAG medical RAG system. It is deterministic and rule-based, designed for high retrieval precision, medical safety, and zero clinical hallucination.

### Key Capabilities

1. **PDF Extraction**: Extracts text with page tracking (`PyMuPDF`) and structured tables (`pdfplumber`).
2. **Medical Cleaning**: Strips repetitive header/footer boilerplate while preserving units, lipid values, thresholds, doses, and comparison operators.
3. **Guideline Structure Detection**: Detects all major sections, subheadings, algorithms, tables, and committee rationale sections.
4. **Recommendation Parsing**: Extracts individual recommendation IDs (e.g. `1.7.1`, `1.6.7`), original/amended dates, and cross-references.
5. **Rich Medical Metadata**: Extracts populations, risk tools (QRISK3), lipid targets, drug doses, lab tests, and technology appraisals (TAs).
6. **Semantic Chunking**: Creates standalone recommendation chunks, rationale chunks, tables, and algorithms with deterministic IDs.
7. **Validation & Quality Gates (V1–V6)**: Comprehensive checks for ID uniqueness, completeness, token length bounds, provenance, and metadata consistency.
8. **Multi-Format Output**: Emits JSON array, JSONL (vector DB ready), markdown preview, and processing reports.

---

## Clean Project Structure

```text
cardiorag/
├── data/
│   ├── raw/
│   │   ├── NICE_2023.pdf                # Official NICE NG238 PDF
│   │   └── WHO_2021.pdf                 # Official WHO Hypertension PDF
│   └── processed/
│       ├── NICE_2023_chunks.json        # Parsed & validated chunks
│       ├── NICE_2023_chunks.jsonl       # Vector-database ready
│       ├── NICE_2023_chunks_preview.md  # Human QA markdown preview
│       ├── NICE_2023_processing_report.json
│       ├── WHO_2021_chunks.json
│       ├── WHO_2021_chunks.jsonl
│       ├── WHO_2021_chunks_preview.md
│       ├── WHO_2021_stats.json
│       ├── fix_report.json              # Validation & fix audit report
│       └── figures/                     # Extracted clinical algorithms & figures
│           ├── WHO_2021_fig_p06.png
│           └── ...
├── src/
│   ├── core/                            # Core utilities
│   │   ├── clean_text.py                # Safe text cleaning & boilerplate stripping
│   │   └── deduplicate.py               # Chunk deduplication
│   ├── parsers/                         # PDF & table parsers
│   │   ├── nice_parser.py               # NICE PyMuPDF & table extractor
│   │   └── who_parser.py                # WHO PyMuPDF & table extractor
│   ├── segmenters/                      # Section & heading segmenters
│   │   ├── nice_segmenter.py            # NICE hierarchy detection
│   │   ├── nice_rec_parser.py           # NICE recommendation extraction
│   │   └── who_segmenter.py             # WHO section segmentation
│   ├── chunkers/                        # Semantic chunking engines
│   │   ├── nice_chunker.py              # NICE recommendation & rationale chunker
│   │   └── who_chunker.py               # WHO chunker (Recs, Evidence, Tables)
│   ├── enrichers/                       # Clinical metadata enrichers
│   │   ├── nice_enricher.py             # NICE clinical metadata
│   │   └── who_enricher.py              # WHO clinical metadata
│   ├── postprocessors/                  # Verification & repair
│   │   ├── fixer.py                     # Validation Gates V1-V6 & repair rules
│   │   ├── patcher.py                   # Chunk patcher & normalizer
│   │   └── validator.py                 # Structural validator
│   ├── pipelines/                       # Modular pipeline definitions
│   │   ├── nice_pipeline.py             # NICE pipeline runner
│   │   └── who_pipeline.py              # WHO pipeline runner
│   └── pipeline.py                      # Unified CLI entry point
├── tests/
│   ├── test_fix_rules.py                # Fix & quality gate tests
│   ├── test_nice3_chunking.py           # NICE pipeline unit & integration tests
│   └── test_who03_chunking.py           # WHO pipeline unit & integration tests
├── requirements.txt
└── README.md
```

---

## Quick Start

### Install Dependencies

```bash
pip install -r requirements.txt
```

### Run Unified Ingestion Pipeline

```bash
# Process all guidelines (WHO + NICE)
python -m src.pipeline --doc all

# Or process individually:
python -m src.pipeline --doc who
python -m src.pipeline --doc nice
```

### Run Test Suite

```bash
pytest -v
```

---

## Medical Safety Guarantee

- **No Paraphrasing**: Guideline recommendation texts are verbatim extracts from the official source PDFs.
- **No Model Hallucination**: Clinical thresholds, drug doses, and dates are never fabricated or rewritten.
- **Strict Provenance**: Every chunk preserves the exact source PDF page boundaries for clinical citation and traceability.
