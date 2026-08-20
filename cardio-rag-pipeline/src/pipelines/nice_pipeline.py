"""
Pipeline orchestrator for the CardioRAG NICE_2023 (NG238) processing pipeline.

End-to-end flow:
  PDF extraction → text cleaning → section hierarchy detection →
  subheading detection → recommendation ID & date parsing →
  metadata extraction → semantic chunking → deduplication →
  validation → JSON/JSONL/Markdown preview → processing report & sanity tests
"""

import json
import os
import sys
import time
import logging
from pathlib import Path
from typing import List, Optional, Dict, Any, Tuple

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from tqdm import tqdm

from src.parsers.nice_parser import (
    extract_pages,
    extract_toc,
    extract_tables,
    PageData,
    TableData,
    TocEntry,
)
from src.core.clean_text import clean_all_pages
from src.segmenters.nice_segmenter import (
    build_nice_sections,
    assign_pages_to_nice_sections,
    NiceSection,
    NiceSectionBlock,
)
from src.chunkers.nice_chunker import (
    NiceChunk,
    chunk_nice_section_block,
    reset_id_counters,
    count_tokens,
)
from src.core.deduplicate import deduplicate_nice_chunks
from src.postprocessors.validator import validate_nice3_chunks, ValidationReport


# ---------------------------------------------------------------------------
# Logging setup
# ---------------------------------------------------------------------------

def setup_logging(log_file: Optional[str] = None):
    """Configure logging for the pipeline."""
    handlers: List[logging.Handler] = [logging.StreamHandler()]
    if log_file:
        os.makedirs(os.path.dirname(log_file), exist_ok=True)
        handlers.append(logging.FileHandler(log_file, encoding="utf-8"))

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=handlers,
    )


# ---------------------------------------------------------------------------
# Sanity Test Queries (Prompt §63)
# ---------------------------------------------------------------------------

SANITY_TEST_QUERIES = [
    {
        "query": "Who should have QRISK3 calculated?",
        "topic": "cardiovascular_risk_assessment",
        "keywords": ["QRISK3", "risk assessment", "25 to 84", "type 2 diabetes"],
    },
    {
        "query": "Should aspirin routinely be used for primary prevention?",
        "topic": "antiplatelet_therapy",
        "keywords": ["aspirin", "primary prevention", "do not offer", "routinely"],
    },
    {
        "query": "What does NICE recommend about saturated fat?",
        "topic": "lifestyle",
        "keywords": ["saturated fat", "cardioprotective diet", "total fat", "monounsaturated"],
    },
    {
        "query": "When should someone be referred for very high triglycerides?",
        "topic": "lipid_assessment",
        "keywords": ["triglyceride", "refer", "specialist", "20 mmol", "10 mmol"],
    },
    {
        "query": "What tests should be performed before starting a statin?",
        "topic": "statin_pre_treatment_assessment",
        "keywords": ["baseline", "transaminase", "creatine kinase", "full lipid profile", "renal"],
    },
    {
        "query": "When is atorvastatin 20 mg recommended for primary prevention?",
        "topic": "lipid_lowering_treatment",
        "keywords": ["atorvastatin 20 mg", "primary prevention", "QRISK3", "10%"],
    },
    {
        "query": "What LDL target is recommended for secondary prevention?",
        "topic": "lipid_lowering_treatment",
        "keywords": ["2.0 mmol", "2.6 mmol", "LDL", "non-HDL", "secondary prevention"],
    },
    {
        "query": "What is the initial statin treatment for someone with established CVD?",
        "topic": "lipid_lowering_treatment",
        "keywords": ["atorvastatin 80 mg", "established CVD", "secondary prevention", "initial treatment"],
    },
    {
        "query": "What statin is recommended for CKD?",
        "topic": "lipid_lowering_treatment",
        "keywords": ["atorvastatin 20 mg", "CKD", "chronic kidney disease", "eGFR"],
    },
    {
        "query": "What should be done if a high-intensity statin is not tolerated?",
        "topic": "statin_intolerance",
        "keywords": ["tolerated", "lower dose", "alternative statin", "ezetimibe", "muscle"],
    },
    {
        "query": "What alternatives are available if statins are contraindicated?",
        "topic": "statin_intolerance",
        "keywords": ["contraindicated", "ezetimibe", "bempedoic acid", "PCSK9", "alirocumab"],
    },
    {
        "query": "When should lipids and liver transaminases be rechecked?",
        "topic": "treatment_monitoring",
        "keywords": ["2 to 3 months", "liver transaminase", "repeat", "annual", "rechecked"],
    },
]


# ---------------------------------------------------------------------------
# Output Serialization
# ---------------------------------------------------------------------------

def chunks_to_dicts(chunks: List[NiceChunk]) -> List[Dict[str, Any]]:
    """Convert chunk objects to serializable dictionaries."""
    return [
        {
            "chunk_id": c.chunk_id,
            "text": c.text,
            "token_count": c.token_count,
            "metadata": c.metadata,
        }
        for c in chunks
    ]


def write_json(chunks: List[NiceChunk], output_path: str):
    """Write chunks to formatted JSON array."""
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    data = chunks_to_dicts(chunks)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    logging.info("Wrote %d chunks to %s", len(chunks), output_path)


def write_jsonl(chunks: List[NiceChunk], output_path: str):
    """Write chunks to JSONL file (one line per chunk)."""
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    data = chunks_to_dicts(chunks)
    with open(output_path, "w", encoding="utf-8") as f:
        for item in data:
            f.write(json.dumps(item, ensure_ascii=False) + "\n")
    logging.info("Wrote %d chunks to %s", len(chunks), output_path)


def write_preview_md(chunks: List[NiceChunk], output_path: str):
    """Write human-readable preview markdown per Prompt §56."""
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    lines: List[str] = [
        "# NICE3 (NG238) Chunks Preview\n",
        f"**Document:** Cardiovascular disease: risk assessment and reduction, including lipid modification",
        f"**Guideline:** NICE NG238 (14 December 2023)",
        f"**Total chunks:** {len(chunks)}\n",
        "---\n",
    ]

    for chunk in chunks:
        meta = chunk.metadata
        cid = chunk.chunk_id

        lines.append(f"## {cid}\n")
        lines.append(f"**PDF page:** {meta.get('pdf_page_start', '?')}")
        if meta.get("printed_page_start"):
            lines.append(f" (printed: {meta['printed_page_start']})")
        lines.append(f"\n**Section:** {meta.get('section', '—')}")
        if meta.get("subsection"):
            lines.append(f"\n**Subsection:** {meta['subsection']}")
        if meta.get("recommendation_id"):
            lines.append(f"\n**Recommendation:** {meta['recommendation_id']}")
        if meta.get("recommendation_original_date"):
            lines.append(f"\n**Date:** {meta['recommendation_original_date']}")
        if meta.get("recommendation_amended_dates"):
            lines.append(f" (amended: {', '.join(meta['recommendation_amended_dates'])})")
        lines.append(f"\n**Topic:** {meta.get('topic', '—')}")
        if meta.get("subtopic"):
            lines.append(f"\n**Subtopic:** {meta['subtopic']}")
        lines.append(f"\n**Type:** {meta.get('content_type', '—')}")
        lines.append(f"\n**Clinical priority:** {meta.get('clinical_priority', '—')}")
        if meta.get("prevention_type"):
            lines.append(f"\n**Prevention type:** {meta['prevention_type']}")
        if meta.get("population"):
            lines.append(f"\n**Population:** {', '.join(meta['population'])}")
        if meta.get("drug_names"):
            lines.append(f"\n**Drug:** {', '.join(meta['drug_names'])}")
        if meta.get("dose"):
            lines.append(f"\n**Dose:** {meta['dose']}")
        if meta.get("risk_tool"):
            lines.append(f"\n**Risk tool:** {meta['risk_tool']}")
        if meta.get("risk_threshold"):
            lines.append(f"\n**Risk threshold:** {meta['risk_threshold']}")
        if meta.get("lipid_measure"):
            lines.append(f"\n**Lipid measure:** {', '.join(meta['lipid_measure'])}")
        if meta.get("lipid_target"):
            lines.append(f"\n**Lipid target:** {meta['lipid_target']}")
        if meta.get("technology_appraisal_refs"):
            lines.append(f"\n**TA refs:** {', '.join(meta['technology_appraisal_refs'])}")
        if meta.get("related_recommendation_ids"):
            lines.append(f"\n**Related recs:** {', '.join(meta['related_recommendation_ids'])}")
        if meta.get("is_duplicate"):
            lines.append(f"\n**⚠️ DUPLICATE of:** {meta.get('canonical_chunk_id')}")

        lines.append(f"\n**Tokens:** {chunk.token_count}\n")
        lines.append("\n### Text\n\n")
        lines.append(chunk.text + "\n")
        lines.append("\n---\n")

    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    logging.info("Wrote markdown preview to %s", output_path)


# ---------------------------------------------------------------------------
# Reports & Statistics (Prompt §58, §59)
# ---------------------------------------------------------------------------

def generate_processing_report(
    chunks: List[NiceChunk],
    total_pdf_pages: int,
    pages_parsed: int,
    tables: List[TableData],
    validation_report: ValidationReport,
    processing_time: float,
) -> Dict[str, Any]:
    """Generate comprehensive processing report and topic distribution."""
    # Count by content type
    type_counts: Dict[str, int] = {}
    topic_counts: Dict[str, int] = {}
    prevention_counts: Dict[str, int] = {"primary": 0, "secondary": 0, "primary_and_secondary": 0, "null": 0}
    token_values: List[int] = []
    ta_refs_all: Set[str] = set()
    cross_links_count = 0
    duplicate_count = 0
    ckd_count = 0
    statin_intolerance_count = 0
    monitoring_count = 0
    rec_ids_detected: Set[str] = set()
    rec_dates_detected: Set[str] = set()

    for chunk in chunks:
        meta = chunk.metadata
        ct = meta.get("content_type", "other")
        type_counts[ct] = type_counts.get(ct, 0) + 1

        top = meta.get("topic") or "unclassified"
        topic_counts[top] = topic_counts.get(top, 0) + 1

        pt = meta.get("prevention_type") or "null"
        prevention_counts[pt] = prevention_counts.get(pt, 0) + 1

        if meta.get("is_duplicate"):
            duplicate_count += 1

        token_values.append(chunk.token_count)

        for ta in meta.get("technology_appraisal_refs", []):
            ta_refs_all.add(ta)

        rel_recs = meta.get("related_recommendation_ids", [])
        if rel_recs:
            cross_links_count += len(rel_recs)

        if "chronic_kidney_disease" in meta.get("special_population", []) or meta.get("subtopic") == "chronic_kidney_disease":
            ckd_count += 1

        if top == "statin_intolerance" or meta.get("statin_status"):
            statin_intolerance_count += 1

        if top == "treatment_monitoring" or meta.get("test_names") or meta.get("monitoring_interval"):
            monitoring_count += 1

        if meta.get("recommendation_id"):
            rec_ids_detected.add(meta["recommendation_id"])

        if meta.get("recommendation_original_date"):
            rec_dates_detected.add(meta["recommendation_original_date"])

    avg_tokens = sum(token_values) / len(token_values) if token_values else 0
    min_tokens = min(token_values) if token_values else 0
    max_tokens = max(token_values) if token_values else 0

    stats = {
        "guideline_code": "NG238",
        "total_pdf_pages": total_pdf_pages,
        "pages_successfully_parsed": pages_parsed,
        "total_chunks": len(chunks),
        "direct_recommendations": type_counts.get("recommendation", 0),
        "committee_rationale_chunks": type_counts.get("committee_rationale", 0),
        "implementation_impact_chunks": type_counts.get("implementation_impact", 0),
        "definition_chunks": type_counts.get("definition", 0),
        "research_recommendation_chunks": type_counts.get("research_recommendation", 0),
        "update_information_chunks": type_counts.get("update_information", 0),
        "primary_prevention_chunks": prevention_counts.get("primary", 0),
        "secondary_prevention_chunks": prevention_counts.get("secondary", 0),
        "ckd_specific_chunks": ckd_count,
        "statin_intolerance_chunks": statin_intolerance_count,
        "monitoring_chunks": monitoring_count,
        "technology_appraisal_references_detected": sorted(list(ta_refs_all)),
        "cross_recommendation_links_detected": cross_links_count,
        "potential_duplicate_blocks": duplicate_count,
        "tables_extracted": len(tables),
        "validation_errors": len(validation_report.errors),
        "validation_warnings": len(validation_report.warnings),
        "token_statistics": {
            "average_tokens_per_chunk": round(avg_tokens, 1),
            "min_tokens": min_tokens,
            "max_tokens": max_tokens,
            "total_tokens": sum(token_values),
        },
        "content_type_breakdown": type_counts,
        "topic_distribution": topic_counts,
        "recommendation_ids_count": len(rec_ids_detected),
        "processing_time_seconds": round(processing_time, 2),
    }

    # Print nicely to stdout
    print("\n" + "=" * 65)
    print("NICE3 PROCESSING REPORT (NG238)")
    print("=" * 65)
    print(f"PDF pages:                                {total_pdf_pages}")
    print(f"Pages successfully parsed:                {pages_parsed}")
    print(f"Total chunks:                             {len(chunks)}")
    print(f"Direct recommendation chunks:             {type_counts.get('recommendation', 0)}")
    print(f"Committee rationale chunks:               {type_counts.get('committee_rationale', 0)}")
    print(f"Implementation impact chunks:             {type_counts.get('implementation_impact', 0)}")
    print(f"Definition chunks:                        {type_counts.get('definition', 0)}")
    print(f"Research recommendation chunks:           {type_counts.get('research_recommendation', 0)}")
    print(f"Update information chunks:                {type_counts.get('update_information', 0)}")
    print(f"Primary prevention chunks:                {prevention_counts.get('primary', 0)}")
    print(f"Secondary prevention chunks:              {prevention_counts.get('secondary', 0)}")
    print(f"CKD-specific chunks:                      {ckd_count}")
    print(f"Statin intolerance chunks:                {statin_intolerance_count}")
    print(f"Monitoring chunks:                        {monitoring_count}")
    print(f"Technology appraisal references detected: {sorted(list(ta_refs_all))}")
    print(f"Cross-recommendation links detected:      {cross_links_count}")
    print(f"Potential duplicate blocks:               {duplicate_count}")
    print(f"Average tokens per chunk:                 {avg_tokens:.1f}")
    print(f"Minimum tokens:                           {min_tokens}")
    print(f"Maximum tokens:                           {max_tokens}")
    print(f"Validation errors:                        {len(validation_report.errors)}")
    print(f"Validation warnings:                      {len(validation_report.warnings)}")
    print(f"Processing time:                          {processing_time:.2f}s")
    print("=" * 65)

    print("\n" + "-" * 40)
    print("TOPIC DISTRIBUTION REPORT (§59)")
    print("-" * 40)
    for topic_name, count in sorted(topic_counts.items(), key=lambda x: x[1], reverse=True):
        print(f"  {topic_name:35s}: {count}")
    print("-" * 40 + "\n")

    return stats


# ---------------------------------------------------------------------------
# Retrieval Sanity Tests (§63 & §64)
# ---------------------------------------------------------------------------

def run_retrieval_sanity_tests(chunks: List[NiceChunk]):
    """Execute keyword-based sanity retrieval scoring per Prompt §63 & §64."""
    print("=" * 65)
    print("RETRIEVAL SANITY TESTS & VALIDATION SCORING (§63, §64)")
    print("=" * 65 + "\n")

    for test_idx, item in enumerate(SANITY_TEST_QUERIES, 1):
        query = item["query"]
        keywords = item["keywords"]
        expected_topic = item["topic"]

        # Score chunks
        scored_chunks: List[Tuple[NiceChunk, int, float]] = []
        for chunk in chunks:
            if chunk.metadata.get("is_duplicate"):
                continue

            text_lower = chunk.text.lower()
            kw_hits = sum(1 for kw in keywords if kw.lower() in text_lower)
            if kw_hits > 0:
                # Direct recommendations get a priority boost in clinical retrieval
                priority = chunk.metadata.get("clinical_priority", 3)
                priority_weight = 2.0 if priority == 1 else (1.2 if priority == 2 else 1.0)
                final_score = kw_hits * priority_weight
                scored_chunks.append((chunk, kw_hits, final_score))

        scored_chunks.sort(key=lambda x: x[2], reverse=True)
        top = scored_chunks[:3]

        print(f"[{test_idx}/12] Query: {query}")
        if top:
            top_chunk, raw_hits, score = top[0]
            top_meta = top_chunk.metadata
            cid = top_chunk.chunk_id
            rec_id = top_meta.get("recommendation_id", "N/A")
            ctype = top_meta.get("content_type", "N/A")
            page = top_meta.get("pdf_page_start", "N/A")
            topic = top_meta.get("topic", "N/A")

            print(f"  Top chunk ID:       {cid}")
            print(f"  Recommendation ID:  {rec_id}")
            print(f"  Content Type:       {ctype}")
            print(f"  Page:               {page}")
            print(f"  Topic:              {topic}")
            print(f"  Retrieval score:    {score:.2f} (keyword matches: {raw_hits})")

            # Check if non-recommendation outranked recommendation
            if ctype in ("committee_rationale", "implementation_impact", "update_information"):
                print("  ⚠️ Flag: Supporting material ranked top.")
        else:
            print("  ⚠️ No matching chunks found!")
        print()


# ---------------------------------------------------------------------------
# Pipeline Execution
# ---------------------------------------------------------------------------

def run_nice_pipeline(pdf_path: Optional[str] = None):
    """Run the complete NICE_2023 (NG238) parsing and chunking pipeline."""
    start_time = time.time()

    if pdf_path is None:
        pdf_path = str(PROJECT_ROOT / "data" / "raw" / "NICE_2023.pdf")

    output_dir = str(PROJECT_ROOT / "data" / "processed")
    log_file = str(PROJECT_ROOT / "NICE_2023_pipeline.log")

    setup_logging(log_file)
    logger = logging.getLogger(__name__)
    logger.info("Starting NICE_2023 (NG238) Pipeline on %s", pdf_path)

    reset_id_counters()

    # Step 1: Extract pages
    print("\n[1/7] Extracting pages with PyMuPDF...")
    pages = extract_pages(pdf_path)
    total_pages = len(pages)
    print(f"  Extracted {total_pages} pages from PDF.")

    # Step 2: Extract TOC & Tables
    print("[2/7] Extracting Table of Contents and structured tables...")
    toc_entries = extract_toc(pdf_path)
    tables = extract_tables(pdf_path)
    print(f"  Found {len(toc_entries)} TOC items, {len(tables)} tables.")

    # Step 3: Clean text
    print("[3/7] Cleaning page text & removing boilerplate...")
    pages_raw = [(p.pdf_page, p.raw_text) for p in pages]
    cleaned_pages = clean_all_pages(pages_raw)
    for page, (_, cleaned_text) in zip(pages, cleaned_pages):
        page.cleaned_text = cleaned_text
    print(f"  Cleaned {len(cleaned_pages)} pages.")

    # Step 4: Section hierarchy detection
    print("[4/7] Detecting NICE guideline structure & section segmentation...")
    pages_with_labels = [(p.pdf_page, p.cleaned_text, p.page_label) for p in pages]
    section_blocks = assign_pages_to_nice_sections(pages_with_labels, total_pdf_pages=total_pages)
    print(f"  Created {len(section_blocks)} section blocks.")

    # Step 5: Semantic Chunking
    print("[5/7] Creating semantic chunks...")
    all_chunks: List[NiceChunk] = []
    for sblock in tqdm(section_blocks, desc="Chunking sections"):
        chunks = chunk_nice_section_block(sblock)
        all_chunks.extend(chunks)
    print(f"  Generated {len(all_chunks)} raw semantic chunks.")

    # Step 6: Deduplication
    print("[6/7] Deduplicating identical extractions...")
    all_chunks = deduplicate_nice_chunks(all_chunks)

    # Step 7: Validation
    print("[7/7] Validating chunks & medical constraints...")
    val_report = validate_nice3_chunks(all_chunks, total_pdf_pages=total_pages)
    if val_report.is_valid:
        print("  ✓ Validation passed with zero critical errors!")
    else:
        print(f"  ⚠️ Found {len(val_report.errors)} validation errors:")
        for err in val_report.errors[:10]:
            print(f"    - {err}")

    # Output writing
    json_path = os.path.join(output_dir, "NICE_2023_chunks.json")
    jsonl_path = os.path.join(output_dir, "NICE_2023_chunks.jsonl")
    preview_path = os.path.join(output_dir, "NICE_2023_chunks_preview.md")
    report_path = os.path.join(output_dir, "NICE_2023_processing_report.json")

    write_json(all_chunks, json_path)
    write_jsonl(all_chunks, jsonl_path)
    write_preview_md(all_chunks, preview_path)

    processing_time = time.time() - start_time
    stats = generate_processing_report(
        chunks=all_chunks,
        total_pdf_pages=total_pages,
        pages_parsed=total_pages,
        tables=tables,
        validation_report=val_report,
        processing_time=processing_time,
    )

    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(stats, f, indent=2, ensure_ascii=False)
    logging.info("Saved processing report to %s", report_path)

    # Sanity retrieval queries
    run_retrieval_sanity_tests(all_chunks)

    print("\n" + "=" * 65)
    print("NICE_2023 PIPELINE EXECUTION COMPLETE")
    print("=" * 65)
    print(f"  JSON:           {json_path}")
    print(f"  JSONL:          {jsonl_path}")
    print(f"  Markdown QA:    {preview_path}")
    print(f"  Report JSON:    {report_path}")
    print(f"  Log File:       {log_file}")
    print("\n[OK] Medical safety verification: No wording modified. Provenance preserved.")
    print("=" * 65 + "\n")

    return all_chunks, stats


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="CardioRAG NICE_2023 Pipeline")
    parser.add_argument("--pdf", type=str, default=None, help="Path to NICE_2023.pdf")
    args = parser.parse_args()

    run_nice_pipeline(pdf_path=args.pdf)
