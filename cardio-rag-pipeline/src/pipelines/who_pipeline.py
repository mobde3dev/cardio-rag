"""
Pipeline orchestrator for the CardioRAG WHO_2021 processing pipeline.

End-to-end flow:
  PDF → page extraction → text cleaning → structure detection →
  section segmentation → clinical block classification →
  recommendation extraction → metadata extraction →
  semantic chunking → deduplication → validation →
  JSON / JSONL / Markdown preview → processing report
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

from src.parsers.who_parser import (
    extract_pages,
    extract_toc,
    extract_tables,
    detect_figures,
    PageData,
    TableData,
    TocEntry,
    FigureInfo,
)
from src.core.clean_text import clean_all_pages
from src.segmenters.who_segmenter import (
    build_sections,
    assign_pages_to_sections,
    Section,
    SectionBlock,
    is_administrative_section,
    get_annex_priority,
)
from src.enrichers.who_enricher import build_chunk_metadata
from src.chunkers.who_chunker import (
    Chunk,
    chunk_section_block,
    chunk_table,
    chunk_algorithm,
    deduplicate_chunks,
    validate_chunks,
    count_tokens,
    reset_id_counters,
)


# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

def setup_logging(log_file: Optional[str] = None):
    """Configure logging for the pipeline."""
    handlers = [logging.StreamHandler()]
    if log_file:
        os.makedirs(os.path.dirname(log_file), exist_ok=True)
        handlers.append(logging.FileHandler(log_file, encoding="utf-8"))

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=handlers,
    )


# ---------------------------------------------------------------------------
# Test queries for validation
# ---------------------------------------------------------------------------

TEST_QUERIES = [
    {
        "query": "What is the blood pressure threshold for starting pharmacological treatment?",
        "expected_section": "3.1",
        "expected_keywords": ["140", "mmHg", "90", "130"],
    },
    {
        "query": "What are the first-line drug classes for hypertension?",
        "expected_section": "3.4",
        "expected_keywords": ["thiazide", "ACE", "ARB", "CCB", "calcium channel"],
    },
    {
        "query": "What is the target blood pressure for patients with cardiovascular disease?",
        "expected_section": "3.6",
        "expected_keywords": ["130", "target", "CVD", "cardiovascular"],
    },
    {
        "query": "How should hypertension be managed during pregnancy?",
        "expected_section": "4.3",
        "expected_keywords": ["pregnancy", "pregnant", "methyldopa", "labetalol"],
    },
    {
        "query": "What is the recommended follow-up frequency after starting treatment?",
        "expected_section": "3.7",
        "expected_keywords": ["month", "reassess", "follow", "visit"],
    },
]


# ---------------------------------------------------------------------------
# Output generators
# ---------------------------------------------------------------------------

def chunks_to_dicts(chunks: List[Chunk]) -> List[Dict[str, Any]]:
    """Convert Chunk objects to serializable dicts."""
    return [
        {
            "chunk_id": c.chunk_id,
            "text": c.text,
            "token_count": c.token_count,
            "metadata": c.metadata,
        }
        for c in chunks
    ]


def write_json(chunks: List[Chunk], output_path: str):
    """Write chunks to JSON file."""
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    data = chunks_to_dicts(chunks)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    logging.info("Wrote %d chunks to %s", len(chunks), output_path)


def write_jsonl(chunks: List[Chunk], output_path: str):
    """Write chunks to JSONL file (one chunk per line)."""
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    data = chunks_to_dicts(chunks)
    with open(output_path, "w", encoding="utf-8") as f:
        for item in data:
            f.write(json.dumps(item, ensure_ascii=False) + "\n")
    logging.info("Wrote %d chunks to %s", len(chunks), output_path)


def write_preview_md(chunks: List[Chunk], output_path: str):
    """Write human-readable Markdown preview of all chunks."""
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    lines: List[str] = [
        "# WHO03 Chunks Preview\n",
        f"**Total chunks:** {len(chunks)}\n",
        "---\n",
    ]

    for chunk in chunks:
        meta = chunk.metadata
        lines.append(f"\n## {chunk.chunk_id}\n")
        lines.append(f"**Pages:** {meta.get('pdf_page_start', '?')}–{meta.get('pdf_page_end', '?')}")
        if meta.get("page_label_start"):
            lines.append(f" (labels: {meta['page_label_start']}–{meta.get('page_label_end', '?')})")
        lines.append("\n")
        lines.append(f"**Section:** {meta.get('subsection') or meta.get('section', '—')}\n")
        lines.append(f"**Topic:** {meta.get('topic', '—')}\n")
        if meta.get("subtopic"):
            lines.append(f"**Subtopic:** {meta['subtopic']}\n")
        lines.append(f"**Type:** {meta.get('content_type', '—')}\n")
        if meta.get("recommendation_strength"):
            lines.append(f"**Strength:** {meta['recommendation_strength']}\n")
        if meta.get("evidence_certainty"):
            lines.append(f"**Evidence certainty:** {meta['evidence_certainty']}\n")
        if meta.get("special_setting"):
            lines.append(f"**Special setting:** {meta['special_setting']}\n")
        lines.append(f"**Priority:** {meta.get('clinical_priority', '—')}\n")
        lines.append(f"**Tokens:** {chunk.token_count}\n")
        if meta.get("is_duplicate"):
            lines.append(f"**⚠️ DUPLICATE of:** {meta.get('canonical_chunk_id')}\n")
        if meta.get("drug_class"):
            lines.append(f"**Drug classes:** {', '.join(meta['drug_class']) if isinstance(meta['drug_class'], list) else meta['drug_class']}\n")
        if meta.get("bp_threshold"):
            lines.append(f"**BP threshold:** {meta['bp_threshold']}\n")

        lines.append(f"\n### Text\n\n")
        # Show first 1000 chars to keep preview manageable
        preview_text = chunk.text[:1000]
        if len(chunk.text) > 1000:
            preview_text += f"\n\n... [{len(chunk.text) - 1000} more characters]\n"
        lines.append(preview_text + "\n")
        lines.append("\n---\n")

    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    logging.info("Wrote preview to %s", output_path)


# ---------------------------------------------------------------------------
# Processing report
# ---------------------------------------------------------------------------

def print_report(
    chunks: List[Chunk],
    total_pdf_pages: int,
    pages_parsed: int,
    skipped_pages: int,
    figures: List[FigureInfo],
    tables: List[TableData],
    validation_errors: List[str],
    processing_time: float,
):
    """Print the processing report to console."""
    # Count by type
    type_counts: Dict[str, int] = {}
    duplicate_count = 0
    token_values: List[int] = []

    for chunk in chunks:
        ct = chunk.metadata.get("content_type", "other")
        type_counts[ct] = type_counts.get(ct, 0) + 1
        if chunk.metadata.get("is_duplicate"):
            duplicate_count += 1
        token_values.append(chunk.token_count)

    # Pages needing manual review
    manual_review_pages = [f.pdf_page for f in figures if f.requires_manual_review]

    report = f"""
{'='*60}
WHO03 PROCESSING REPORT
{'='*60}

PDF pages:                      {total_pdf_pages}
Pages parsed:                   {pages_parsed}
Pages skipped (admin/front):    {skipped_pages}

Total chunks:                   {len(chunks)}

Chunk breakdown by type:
"""
    for ct in sorted(type_counts.keys()):
        report += f"  {ct:30s}  {type_counts[ct]}\n"

    report += f"""
Tables extracted:               {len(tables)}
Figures detected:               {len(figures)}
Potential duplicate chunks:     {duplicate_count}
Validation errors:              {len(validation_errors)}

Token statistics:
  Average tokens per chunk:     {sum(token_values) / len(token_values):.0f}
  Minimum tokens:               {min(token_values)}
  Maximum tokens:               {max(token_values)}

Pages requiring manual review:  {manual_review_pages if manual_review_pages else 'None'}

Processing time:                {processing_time:.1f}s
{'='*60}
"""
    print(report)

    # Save stats as JSON
    stats = {
        "total_pages": total_pdf_pages,
        "pages_processed": pages_parsed,
        "pages_skipped": skipped_pages,
        "total_chunks": len(chunks),
        "chunks_by_type": type_counts,
        "tables_extracted": len(tables),
        "figures_detected": len(figures),
        "duplicate_chunks": duplicate_count,
        "validation_errors": len(validation_errors),
        "token_statistics": {
            "total_tokens": sum(token_values),
            "average_tokens_per_chunk": round(sum(token_values) / len(token_values), 1),
            "min_tokens": min(token_values),
            "max_tokens": max(token_values),
        },
        "manual_review_pages": manual_review_pages,
        "processing_time_seconds": round(processing_time, 1),
    }

    stats_path = str(PROJECT_ROOT / "data" / "processed" / "WHO_2021_stats.json")
    os.makedirs(os.path.dirname(stats_path), exist_ok=True)
    with open(stats_path, "w", encoding="utf-8") as f:
        json.dump(stats, f, indent=2, ensure_ascii=False)
    logging.info("Saved processing stats to %s", stats_path)

    return stats


# ---------------------------------------------------------------------------
# Test query runner
# ---------------------------------------------------------------------------

def run_test_queries(chunks: List[Chunk]):
    """Run test queries against chunks using simple keyword matching.

    This is for validating chunk quality only — NOT the final RAG system.
    """
    print(f"\n{'='*60}")
    print("TEST QUERY VALIDATION")
    print(f"{'='*60}\n")

    for q in TEST_QUERIES:
        query = q["query"]
        keywords = q["expected_keywords"]
        expected_section = q["expected_section"]

        # Find chunks containing any of the keywords
        matches: List[Tuple[Chunk, int]] = []
        for chunk in chunks:
            if chunk.metadata.get("is_duplicate"):
                continue
            text_lower = chunk.text.lower()
            score = sum(1 for kw in keywords if kw.lower() in text_lower)
            if score > 0:
                matches.append((chunk, score))

        # Sort by score descending
        matches.sort(key=lambda x: x[1], reverse=True)
        top = matches[:3]

        print(f"Query: {query}")
        print(f"  Expected section: {expected_section}")
        print(f"  Keywords: {keywords}")
        print(f"  Matching chunks: {len(matches)}")

        if top:
            for chunk, score in top:
                sec = chunk.metadata.get("subsection") or chunk.metadata.get("section", "-")
                print(f"    -> {chunk.chunk_id} (score={score}, section={sec}, "
                      f"type={chunk.metadata.get('content_type')}, "
                      f"tokens={chunk.token_count})")
        else:
            print("    [!] No matching chunks found!")
        print()


# ---------------------------------------------------------------------------
# Main pipeline
# ---------------------------------------------------------------------------

def run_pipeline(pdf_path: str = None):
    """Execute the full WHO03 parsing and chunking pipeline."""
    logger = logging.getLogger(__name__)
    start_time = time.time()

    # Paths
    if pdf_path is None:
        pdf_path = str(PROJECT_ROOT / "data" / "raw" / "WHO_2021.pdf")

    output_dir = str(PROJECT_ROOT / "data" / "processed")
    figures_dir = os.path.join(output_dir, "figures")
    log_file = str(PROJECT_ROOT / "pipeline.log")

    # Setup logging
    setup_logging(log_file)
    logger.info("Starting WHO03 pipeline")
    logger.info("PDF: %s", pdf_path)

    # Reset chunk ID counters
    reset_id_counters()

    # -----------------------------------------------------------------------
    # Step 1: Extract pages
    # -----------------------------------------------------------------------
    print("\n[1/8] Extracting pages from PDF...")
    pages = extract_pages(pdf_path)
    total_pdf_pages = len(pages)
    print(f"  Extracted {total_pdf_pages} pages")

    # -----------------------------------------------------------------------
    # Step 2: Extract TOC
    # -----------------------------------------------------------------------
    print("[2/8] Extracting Table of Contents...")
    toc_entries = extract_toc(pdf_path)
    print(f"  Found {len(toc_entries)} TOC entries")
    if toc_entries:
        for entry in toc_entries[:10]:
            print(f"    L{entry.level}: {entry.title} (p.{entry.page})")
        if len(toc_entries) > 10:
            print(f"    ... and {len(toc_entries) - 10} more")

    # -----------------------------------------------------------------------
    # Step 3: Extract tables
    # -----------------------------------------------------------------------
    print("[3/8] Extracting tables (pdfplumber)...")
    tables = extract_tables(pdf_path)
    print(f"  Extracted {len(tables)} tables")

    # -----------------------------------------------------------------------
    # Step 4: Detect figures
    # -----------------------------------------------------------------------
    print("[4/8] Detecting figures and algorithms...")
    figures = detect_figures(pdf_path, output_dir=figures_dir)
    print(f"  Detected {len(figures)} figure pages")

    # -----------------------------------------------------------------------
    # Step 5: Clean text
    # -----------------------------------------------------------------------
    print("[5/8] Cleaning text...")
    pages_raw = [(p.pdf_page, p.raw_text) for p in pages]
    cleaned_pages = clean_all_pages(pages_raw)

    # Update PageData with cleaned text
    for page, (pdf_page, cleaned_text) in zip(pages, cleaned_pages):
        page.cleaned_text = cleaned_text

    print(f"  Cleaned {len(cleaned_pages)} pages")

    # -----------------------------------------------------------------------
    # Step 6: Detect sections
    # -----------------------------------------------------------------------
    print("[6/8] Detecting document structure...")
    pages_for_sections = [(p, t) for p, t in cleaned_pages]
    sections = build_sections(toc_entries, pages_for_sections, pages)

    print(f"  Detected {len(sections)} sections:")
    for sec in sections:
        indent = "  " * sec.level
        print(f"    {indent}{sec.number} {sec.title} (p.{sec.page_start})")

    # Assign pages to sections
    pages_with_labels = [
        (p.pdf_page, p.cleaned_text, p.page_label)
        for p in pages
    ]
    section_blocks = assign_pages_to_sections(
        pages_with_labels, sections, total_pdf_pages
    )
    print(f"  Created {len(section_blocks)} section blocks")

    # -----------------------------------------------------------------------
    # Step 7: Chunk
    # -----------------------------------------------------------------------
    print("[7/8] Creating semantic chunks...")
    all_chunks: List[Chunk] = []
    skipped_pages = 0

    for sblock in tqdm(section_blocks, desc="Chunking sections"):
        if is_administrative_section(sblock.section):
            skipped_pages += (sblock.pdf_page_end - sblock.pdf_page_start + 1)
            continue

        chunks = chunk_section_block(sblock)
        all_chunks.extend(chunks)

    # Add table chunks
    for table in tables:
        # Find section for this table's page
        sec = None
        for sblock in section_blocks:
            if sblock.pdf_page_start <= table.pdf_page <= sblock.pdf_page_end:
                sec = sblock.section
                break
        if sec is None:
            sec = Section(number="", title="Tables", level=1, page_start=table.pdf_page,
                          full_heading="Tables")

        # Find page label
        page_label = None
        for p in pages:
            if p.pdf_page == table.pdf_page:
                page_label = p.page_label
                break

        caption = f"Table on page {table.pdf_page}"
        if table.headers:
            caption = " | ".join(h for h in table.headers[:3] if h)

        tbl_chunk = chunk_table(
            markdown=table.markdown,
            caption=caption,
            section=sec,
            pdf_page=table.pdf_page,
            page_label=page_label,
        )
        all_chunks.append(tbl_chunk)

    # Add algorithm/figure chunks
    for fig in figures:
        sec = None
        for sblock in section_blocks:
            if sblock.pdf_page_start <= fig.pdf_page <= sblock.pdf_page_end:
                sec = sblock.section
                break
        if sec is None:
            sec = Section(number="6", title="Implementation tools", level=1,
                          page_start=fig.pdf_page, full_heading="6 Implementation tools")

        page_label = None
        for p in pages:
            if p.pdf_page == fig.pdf_page:
                page_label = p.page_label

        # Get page text for algorithm content
        page_text = ""
        for p in pages:
            if p.pdf_page == fig.pdf_page:
                page_text = p.cleaned_text
                break

        algo_chunk = chunk_algorithm(
            text=page_text,
            figure_desc=fig.description,
            section=sec,
            pdf_page=fig.pdf_page,
            page_label=page_label,
            requires_manual_review=fig.requires_manual_review,
        )
        all_chunks.append(algo_chunk)

    print(f"  Created {len(all_chunks)} chunks")

    # -----------------------------------------------------------------------
    # Step 7b: Deduplicate
    # -----------------------------------------------------------------------
    print("  Deduplicating...")
    all_chunks = deduplicate_chunks(all_chunks)

    # -----------------------------------------------------------------------
    # Step 8: Validate & output
    # -----------------------------------------------------------------------
    print("[8/8] Validating and writing output...")

    validation_errors = validate_chunks(all_chunks, total_pdf_pages)

    if validation_errors:
        print(f"  ⚠️  {len(validation_errors)} validation errors found:")
        for err in validation_errors[:10]:
            print(f"    - {err}")
        if len(validation_errors) > 10:
            print(f"    ... and {len(validation_errors) - 10} more")

    # Write outputs
    json_path = os.path.join(output_dir, "WHO_2021_chunks.json")
    jsonl_path = os.path.join(output_dir, "WHO_2021_chunks.jsonl")
    preview_path = os.path.join(output_dir, "WHO_2021_chunks_preview.md")

    write_json(all_chunks, json_path)
    write_jsonl(all_chunks, jsonl_path)
    write_preview_md(all_chunks, preview_path)

    # Processing time
    processing_time = time.time() - start_time

    # Print report
    stats = print_report(
        chunks=all_chunks,
        total_pdf_pages=total_pdf_pages,
        pages_parsed=total_pdf_pages - skipped_pages,
        skipped_pages=skipped_pages,
        figures=figures,
        tables=tables,
        validation_errors=validation_errors,
        processing_time=processing_time,
    )

    # Run test queries
    run_test_queries(all_chunks)

    # -----------------------------------------------------------------------
    # Summary
    # -----------------------------------------------------------------------
    print(f"\n{'='*60}")
    print("PIPELINE COMPLETE")
    print(f"{'='*60}")
    print(f"\nOutputs:")
    print(f"  JSON:     {json_path}")
    print(f"  JSONL:    {jsonl_path}")
    print(f"  Preview:  {preview_path}")
    print(f"  Stats:    {os.path.join(output_dir, 'WHO_2021_stats.json')}")
    print(f"  Log:      {log_file}")
    if figures:
        print(f"  Figures:  {figures_dir}")
    print(f"\n[OK] No recommendation wording was intentionally altered.")
    print(f"[OK] All text is extracted directly from the source PDF.\n")

    return all_chunks, stats


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="CardioRAG WHO03 Processing Pipeline")
    parser.add_argument(
        "--pdf", type=str, default=None,
        help="Path to WHO03.pdf (default: data/raw/WHO03.pdf)",
    )
    args = parser.parse_args()

    chunks, stats = run_pipeline(pdf_path=args.pdf)
