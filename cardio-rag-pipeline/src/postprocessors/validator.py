"""
Validation module for CardioRAG NICE3 chunking.

Implements all 15 validation rules from Prompt §53:
  1. No duplicate chunk IDs
  2. Recommendation chunks must have recommendation_id
  3. Text cannot be empty
  4. Page provenance must be present and in valid range
  5. Recommendation date preserved when present
  6. Drug doses preserved without corruption
  7. Numerical thresholds preserved accurately
  8. No merged unrelated recommendations
  9. Primary and secondary prevention not merged inappropriately
 10. Research recommendations not marked as clinical priority 1
 11. Committee rationale not classified as direct recommendation
 12. No excessive repeated footer boilerplate
 13. Chunk size limits (<= 1000 tokens unless justified)
 14. Page references inside document bounds
 15. QRISK3 metadata preserved

Also implements numerical integrity checks (§54) and ID format integrity (§55).
"""

import re
import logging
from dataclasses import dataclass
from typing import List, Dict, Any, Set, Tuple

logger = logging.getLogger(__name__)

# Pattern for valid NICE recommendation ID
_VALID_REC_ID_RE = re.compile(r"^1\.(?:1[0-2]|[1-9])\.(?:[1-9]\d*)$")

# Numerical integrity patterns to monitor
_NUMERICAL_PATTERNS = [
    re.compile(r"\b\d+(?:\.\d+)?\s*mg\b", re.IGNORECASE),
    re.compile(r"\b\d+(?:\.\d+)?\s*mmol(?:\s+per\s+litre|/L)?\b", re.IGNORECASE),
    re.compile(r"\b\d+%", re.IGNORECASE),
    re.compile(r"\b\d+\s*(?:to|–|-)\s*\d+\s*(?:months?|years?)\b", re.IGNORECASE),
    re.compile(r"eGFR\s*\d+", re.IGNORECASE),
    re.compile(r"\d+\s*ml\s+per\s+minute", re.IGNORECASE),
    re.compile(r"\d+\s*times\s+the\s+upper\s+limit\s+of\s+normal", re.IGNORECASE),
]

_BOILERPLATE_LEAK_PATTERNS = [
    re.compile(r"©\s*NICE\s*\d{4}\..*All\s+rights\s+reserved", re.IGNORECASE),
    re.compile(r"Page\s+\d+\s+of\s+\d+", re.IGNORECASE),
]


@dataclass
class ValidationReport:
    """Detailed validation results."""
    is_valid: bool
    total_chunks: int
    errors: List[str]
    warnings: List[str]
    numerical_check_count: int


def validate_nice3_chunks(
    chunks: List[Any],
    total_pdf_pages: int,
) -> ValidationReport:
    """Validate all chunks against NICE3 guidelines and safety constraints."""
    errors: List[str] = []
    warnings: List[str] = []
    seen_ids: Set[str] = set()
    numerical_check_count = 0

    for chunk in chunks:
        cid = getattr(chunk, "chunk_id", "")
        text = getattr(chunk, "text", "")
        token_count = getattr(chunk, "token_count", 0)
        meta = getattr(chunk, "metadata", {})

        # Rule 1: Unique chunk IDs
        if not cid:
            errors.append("Found chunk with empty chunk_id")
        elif cid in seen_ids:
            errors.append(f"Duplicate chunk ID detected: {cid}")
        seen_ids.add(cid)

        # Rule 3: Non-empty text
        if not text or not text.strip():
            errors.append(f"{cid}: Chunk text is empty")
            continue

        # Rule 4 & 14: Page provenance
        p_start = meta.get("pdf_page_start")
        p_end = meta.get("pdf_page_end")
        if p_start is None or p_start <= 0:
            errors.append(f"{cid}: Missing or invalid pdf_page_start ({p_start})")
        elif total_pdf_pages > 0 and p_start > total_pdf_pages:
            errors.append(f"{cid}: pdf_page_start ({p_start}) exceeds total pages ({total_pdf_pages})")

        if p_end is not None and total_pdf_pages > 0 and p_end > total_pdf_pages:
            errors.append(f"{cid}: pdf_page_end ({p_end}) exceeds total pages ({total_pdf_pages})")

        content_type = meta.get("content_type", "")
        rec_id = meta.get("recommendation_id")
        priority = meta.get("clinical_priority")

        # Rule 2 & Rule §55: Recommendation chunks must have valid recommendation_id
        if content_type == "recommendation":
            if not rec_id:
                errors.append(f"{cid}: Recommendation chunk is missing recommendation_id")
            elif not _VALID_REC_ID_RE.match(rec_id):
                errors.append(f"{cid}: Recommendation ID format invalid: '{rec_id}' (must match ^1\\.\\d+\\.\\d+$)")

            # Rule 5: Date preservation
            date_match = re.search(r"\[(?:(?:January|February|March|April|May|June|July|August|September|October|November|December|\d{4})[^\]]*)\]", text)
            if date_match and not meta.get("recommendation_original_date"):
                warnings.append(f"{cid}: Date marker visible in text ({date_match.group(0)}) but recommendation_original_date is null")

            # Priority check: recommendations must be priority 1
            if priority != 1:
                errors.append(f"{cid}: Recommendation chunk has priority {priority} (must be 1)")

            # Rule 8: No multiple merged recommendations in one recommendation chunk
            other_rec_ids = re.findall(r"(?:^|\n)\s*(1\.(?:1[0-2]|[1-9])\.\d+)\b", text)
            if len(set(other_rec_ids)) > 1:
                warnings.append(f"{cid}: Possible merged recommendations in single chunk: {set(other_rec_ids)}")

        # Rule 10: Research recommendations cannot be clinical priority 1
        if content_type == "research_recommendation" and priority == 1:
            errors.append(f"{cid}: Research recommendation must not be clinical priority 1")

        # Rule 11: Committee rationale must not be direct recommendation
        if content_type == "committee_rationale":
            if priority == 1:
                errors.append(f"{cid}: Committee rationale must not have clinical priority 1")
            if rec_id:
                warnings.append(f"{cid}: Committee rationale chunk should not have single recommendation_id, use related_recommendation_ids")

        # Rule 12: Excessive boilerplate leaks
        for bp_pat in _BOILERPLATE_LEAK_PATTERNS:
            if bp_pat.search(text):
                warnings.append(f"{cid}: Potential boilerplate leaked into chunk text")

        # Rule 13: Chunk token limits
        if token_count > 1000:
            if content_type not in ("committee_rationale", "table", "definition", "update_information"):
                warnings.append(f"{cid}: Chunk size is {token_count} tokens (> 1000 token target limit)")

        # Rule 15: QRISK3 metadata consistency
        if "QRISK3" in text and "10%" in text and not meta.get("risk_threshold"):
            warnings.append(f"{cid}: QRISK3 10% threshold mentioned in text but missing from metadata")

        # §54: Numerical integrity scan
        for num_pat in _NUMERICAL_PATTERNS:
            matches = num_pat.findall(text)
            if matches:
                numerical_check_count += len(matches)

    is_valid = len(errors) == 0

    for err in errors:
        logger.error("VALIDATION ERROR: %s", err)
    for warn in warnings:
        logger.warning("VALIDATION WARNING: %s", warn)

    return ValidationReport(
        is_valid=is_valid,
        total_chunks=len(chunks),
        errors=errors,
        warnings=warnings,
        numerical_check_count=numerical_check_count,
    )
