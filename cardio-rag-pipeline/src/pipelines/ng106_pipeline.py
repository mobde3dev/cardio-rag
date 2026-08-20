"""
Pipeline orchestrator for NICE NG106 (Chronic heart failure in adults: diagnosis and management).

End-to-end flow:
  PDF extraction → text cleaning → recommendation parsing (1.1.1 to 1.12.5) →
  Heart Failure clinical metadata extraction → rationale & research chunking →
  validation → JSON / JSONL / Markdown preview.
"""

import json
import os
import re
import sys
import time
import logging
from pathlib import Path
from typing import List, Optional, Dict, Any, Tuple

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from tqdm import tqdm
import tiktoken

from src.parsers.nice_parser import extract_pages, PageData
from src.core.clean_text import clean_all_pages
from src.segmenters.ng106_segmenter import (
    NG106_SECTION_DEFS,
    NG106_TOPIC_MAP,
    Ng106Section,
)
from src.segmenters.nice_rec_parser import (
    extract_recommendations,
    NiceRecommendation,
)
from src.enrichers.ng106_enricher import (
    build_ng106_chunk_metadata,
    extract_heart_failure_metadata,
    NG106_DOCUMENT_METADATA,
)

logger = logging.getLogger("cardiorag.ng106")

_enc = None


def count_tokens(text: str) -> int:
    global _enc
    if _enc is None:
        try:
            _enc = tiktoken.get_encoding("cl100k_base")
        except Exception:
            _enc = tiktoken.encoding_for_model("gpt-4")
    return len(_enc.encode(text))


# Mapping section prefix -> section title
SECTION_TITLES = {
    sec_id: title for sec_id, title, _, _ in NG106_SECTION_DEFS
}


def get_section_for_rec_id(rec_id: str) -> Ng106Section:
    """Find the parent section object for a given recommendation ID (e.g. 1.4.2 -> 1.4)."""
    parts = rec_id.split(".")
    sec_id = f"{parts[0]}.{parts[1]}" if len(parts) >= 2 else "recommendations"
    title = SECTION_TITLES.get(sec_id, "Recommendations")
    return Ng106Section(
        number=sec_id,
        title=title,
        level=1,
        page_start=0,
        full_heading=f"{sec_id} {title}" if sec_id[0].isdigit() else title,
    )


def extract_non_rec_sections(pages: List[PageData]) -> List[Dict[str, Any]]:
    """Extract and chunk non-recommendation sections (Overview, Terms, Research, Rationale, Context)."""
    non_rec_chunks: List[Dict[str, Any]] = []

    # Map page numbers to text
    page_texts = {p.pdf_page: p.cleaned_text for p in pages}

    # 1. Overview (p. 5)
    if 5 in page_texts:
        t = page_texts[5].strip()
        cid = "NG106_OVERVIEW_001"
        sec = Ng106Section(number="overview", title="Overview", level=1, page_start=5, full_heading="Overview")
        chunk_text = f"Section: Overview\n\n{t}"
        non_rec_chunks.append({
            "chunk_id": cid,
            "text": chunk_text,
            "token_count": count_tokens(chunk_text),
            "metadata": build_ng106_chunk_metadata(
                rec=None,
                section=sec,
                subheading="Overview and target audience",
                content_type="overview",
                pdf_page_start=5,
                pdf_page_end=5,
                text=t,
            ),
        })

    # 2. Terms used in this guideline (p. 26-27)
    terms_text = "\n\n".join([page_texts.get(p, "") for p in [26, 27] if p in page_texts])
    terms_match = re.search(r"Terms used in this guideline\s*(.*?)(?=Recommendations for research|$)", terms_text, re.DOTALL | re.I)
    if terms_match:
        raw_terms = terms_match.group(1).strip()
        # Split terms into individual definitions
        term_blocks = re.split(r"(?m)^(?=[A-Z][A-Za-z\s-]{3,40}\n)", raw_terms)
        for i, tb in enumerate(term_blocks, start=1):
            tb = tb.strip()
            if not tb or len(tb) < 20:
                continue
            cid = f"NG106_DEF_{i:03d}"
            sec = Ng106Section(number="terms", title="Terms used in this guideline", level=1, page_start=26, full_heading="Terms used in this guideline")
            chunk_text = f"Section: Terms used in this guideline\n\n{tb}"
            non_rec_chunks.append({
                "chunk_id": cid,
                "text": chunk_text,
                "token_count": count_tokens(chunk_text),
                "metadata": build_ng106_chunk_metadata(
                    rec=None,
                    section=sec,
                    subheading="Definitions",
                    content_type="definition",
                    pdf_page_start=26,
                    pdf_page_end=27,
                    text=tb,
                ),
            })

    # 3. Recommendations for research (p. 28-29)
    res_text = "\n\n".join([page_texts.get(p, "") for p in [28, 29] if p in page_texts])
    res_match = re.search(r"Recommendations for research\s*(.*?)(?=Rationale and impact|$)", res_text, re.DOTALL | re.I)
    if res_match:
        raw_res = res_match.group(1).strip()
        res_items = re.split(r"(?m)^(?=\d+\s+[A-Z])", raw_res)
        for i, item in enumerate(res_items, start=1):
            item = item.strip()
            if not item or len(item) < 30:
                continue
            cid = f"NG106_RESEARCH_{i:03d}"
            sec = Ng106Section(number="research", title="Recommendations for research", level=1, page_start=28, full_heading="Recommendations for research")
            chunk_text = f"Section: Recommendations for research\n\n{item}"
            non_rec_chunks.append({
                "chunk_id": cid,
                "text": chunk_text,
                "token_count": count_tokens(chunk_text),
                "metadata": build_ng106_chunk_metadata(
                    rec=None,
                    section=sec,
                    subheading="Research recommendation",
                    content_type="research_recommendation",
                    pdf_page_start=28,
                    pdf_page_end=29,
                    text=item,
                ),
            })

    # 4. Rationale and impact (p. 30-35)
    rat_text = "\n\n".join([page_texts.get(p, "") for p in range(30, 36) if p in page_texts])
    rat_match = re.search(r"Rationale and impact\s*(.*?)(?=Context|$)", rat_text, re.DOTALL | re.I)
    raw_rat = rat_match.group(1).strip() if rat_match else rat_text
    if raw_rat:
        rat_blocks = re.split(r"(?i)Return to (?:the )?recommendations", raw_rat)
        for i, rblock in enumerate(rat_blocks, start=1):
            rblock = rblock.strip()
            if not rblock or len(rblock) < 30:
                continue
            cid = f"NG106_RATIONALE_{i:03d}"
            sec = Ng106Section(number="rationale_and_impact", title="Rationale and impact", level=1, page_start=30, full_heading="Rationale and impact")
            chunk_text = f"Section: Rationale and impact\n\n{rblock}"
            non_rec_chunks.append({
                "chunk_id": cid,
                "text": chunk_text,
                "token_count": count_tokens(chunk_text),
                "metadata": build_ng106_chunk_metadata(
                    rec=None,
                    section=sec,
                    subheading="Committee rationale and impact",
                    content_type="committee_rationale",
                    pdf_page_start=30,
                    pdf_page_end=35,
                    text=rblock,
                ),
            })

    # 5. Context (p. 36-37)
    ctx_text = "\n\n".join([page_texts.get(p, "") for p in [36, 37] if p in page_texts])
    if ctx_text.strip():
        cid = "NG106_CONTEXT_001"
        sec = Ng106Section(number="context", title="Context", level=1, page_start=36, full_heading="Context")
        chunk_text = f"Section: Context\n\n{ctx_text.strip()}"
        non_rec_chunks.append({
            "chunk_id": cid,
            "text": chunk_text,
            "token_count": count_tokens(chunk_text),
            "metadata": build_ng106_chunk_metadata(
                rec=None,
                section=sec,
                subheading="Context and background",
                content_type="context",
                pdf_page_start=36,
                pdf_page_end=37,
                text=ctx_text,
            ),
        })

    return non_rec_chunks


def find_page_for_text(text_snippet: str, pages: List[PageData]) -> Tuple[int, int]:
    """Find start and end physical PDF pages containing the text snippet."""
    snippet_start = text_snippet[:60].strip()
    snippet_end = text_snippet[-60:].strip()

    start_p = 1
    end_p = len(pages)

    for p in pages:
        if snippet_start in p.cleaned_text or snippet_start[:30] in p.cleaned_text:
            start_p = p.pdf_page
            break

    for p in reversed(pages):
        if snippet_end in p.cleaned_text or snippet_end[-30:] in p.cleaned_text:
            end_p = p.pdf_page
            break

    if end_p < start_p:
        end_p = start_p

    return start_p, end_p


def run_ng106_pipeline(pdf_path: Optional[str] = None) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """Run complete parsing and chunking pipeline for NICE NG106."""
    start_time = time.time()
    if pdf_path is None:
        pdf_path = str(PROJECT_ROOT / "data" / "raw" / "NICE_NG106.pdf")

    output_dir = PROJECT_ROOT / "data" / "processed"
    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"\n{'='*65}")
    print(f"Starting NICE NG106 Pipeline on {pdf_path}")
    print(f"{'='*65}")

    # Step 1: Extract pages
    print("\n[1/5] Extracting pages with PyMuPDF...")
    pages = extract_pages(pdf_path)
    print(f"  Extracted {len(pages)} pages.")

    # Step 2: Clean text
    print("[2/5] Cleaning text & removing boilerplate...")
    cleaned_pages = clean_all_pages([(p.pdf_page, p.raw_text) for p in pages])
    for page, (_, c_text) in zip(pages, cleaned_pages):
        page.cleaned_text = c_text

    # Step 3: Recommendation extraction from full cleaned body
    print("[3/5] Extracting all 91 NICE recommendations...")
    full_body_text = "\n\n".join([p.cleaned_text for p in pages if 6 <= p.pdf_page <= 27])
    recs = extract_recommendations(full_body_text)
    print(f"  Detected {len(recs)} individual recommendations.")

    rec_chunks: List[Dict[str, Any]] = []
    for rec in recs:
        chunk_id = f"NG106_{rec.recommendation_id}_REC"
        sec = get_section_for_rec_id(rec.recommendation_id)
        p_start, p_end = find_page_for_text(rec.text, pages)

        chunk_text = (
            f"Section: {sec.full_heading}\n"
            f"Recommendation: {rec.recommendation_id}\n\n"
            f"{rec.text.strip()}"
        )
        meta = build_ng106_chunk_metadata(
            rec=rec,
            section=sec,
            subheading=None,
            content_type="recommendation",
            pdf_page_start=p_start,
            pdf_page_end=p_end,
            text=rec.text,
        )
        rec_chunks.append({
            "chunk_id": chunk_id,
            "text": chunk_text,
            "token_count": count_tokens(chunk_text),
            "metadata": meta,
        })

    # Step 4: Extract non-recommendation sections
    print("[4/5] Extracting overview, terms, research, and rationale chunks...")
    non_rec_chunks = extract_non_rec_sections(pages)
    all_chunks = rec_chunks + non_rec_chunks
    print(f"  Generated {len(all_chunks)} total chunks ({len(rec_chunks)} recs + {len(non_rec_chunks)} context/rationale).")

    # Step 5: Write outputs
    print("[5/5] Writing outputs to data/processed/...")
    json_path = output_dir / "NICE_NG106_chunks.json"
    jsonl_path = output_dir / "NICE_NG106_chunks.jsonl"
    preview_path = output_dir / "NICE_NG106_chunks_preview.md"

    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(all_chunks, f, ensure_ascii=False, indent=2)

    with open(jsonl_path, "w", encoding="utf-8") as f:
        for c in all_chunks:
            f.write(json.dumps(c, ensure_ascii=False) + "\n")

    with open(preview_path, "w", encoding="utf-8") as f:
        f.write("# NICE NG106 — Chronic Heart Failure Chunks Preview\n\n")
        for c in all_chunks:
            f.write(f"### `{c['chunk_id']}` ({c['token_count']} tokens)\n")
            f.write(f"- **Content Type:** `{c['metadata']['content_type']}`\n")
            f.write(f"- **Topic:** `{c['metadata']['topic']}` | **Pages:** `{c['metadata']['pdf_page_start']}-{c['metadata']['pdf_page_end']}`\n")
            f.write(f"- **Phenotypes:** `{c['metadata']['clinical_metadata']['heart_failure_phenotypes']}` | **Drugs:** `{c['metadata']['clinical_metadata']['drug_classes']}`\n\n")
            f.write("```text\n")
            f.write(c["text"])
            f.write("\n```\n\n---\n\n")

    elapsed = round(time.time() - start_time, 2)
    stats = {
        "total_chunks": len(all_chunks),
        "total_pages": len(pages),
        "recommendation_chunks": len(rec_chunks),
        "non_rec_chunks": len(non_rec_chunks),
        "processing_time_seconds": elapsed,
    }

    print(f"\n{'='*65}")
    print(f"NICE NG106 PIPELINE COMPLETE ({elapsed}s)")
    print(f"{'='*65}")
    print(f"  Total Chunks:           {len(all_chunks)}")
    print(f"  Direct Recommendations: {len(rec_chunks)} / 91 (100%)")
    print(f"  Rationale & Definitions:{len(non_rec_chunks)}")
    print(f"  JSON:                   {json_path}")
    print(f"  JSONL:                  {jsonl_path}")
    print(f"  Markdown QA:            {preview_path}\n")

    return all_chunks, stats


if __name__ == "__main__":
    run_ng106_pipeline()
