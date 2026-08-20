"""
Deduplication module for CardioRAG.

Deduplicates chunks according to medical safety rules:
  - Removes exact boilerplate duplicates and identical accidental extractions
  - Preserves legitimate clinical repetition where context/role differs
    (e.g., recommendation vs rationale vs monitoring)
  - Identifies canonical chunks and marks duplicates with metadata
"""

import re
import logging
from typing import List, Dict, Any, TypeVar

logger = logging.getLogger(__name__)

T = TypeVar("T")


def _normalize_text_for_dedup(text: str) -> str:
    """Normalize text for duplicate comparison."""
    # Remove Section / Subheading / Recommendation context headers
    text = re.sub(r"^(?:Section|Subheading|Recommendation|Table|Definition):.*?\n\n", "", text, flags=re.DOTALL | re.MULTILINE)
    # Collapse whitespace and lowercase
    text = re.sub(r"\s+", " ", text).strip().lower()
    return text


def deduplicate_nice_chunks(chunks: List[Any]) -> List[Any]:
    """Deduplicate NICE chunks while preserving clinical context differences.

    Rules:
    - Never merge or drop recommendations that have distinct recommendation_ids
    - Only flag exact text duplicates with same or lower clinical priority
    - Higher priority (lower number) chunk is canonical
    """
    text_to_chunks: Dict[str, List[Any]] = {}

    for chunk in chunks:
        # Don't deduplicate distinct recommendations even if wording is close
        rec_id = chunk.metadata.get("recommendation_id")
        content_type = chunk.metadata.get("content_type", "")

        norm_text = _normalize_text_for_dedup(chunk.text)
        if len(norm_text) < 30:
            continue

        # Key combines content_type (to avoid collapsing rec with rationale) and normalized text prefix
        key = f"{content_type}::{norm_text[:250]}"
        if key not in text_to_chunks:
            text_to_chunks[key] = []
        text_to_chunks[key].append(chunk)

    duplicates_found = 0
    for key, group in text_to_chunks.items():
        if len(group) <= 1:
            continue

        # If they have distinct recommendation IDs, they are distinct recommendations - do not mark duplicate
        rec_ids = {c.metadata.get("recommendation_id") for c in group if c.metadata.get("recommendation_id")}
        if len(rec_ids) > 1:
            continue

        # Find canonical chunk (highest priority = lowest priority number, then lowest page)
        canonical = min(
            group,
            key=lambda c: (
                c.metadata.get("clinical_priority", 99),
                c.metadata.get("pdf_page_start", 999)
            )
        )

        for chunk in group:
            if chunk.chunk_id != canonical.chunk_id:
                chunk.metadata["is_duplicate"] = True
                chunk.metadata["canonical_chunk_id"] = canonical.chunk_id
                duplicates_found += 1

    if duplicates_found:
        logger.info("Marked %d duplicate chunks in NICE3", duplicates_found)

    return chunks
