"""
NICE recommendation parser for the NICE3 (NG238) guideline.

Detects:
  - Individual NICE recommendation IDs (e.g. 1.1.7, 1.6.7, 1.10.3)
  - Recommendation date markers ([May 2023], [2008, amended 2014])
  - Cross-references to other recommendations
  - Evidence review references
  - Technology appraisal references (TA385, TA393, etc.)
"""

import re
import logging
from dataclasses import dataclass, field
from typing import List, Optional, Tuple, Dict

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass
class NiceRecommendation:
    """A parsed NICE recommendation."""
    recommendation_id: str              # e.g. "1.7.1"
    text: str                           # Full recommendation text
    original_date: Optional[str] = None  # e.g. "May 2023"
    amended_dates: List[str] = field(default_factory=list)  # e.g. ["December 2023"]
    raw_date_marker: Optional[str] = None  # e.g. "[May 2023, amended December 2023]"
    cross_refs: List[str] = field(default_factory=list)  # e.g. ["1.6.1", "1.7.1"]
    technology_appraisal_refs: List[str] = field(default_factory=list)  # e.g. ["TA385"]
    evidence_review_reference: Optional[str] = None
    external_guideline_references: List[str] = field(default_factory=list)
    start_offset: int = 0
    end_offset: int = 0


# ---------------------------------------------------------------------------
# Recommendation ID detection
# ---------------------------------------------------------------------------

# Pattern for NICE recommendation IDs: 1.X.Y where X can be 1-12, Y can be 1+
# Must be robust against line wrapping and various whitespace
_REC_ID_RE = re.compile(
    r"(?:^|\n)\s*(1\.(?:1[0-2]|[1-9])\.(\d+))\s",
    re.MULTILINE,
)

# Alternative: recommendation ID at the start of a line, possibly followed by text
_REC_ID_LINE_RE = re.compile(
    r"(?:^|\n)\s*(1\.(?:1[0-2]|[1-9])\.(\d+))\b",
    re.MULTILINE,
)


def detect_recommendation_ids(text: str, expected_prefix: Optional[str] = None) -> List[Tuple[int, str]]:
    """Find all recommendation IDs in text.

    Returns list of (position, recommendation_id).
    Filters out cross-references (e.g. 'see recommendation 1.5.1' or references
    to other sections).
    """
    found: List[Tuple[int, str]] = []
    seen_ids = set()

    for m in _REC_ID_LINE_RE.finditer(text):
        rec_id = m.group(1)
        start_idx = m.start()

        # Check if preceded by cross-reference words like 'see recommendation' or '(see '
        prefix_context = text[max(0, start_idx - 35):start_idx].lower()
        if re.search(r"(?:see\s+(?:recommendations?\s+)?|recommendations?\s+|and\s+|\(\s*see\s+)\s*$", prefix_context):
            continue

        # If section prefix is specified (e.g. '1.6'), only match rec IDs belonging to this section ('1.6.X')
        if expected_prefix and not rec_id.startswith(expected_prefix + "."):
            continue

        if rec_id not in seen_ids:
            found.append((start_idx, rec_id))
            seen_ids.add(rec_id)

    return found


# ---------------------------------------------------------------------------
# Date parsing
# ---------------------------------------------------------------------------

# Pattern for date markers like [May 2023], [2008], [2014, amended May 2023]
_DATE_MARKER_RE = re.compile(
    r"\[("
    r"(?:(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+)?\d{4}"
    r"(?:\s*,\s*amended\s+"
    r"(?:(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+)?\d{4}"
    r"(?:\s+and\s+(?:(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+)?\d{4})*"
    r")?"
    r")\]",
    re.IGNORECASE,
)

# For parsing the inner content of a date marker
_ORIGINAL_DATE_RE = re.compile(
    r"^((?:(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+)?\d{4})",
    re.IGNORECASE,
)

_AMENDED_DATES_RE = re.compile(
    r"amended\s+(.*)",
    re.IGNORECASE,
)

_INDIVIDUAL_DATE_RE = re.compile(
    r"((?:(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+)?\d{4})",
    re.IGNORECASE,
)


def parse_date_marker(marker_text: str) -> Tuple[Optional[str], List[str]]:
    """Parse a NICE date marker into original date and amendment dates.

    Examples:
        "May 2023" → ("May 2023", [])
        "2008, amended 2014" → ("2008", ["2014"])
        "2014, amended May 2023 and December 2023" → ("2014", ["May 2023", "December 2023"])
    """
    # Extract original date
    original_match = _ORIGINAL_DATE_RE.search(marker_text)
    original_date = original_match.group(1).strip() if original_match else None

    # Extract amended dates
    amended_dates: List[str] = []
    amended_match = _AMENDED_DATES_RE.search(marker_text)
    if amended_match:
        amended_text = amended_match.group(1)
        for m in _INDIVIDUAL_DATE_RE.finditer(amended_text):
            amended_dates.append(m.group(1).strip())

    return original_date, amended_dates


def find_date_markers(text: str) -> List[Tuple[int, str, Optional[str], List[str]]]:
    """Find all date markers in text.

    Returns list of (position, raw_marker, original_date, amended_dates).
    """
    results = []
    for m in _DATE_MARKER_RE.finditer(text):
        raw = m.group(0)  # includes brackets
        inner = m.group(1)
        original, amended = parse_date_marker(inner)
        results.append((m.start(), raw, original, amended))
    return results


# ---------------------------------------------------------------------------
# Cross-reference extraction
# ---------------------------------------------------------------------------

# "see recommendation 1.6.1" or "recommendations 1.9.2 and 1.9.3"
_CROSS_REF_RE = re.compile(
    r"(?:see\s+)?recommendations?\s+(1\.(?:1[0-2]|[1-9])\.\d+"
    r"(?:\s+and\s+1\.(?:1[0-2]|[1-9])\.\d+)*"
    r"(?:\s*,\s*1\.(?:1[0-2]|[1-9])\.\d+)*)",
    re.IGNORECASE,
)

_REF_ID_EXTRACT_RE = re.compile(r"(1\.(?:1[0-2]|[1-9])\.\d+)")


def extract_cross_references(text: str) -> List[str]:
    """Extract cross-referenced recommendation IDs from text."""
    refs = set()
    for m in _CROSS_REF_RE.finditer(text):
        ref_text = m.group(1)
        for ref_m in _REF_ID_EXTRACT_RE.finditer(ref_text):
            refs.add(ref_m.group(1))
    return sorted(refs)


# ---------------------------------------------------------------------------
# Technology appraisal references
# ---------------------------------------------------------------------------

_TA_REF_RE = re.compile(r"\b(TA\d{2,4})\b")


def extract_technology_appraisals(text: str) -> List[str]:
    """Extract technology appraisal references (e.g. TA385, TA393)."""
    return sorted(set(m.group(1) for m in _TA_REF_RE.finditer(text)))


# ---------------------------------------------------------------------------
# Evidence review references
# ---------------------------------------------------------------------------

_EVIDENCE_REVIEW_RE = re.compile(
    r"evidence\s+review\s+([A-Z](?:\s*[-:]\s*[^\n.]+)?)",
    re.IGNORECASE,
)


def extract_evidence_review_reference(text: str) -> Optional[str]:
    """Extract evidence review reference if present."""
    m = _EVIDENCE_REVIEW_RE.search(text)
    if m:
        ref = m.group(0).strip()
        # Clean up to get a reasonable reference
        ref = re.sub(r"\s+", " ", ref)
        # Limit length
        if len(ref) > 150:
            ref = ref[:150]
        return ref
    return None


# ---------------------------------------------------------------------------
# External guideline references
# ---------------------------------------------------------------------------

_EXT_GUIDELINE_RE = re.compile(
    r"(?:see\s+)?NICE(?:'s|'s)?\s+guideline\s+on\s+([^.(\n]+)",
    re.IGNORECASE,
)


def extract_external_guideline_references(text: str) -> List[str]:
    """Extract references to other NICE guidelines."""
    refs = []
    for m in _EXT_GUIDELINE_RE.finditer(text):
        ref = m.group(1).strip()
        # Normalize
        ref = f"NICE {ref}"
        if ref not in refs:
            refs.append(ref)
    return refs


# ---------------------------------------------------------------------------
# Full recommendation extraction
# ---------------------------------------------------------------------------

def extract_recommendations(section_text: str, section_number: str = "") -> List[NiceRecommendation]:
    """Extract all individual NICE recommendations from a section block.

    Each recommendation ID found becomes a separate recommendation.
    Captures the text from one rec ID to the next (or to end of block).
    """
    recommendations: List[NiceRecommendation] = []

    # Find all recommendation IDs and their positions
    rec_positions = detect_recommendation_ids(
        section_text,
        expected_prefix=section_number if section_number and section_number.startswith("1.") else None
    )

    if not rec_positions:
        return recommendations

    for i, (pos, rec_id) in enumerate(rec_positions):
        # Text runs from this rec ID to the next, or to end
        if i + 1 < len(rec_positions):
            end_pos = rec_positions[i + 1][0]
        else:
            end_pos = len(section_text)

        rec_text = section_text[pos:end_pos].strip()

        # Clean the rec text: remove the ID prefix from the beginning
        clean_text = re.sub(r"^\s*" + re.escape(rec_id) + r"\s*", "", rec_text).strip()

        # Find date marker within this recommendation
        date_markers = find_date_markers(rec_text)
        original_date = None
        amended_dates = []
        raw_date_marker = None

        if date_markers:
            # Use the last date marker (typically at the end of the rec)
            _, raw_date_marker, original_date, amended_dates = date_markers[-1]

        # Extract cross-references
        cross_refs = extract_cross_references(rec_text)
        # Remove self-reference
        cross_refs = [r for r in cross_refs if r != rec_id]

        # Extract technology appraisals
        ta_refs = extract_technology_appraisals(rec_text)

        # Extract evidence review reference
        evidence_ref = extract_evidence_review_reference(rec_text)

        # Extract external guideline references
        ext_refs = extract_external_guideline_references(rec_text)

        recommendations.append(NiceRecommendation(
            recommendation_id=rec_id,
            text=rec_text,
            original_date=original_date,
            amended_dates=amended_dates,
            raw_date_marker=raw_date_marker,
            cross_refs=cross_refs,
            technology_appraisal_refs=ta_refs,
            evidence_review_reference=evidence_ref,
            external_guideline_references=ext_refs,
            start_offset=pos,
            end_offset=end_pos,
        ))

    logger.info("Extracted %d recommendations from section %s", len(recommendations), section_number)
    return recommendations


def validate_recommendation_id(rec_id: str) -> bool:
    """Validate that a recommendation ID matches the expected NICE3 format.

    Pattern: 1.X.Y where X is 1-12 and Y is a positive integer without leading zeros.
    Guards against mis-parsing like "1.10.3" → "1.1.03".
    """
    m = re.fullmatch(r"1\.(1[0-2]|[1-9])\.([1-9]\d*)", rec_id)
    return bool(m)
