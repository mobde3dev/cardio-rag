"""
Semantic chunking engine for the WHO03 hypertension guideline.

Splits section blocks into medically meaningful chunks:
  - Recommendations → self-contained chunks
  - Implementation remarks → separate chunks linked to parent recommendation
  - Evidence/rationale → split at semantic boundaries (400-750 tokens target)
  - Tables → dedicated chunks
  - Algorithms → dedicated chunks

Includes deduplication and validation.
"""

import re
import logging
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Tuple, Set

from src.core.clean_text import clean_chunk_noise
from src.segmenters.who_segmenter import SectionBlock, Section, is_administrative_section
from src.enrichers.who_enricher import (
    detect_recommendation,
    detect_all_recommendations,
    extract_recommendation_statements,
    classify_content_type,
    build_chunk_metadata,
    RecommendationMeta,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Token counter
# ---------------------------------------------------------------------------

class TokenCounter:
    """Configurable token counter for chunk sizing."""

    def __init__(self, encoding_name: str = "cl100k_base"):
        try:
            import tiktoken
            self.encoding = tiktoken.get_encoding(encoding_name)
            self._method = f"tiktoken_{encoding_name}"
        except Exception:
            self.encoding = None
            self._method = "word_estimate"
            logger.warning("tiktoken not available, using word-based estimate")

    @property
    def method(self) -> str:
        return self._method

    def count(self, text: str) -> int:
        if self.encoding:
            return len(self.encoding.encode(text))
        # Fallback: ~1.3 tokens per word
        return int(len(text.split()) * 1.3)


# Module-level counter instance
_counter = TokenCounter()


def count_tokens(text: str) -> int:
    """Count tokens in text."""
    return _counter.count(text)


# ---------------------------------------------------------------------------
# Chunk data structure
# ---------------------------------------------------------------------------

@dataclass
class Chunk:
    """A single RAG chunk."""
    chunk_id: str
    text: str
    token_count: int = 0
    metadata: Dict = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Chunk ID generation
# ---------------------------------------------------------------------------

# Counters per section+type for deterministic IDs
_id_counters: Dict[str, int] = {}


def reset_id_counters():
    """Reset chunk ID counters (call at start of pipeline)."""
    global _id_counters
    _id_counters = {}


def _type_code(content_type: str) -> str:
    """Map content type to short code for chunk IDs."""
    mapping = {
        "recommendation": "REC",
        "implementation_remark": "IMPL",
        "evidence_rationale": "EVID",
        "evidence_to_decision": "E2D",
        "background": "BG",
        "definition": "DEF",
        "clinical_threshold": "THR",
        "drug_guidance": "DRUG",
        "laboratory_guidance": "LAB",
        "risk_assessment": "RISK",
        "follow_up": "FUP",
        "special_setting": "SPEC",
        "algorithm": "ALGO",
        "table": "TBL",
        "research_methodology": "METH",
        "other": "OTH",
        "references": "REF",
    }
    return mapping.get(content_type, "OTH")


def generate_chunk_id(section_number: str, content_type: str) -> str:
    """Generate a deterministic chunk ID.

    Format: WHO03_{section}_{TYPE}_{seq:03d}
    e.g. WHO03_3.4_REC_001
    """
    sec = section_number if section_number else "0"
    code = _type_code(content_type)
    key = f"{sec}_{code}"

    _id_counters[key] = _id_counters.get(key, 0) + 1
    seq = _id_counters[key]

    return f"WHO03_{sec}_{code}_{seq:03d}"


# ---------------------------------------------------------------------------
# Text splitting utilities
# ---------------------------------------------------------------------------

def _split_into_paragraphs(text: str) -> List[str]:
    """Split text into paragraphs (on double newlines)."""
    paragraphs = re.split(r"\n\s*\n", text)
    return [p.strip() for p in paragraphs if p.strip()]


def _split_into_sentences(text: str) -> List[str]:
    """Split text into sentences, careful not to split on abbreviations or numbers."""
    protected = text
    for abbr in ["Dr.", "Mr.", "Mrs.", "Ms.", "e.g.", "i.e.", "vs.", "etc.", "Fig.", "No.", "Vol.", "al.", "Jan.", "Feb."]:
        protected = protected.replace(abbr, abbr.replace(".", "@@DOT@@"))

    sentences = re.split(r"(?<=[.!?])\s+", protected)
    return [s.replace("@@DOT@@", ".").strip() for s in sentences if s.strip()]


def _is_bullet_list(text: str) -> bool:
    """Check if text is a bullet list."""
    lines = text.strip().split("\n")
    bullet_count = sum(1 for l in lines if re.match(r"^\s*[•\-–▪*]\s", l))
    return bullet_count >= 2 and bullet_count / len(lines) > 0.4


# ---------------------------------------------------------------------------
# Semantic block detection within a section
# ---------------------------------------------------------------------------

_REC_BLOCK_START = re.compile(
    r"(?:^|\n)(?:RECOMMENDATION\s+(?:ON\s+)?|WHO\s+(?:recommends|suggests)\b)",
    re.IGNORECASE,
)

_IMPL_BLOCK_START = re.compile(
    r"(?:^|\n)(?:Implementation\s+remark|Remarks?\s+(?:for|on)\s+implementation)",
    re.IGNORECASE,
)

_EVIDENCE_BLOCK_START = re.compile(
    r"(?:^|\n)(?:Evidence\s+(?:and|&)\s+rationale|Summary\s+of\s+evidence|Evidence\s+summary)",
    re.IGNORECASE,
)

_E2D_BLOCK_START = re.compile(
    r"(?:^|\n)Evidence[-\s]+to[-\s]+decision",
    re.IGNORECASE,
)


@dataclass
class SemanticBlock:
    """A detected semantic block within a section."""
    block_type: str  # recommendation, implementation_remark, evidence_rationale, etc.
    text: str
    start_offset: int = 0


def detect_semantic_blocks(text: str) -> List[SemanticBlock]:
    """Split section text into semantic blocks based on sub-headings.

    Detects: recommendations, implementation remarks, evidence, E2D, and general content.
    """
    split_points: List[Tuple[int, str]] = []

    for m in _REC_BLOCK_START.finditer(text):
        split_points.append((m.start(), "recommendation"))
    for m in _IMPL_BLOCK_START.finditer(text):
        split_points.append((m.start(), "implementation_remark"))
    for m in _EVIDENCE_BLOCK_START.finditer(text):
        split_points.append((m.start(), "evidence_rationale"))
    for m in _E2D_BLOCK_START.finditer(text):
        split_points.append((m.start(), "evidence_to_decision"))

    if not split_points:
        return [SemanticBlock(block_type="auto", text=text, start_offset=0)]

    split_points.sort(key=lambda x: x[0])

    blocks: List[SemanticBlock] = []

    if split_points[0][0] > 0:
        pre_text = text[:split_points[0][0]].strip()
        if pre_text:
            blocks.append(SemanticBlock(
                block_type="background",
                text=pre_text,
                start_offset=0,
            ))

    for i, (pos, btype) in enumerate(split_points):
        end = split_points[i + 1][0] if i + 1 < len(split_points) else len(text)
        block_text = text[pos:end].strip()
        if block_text:
            blocks.append(SemanticBlock(
                block_type=btype,
                text=block_text,
                start_offset=pos,
            ))

    return blocks


# ---------------------------------------------------------------------------
# Chunk a recommendation block
# ---------------------------------------------------------------------------

def chunk_recommendation(
    block: SemanticBlock,
    section: Section,
    pdf_page_start: int,
    pdf_page_end: int,
    page_label_start: Optional[str],
    page_label_end: Optional[str],
    rec_id: Optional[str] = None,
) -> Chunk:
    """Create a single self-contained recommendation chunk.

    Keeps together: section title + recommendation title + WHO text +
    strength + evidence certainty.
    """
    rec_meta = detect_recommendation(block.text)

    section_ctx = f"Section: {section.full_heading}\n\n" if section.full_heading else ""
    full_text = section_ctx + block.text

    content_type = "recommendation"
    chunk_id = generate_chunk_id(section.number, content_type)

    metadata = build_chunk_metadata(
        text=full_text,
        section=section,
        pdf_page_start=pdf_page_start,
        pdf_page_end=pdf_page_end,
        page_label_start=page_label_start,
        page_label_end=page_label_end,
        content_type=content_type,
        recommendation_meta=rec_meta,
        recommendation_id=rec_id or section.number,
    )

    tokens = count_tokens(full_text)

    return Chunk(
        chunk_id=chunk_id,
        text=full_text,
        token_count=tokens,
        metadata=metadata,
    )


# ---------------------------------------------------------------------------
# Chunk an implementation remark block
# ---------------------------------------------------------------------------

def chunk_implementation_remark(
    block: SemanticBlock,
    section: Section,
    pdf_page_start: int,
    pdf_page_end: int,
    page_label_start: Optional[str],
    page_label_end: Optional[str],
    parent_rec: Optional[str] = None,
) -> Chunk:
    """Create an implementation remark chunk linked to its parent recommendation."""
    section_ctx = f"Section: {section.full_heading}\n\nImplementation remarks:\n\n"
    full_text = section_ctx + block.text

    content_type = "implementation_remark"
    chunk_id = generate_chunk_id(section.number, content_type)

    metadata = build_chunk_metadata(
        text=full_text,
        section=section,
        pdf_page_start=pdf_page_start,
        pdf_page_end=pdf_page_end,
        page_label_start=page_label_start,
        page_label_end=page_label_end,
        content_type=content_type,
        parent_recommendation=parent_rec or section.number,
    )

    tokens = count_tokens(full_text)

    return Chunk(
        chunk_id=chunk_id,
        text=full_text,
        token_count=tokens,
        metadata=metadata,
    )


# ---------------------------------------------------------------------------
# Chunk evidence/rationale (long text → multiple chunks)
# ---------------------------------------------------------------------------

def chunk_evidence(
    block: SemanticBlock,
    section: Section,
    pdf_page_start: int,
    pdf_page_end: int,
    page_label_start: Optional[str],
    page_label_end: Optional[str],
    target_tokens: int = 600,
    max_tokens: int = 850,
    overlap_tokens: int = 75,
) -> List[Chunk]:
    """Split a long evidence/rationale block into multiple chunks.

    Splits at paragraph and sentence boundaries. Target 400-750 tokens, max ~850.
    50-100 token overlap for continuity.
    """
    content_type = block.block_type
    text = block.text
    section_ctx = f"Section: {section.full_heading}\n\n" if section.full_heading else ""
    ctx_tokens = count_tokens(section_ctx)

    full_single_text = section_ctx + text
    if count_tokens(full_single_text) <= max_tokens:
        chunk_id = generate_chunk_id(section.number, content_type)
        metadata = build_chunk_metadata(
            text=full_single_text,
            section=section,
            pdf_page_start=pdf_page_start,
            pdf_page_end=pdf_page_end,
            page_label_start=page_label_start,
            page_label_end=page_label_end,
            content_type=content_type,
            parent_recommendation=section.number,
        )
        return [Chunk(
            chunk_id=chunk_id,
            text=full_single_text,
            token_count=count_tokens(full_single_text),
            metadata=metadata,
        )]

    # Split into sentences for fine-grained chunking
    sentences = _split_into_sentences(text)
    if not sentences:
        sentences = [text]

    chunks: List[Chunk] = []
    current_sentences: List[str] = []
    current_tokens = 0
    overlap_sentences: List[str] = []

    for sent in sentences:
        st = count_tokens(sent)

        # Check if adding this sentence exceeds target tokens
        if current_sentences and (ctx_tokens + current_tokens + st > target_tokens):
            chunk_text = section_ctx + " ".join(current_sentences)
            chunk_id = generate_chunk_id(section.number, content_type)
            metadata = build_chunk_metadata(
                text=chunk_text,
                section=section,
                pdf_page_start=pdf_page_start,
                pdf_page_end=pdf_page_end,
                page_label_start=page_label_start,
                page_label_end=page_label_end,
                content_type=content_type,
                parent_recommendation=section.number,
            )
            chunks.append(Chunk(
                chunk_id=chunk_id,
                text=chunk_text,
                token_count=count_tokens(chunk_text),
                metadata=metadata,
            ))

            # Build overlap from the end of current_sentences (~50-100 tokens)
            overlap_sentences = []
            ot = 0
            for s in reversed(current_sentences):
                st_rev = count_tokens(s)
                if ot + st_rev > overlap_tokens:
                    break
                overlap_sentences.insert(0, s)
                ot += st_rev

            current_sentences = list(overlap_sentences) + [sent]
            current_tokens = sum(count_tokens(s) for s in current_sentences)
        else:
            current_sentences.append(sent)
            current_tokens += st

    # Flush remaining
    if current_sentences:
        chunk_text = section_ctx + " ".join(current_sentences)
        chunk_id = generate_chunk_id(section.number, content_type)
        metadata = build_chunk_metadata(
            text=chunk_text,
            section=section,
            pdf_page_start=pdf_page_start,
            pdf_page_end=pdf_page_end,
            page_label_start=page_label_start,
            page_label_end=page_label_end,
            content_type=content_type,
            parent_recommendation=section.number,
        )
        chunks.append(Chunk(
            chunk_id=chunk_id,
            text=chunk_text,
            token_count=count_tokens(chunk_text),
            metadata=metadata,
        ))

    return chunks


# ---------------------------------------------------------------------------
# Chunk a table
# ---------------------------------------------------------------------------

def chunk_table(
    markdown: str,
    caption: str,
    section: Section,
    pdf_page: int,
    page_label: Optional[str],
) -> Chunk:
    """Create a chunk for a table."""
    full_text = f"Table: {caption}\n\n{markdown}\n\nSource: WHO03\nSection: {section.full_heading}\nPage: {pdf_page}"

    content_type = "table"
    chunk_id = generate_chunk_id(section.number, content_type)
    metadata = build_chunk_metadata(
        text=full_text,
        section=section,
        pdf_page_start=pdf_page,
        pdf_page_end=pdf_page,
        page_label_start=page_label,
        page_label_end=page_label,
        content_type=content_type,
    )

    return Chunk(
        chunk_id=chunk_id,
        text=full_text,
        token_count=count_tokens(full_text),
        metadata=metadata,
    )


# ---------------------------------------------------------------------------
# Chunk an algorithm / figure
# ---------------------------------------------------------------------------

def chunk_algorithm(
    text: str,
    figure_desc: str,
    section: Section,
    pdf_page: int,
    page_label: Optional[str],
    requires_manual_review: bool = True,
) -> Chunk:
    """Create a chunk for a clinical algorithm or figure."""
    full_text = text
    if figure_desc and figure_desc not in text:
        full_text = f"{figure_desc}\n\n{text}"

    content_type = "algorithm"
    chunk_id = generate_chunk_id(section.number, content_type)
    metadata = build_chunk_metadata(
        text=full_text,
        section=section,
        pdf_page_start=pdf_page,
        pdf_page_end=pdf_page,
        page_label_start=page_label,
        page_label_end=page_label,
        content_type=content_type,
    )
    metadata["has_figure"] = True
    metadata["requires_manual_review"] = requires_manual_review

    return Chunk(
        chunk_id=chunk_id,
        text=full_text,
        token_count=count_tokens(full_text),
        metadata=metadata,
    )


# ---------------------------------------------------------------------------
# Process a full section block
# ---------------------------------------------------------------------------

def chunk_section_block(
    section_block: SectionBlock,
) -> List[Chunk]:
    """Process a SectionBlock into a list of Chunks.

    Detects semantic sub-blocks (recommendation, implementation remark,
    evidence, etc.) and creates appropriate chunks for each.
    """
    section = section_block.section
    text = section_block.text

    if not text.strip():
        return []

    # Skip administrative sections
    if is_administrative_section(section):
        logger.info("Skipping administrative section: %s %s", section.number, section.title)
        return []

    chunks: List[Chunk] = []
    p_start = section_block.pdf_page_start
    p_end = section_block.pdf_page_end
    l_start = section_block.page_label_start
    l_end = section_block.page_label_end
    sec_num = section.number

    # -----------------------------------------------------------------------
    # Case A: Recommendation Sections (3.1 to 3.8 and Executive Summary)
    # -----------------------------------------------------------------------
    if sec_num.startswith("3.") or "executive summary" in section.title.lower():
        # 1. Extract recommendation statements
        rec_stmts = extract_recommendation_statements(text)
        for stmt_text, rec_meta in rec_stmts:
            section_ctx = f"Section: {section.full_heading}\n\n" if section.full_heading else ""
            full_text = section_ctx + stmt_text
            content_type = "recommendation"
            chunk_id = generate_chunk_id(sec_num, content_type)

            metadata = build_chunk_metadata(
                text=full_text,
                section=section,
                pdf_page_start=p_start,
                pdf_page_end=p_end,
                page_label_start=l_start,
                page_label_end=l_end,
                content_type=content_type,
                recommendation_meta=rec_meta,
                recommendation_id=sec_num if sec_num else None,
            )
            chunks.append(Chunk(
                chunk_id=chunk_id,
                text=full_text,
                token_count=count_tokens(full_text),
                metadata=metadata,
            ))

        # 2. Extract Implementation remarks
        impl_m = re.search(
            r"Implementation\s+remarks?:\s*\n(.*?)(?=\n\s*(?:Evidence\s+(?:and|&)\s+rationale|Summary\s+of\s+evidence|Evidence[-\s]+to[-\s]+decision|$))",
            text, re.IGNORECASE | re.DOTALL,
        )
        if impl_m:
            impl_text = impl_m.group(1).strip()
            if impl_text:
                section_ctx = f"Section: {section.full_heading}\n\nImplementation remarks:\n\n"
                full_text = section_ctx + impl_text
                content_type = "implementation_remark"
                chunk_id = generate_chunk_id(sec_num, content_type)
                metadata = build_chunk_metadata(
                    text=full_text,
                    section=section,
                    pdf_page_start=p_start,
                    pdf_page_end=p_end,
                    page_label_start=l_start,
                    page_label_end=l_end,
                    content_type=content_type,
                    parent_recommendation=sec_num,
                )
                chunks.append(Chunk(
                    chunk_id=chunk_id,
                    text=full_text,
                    token_count=count_tokens(full_text),
                    metadata=metadata,
                ))

        # 3. Extract Evidence and rationale
        evid_m = re.search(
            r"(?:Evidence\s+(?:and|&)\s+rationale|Summary\s+of\s+evidence)\s*\n(.*?)(?=\n\s*Evidence[-\s]+to[-\s]+decision|$)",
            text, re.IGNORECASE | re.DOTALL,
        )
        if evid_m:
            evid_text = evid_m.group(1).strip()
            if evid_text:
                evid_block = SemanticBlock(block_type="evidence_rationale", text=evid_text)
                evid_chunks = chunk_evidence(
                    block=evid_block,
                    section=section,
                    pdf_page_start=p_start,
                    pdf_page_end=p_end,
                    page_label_start=l_start,
                    page_label_end=l_end,
                )
                chunks.extend(evid_chunks)

        # 4. Extract Evidence-to-decision considerations
        e2d_m = re.search(
            r"Evidence[-\s]+to[-\s]+decision[^\n]*\n(.*)",
            text, re.IGNORECASE | re.DOTALL,
        )
        if e2d_m:
            e2d_text = e2d_m.group(1).strip()
            if e2d_text:
                e2d_block = SemanticBlock(block_type="evidence_to_decision", text=e2d_text)
                e2d_chunks = chunk_evidence(
                    block=e2d_block,
                    section=section,
                    pdf_page_start=p_start,
                    pdf_page_end=p_end,
                    page_label_start=l_start,
                    page_label_end=l_end,
                )
                chunks.extend(e2d_chunks)

        # If no recommendation was extracted in a non-executive summary section (fallback)
        if not chunks and text.strip():
            sem_blocks = detect_semantic_blocks(text)
            for block in sem_blocks:
                content_type = classify_content_type(block.text, section)
                section_ctx = f"Section: {section.full_heading}\n\n"
                full_text = section_ctx + block.text
                chunk_id = generate_chunk_id(sec_num, content_type)
                metadata = build_chunk_metadata(
                    text=full_text,
                    section=section,
                    pdf_page_start=p_start,
                    pdf_page_end=p_end,
                    page_label_start=l_start,
                    page_label_end=l_end,
                    content_type=content_type,
                )
                chunks.append(Chunk(
                    chunk_id=chunk_id,
                    text=full_text,
                    token_count=count_tokens(full_text),
                    metadata=metadata,
                ))

        return chunks

    # -----------------------------------------------------------------------
    # Case B: Other Sections (1 Introduction, 2 Methods, 4 Special Settings, 5, 6, Annexes)
    # -----------------------------------------------------------------------
    sem_blocks = detect_semantic_blocks(text)

    for block in sem_blocks:
        content_type = classify_content_type(block.text, section)
        section_ctx = f"Section: {section.full_heading}\n\n"
        full_text = section_ctx + block.text
        tokens = count_tokens(full_text)

        if tokens > 900:
            sub_block = SemanticBlock(block_type=content_type, text=block.text)
            sub_chunks = chunk_evidence(
                block=sub_block,
                section=section,
                pdf_page_start=p_start,
                pdf_page_end=p_end,
                page_label_start=l_start,
                page_label_end=l_end,
            )
            chunks.extend(sub_chunks)
        else:
            chunk_id = generate_chunk_id(sec_num, content_type)
            metadata = build_chunk_metadata(
                text=full_text,
                section=section,
                pdf_page_start=p_start,
                pdf_page_end=p_end,
                page_label_start=l_start,
                page_label_end=l_end,
                content_type=content_type,
            )
            chunks.append(Chunk(
                chunk_id=chunk_id,
                text=full_text,
                token_count=tokens,
                metadata=metadata,
            ))

    return chunks


# ---------------------------------------------------------------------------
# Deduplication
# ---------------------------------------------------------------------------

def _normalize_for_dedup(text: str) -> str:
    """Normalize text for duplicate comparison."""
    # Remove section context prefix, collapse whitespace
    text = re.sub(r"^Section:.*?\n\n", "", text, flags=re.DOTALL)
    text = re.sub(r"\s+", " ", text).strip().lower()
    return text


def deduplicate_chunks(chunks: List[Chunk]) -> List[Chunk]:
    """Mark duplicate chunks and clean noise.

    The main recommendation section version is canonical (clinical_priority=1).
    Duplicates in executive summary or implementation tools are flagged.
    """
    for chunk in chunks:
        chunk.text = clean_chunk_noise(chunk.text)
        chunk.token_count = count_tokens(chunk.text)
        chunk.metadata["token_count"] = chunk.token_count

    # Group by normalized text
    text_to_chunks: Dict[str, List[Chunk]] = {}
    for chunk in chunks:
        norm = _normalize_for_dedup(chunk.text)
        # Use first 200 chars as dedup key (fast comparison)
        key = norm[:200]
        if key not in text_to_chunks:
            text_to_chunks[key] = []
        text_to_chunks[key].append(chunk)

    duplicates_found = 0
    for key, group in text_to_chunks.items():
        if len(group) <= 1:
            for chunk in group:
                chunk.metadata["is_canonical"] = not chunk.metadata.get("is_duplicate", False)
            continue

        # Find the canonical chunk (highest priority = lowest number)
        canonical = min(group, key=lambda c: c.metadata.get("clinical_priority", 99))

        for chunk in group:
            if chunk.chunk_id != canonical.chunk_id:
                chunk.metadata["is_duplicate"] = True
                chunk.metadata["is_canonical"] = False
                chunk.metadata["canonical_chunk_id"] = canonical.chunk_id
                duplicates_found += 1
            else:
                chunk.metadata["is_duplicate"] = False
                chunk.metadata["is_canonical"] = True
                chunk.metadata["canonical_chunk_id"] = None

    if duplicates_found:
        logger.info("Marked %d duplicate chunks", duplicates_found)

    return chunks


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------

def validate_chunks(
    chunks: List[Chunk],
    total_pdf_pages: int,
) -> List[str]:
    """Validate chunks and return a list of error messages.

    The pipeline should fail if any critical errors are found.
    """
    errors: List[str] = []
    warnings: List[str] = []
    seen_ids: Set[str] = set()

    for chunk in chunks:
        meta = chunk.metadata

        # 1. No source file
        if not meta.get("source_file"):
            errors.append(f"{chunk.chunk_id}: missing source_file")

        # 2. No page number
        if not meta.get("pdf_page_start"):
            errors.append(f"{chunk.chunk_id}: missing pdf_page_start")

        # 3. Empty text
        if not chunk.text.strip():
            errors.append(f"{chunk.chunk_id}: empty text")

        # 4. Duplicate IDs
        if chunk.chunk_id in seen_ids:
            errors.append(f"{chunk.chunk_id}: duplicate chunk ID")
        seen_ids.add(chunk.chunk_id)

        # 5 & 6. Recommendation missing strength/certainty
        if meta.get("content_type") == "recommendation":
            if not meta.get("recommendation_strength"):
                warnings.append(
                    f"{chunk.chunk_id}: recommendation without strength classification"
                )
            if not meta.get("evidence_certainty"):
                warnings.append(
                    f"{chunk.chunk_id}: recommendation without evidence certainty"
                )

        # 7. Oversized chunks
        if chunk.token_count > 1000:
            has_reason = meta.get("content_type") in ("table", "algorithm")
            if not has_reason:
                warnings.append(
                    f"{chunk.chunk_id}: {chunk.token_count} tokens (exceeds ~1000 limit)"
                )

        # 9. Page out of range
        page_start = meta.get("pdf_page_start", 0)
        page_end = meta.get("pdf_page_end", 0)
        if page_start > total_pdf_pages or page_end > total_pdf_pages:
            errors.append(
                f"{chunk.chunk_id}: page reference out of range "
                f"(start={page_start}, end={page_end}, total={total_pdf_pages})"
            )

    # Log results
    for e in errors:
        logger.error("VALIDATION ERROR: %s", e)
    for w in warnings:
        logger.warning("VALIDATION WARNING: %s", w)

    return errors
