"""
Text cleaning module for CardioRAG.

Removes PDF noise (headers, footers, boilerplate) while carefully
preserving all medical content (drug names, BP values, units,
recommendation strength, evidence grades, clinical abbreviations).
"""

import re
import logging
from collections import Counter
from typing import List, Set, Tuple

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Medical safelist — patterns that must NEVER be removed or altered
# ---------------------------------------------------------------------------

# Common medical abbreviations in cardiovascular and hypertension guidelines
MEDICAL_ABBREVIATIONS = {
    "ACEi", "ARB", "CCB", "CKD", "CVD", "SBP", "DBP", "BP",
    "HCTZ", "ACEI", "MI", "HF", "LVH", "GFR", "eGFR", "WHO",
    "PICO", "GRADE", "RCT", "NNT", "CI", "HR", "OR", "RR",
    "mmHg", "mg", "kg", "mL", "dL", "mg/dL", "mmol/L", "mmol",
    "HIV", "DM", "T2DM", "T1DM", "COPD", "AF", "PAD", "TIA", "ACS",
    "NSAID", "OTC", "ECG", "ABPM", "HBPM",
    "LDL", "HDL", "non-HDL", "QRISK", "QRISK2", "QRISK3",
    "HbA1c", "BMI", "ALT", "AST", "TSH", "CK", "PCSK9",
    "TA385", "TA393", "TA394", "TA694", "TA733",
}

# Patterns that represent clinical content — protect from removal
_CLINICAL_PATTERNS = [
    re.compile(r"\d{2,3}\s*[-–]\s*\d{2,3}\s*mmHg"),     # 130–139 mmHg
    re.compile(r"[≥≤<>]\s*\d{2,3}\s*mmHg"),              # ≥140 mmHg
    re.compile(r"\d+(\.\d+)?\s*mg\b"),                   # 20 mg, 80 mg
    re.compile(r"\b\d+\s*[-–]\s*\d+\s*mg\b"),             # 25–50 mg
    re.compile(r"\b\d+(\.\d+)?\s*mmol(?:\s+per\s+litre|/L)?\b", re.IGNORECASE), # 2.0 mmol per litre
    re.compile(r"\b\d+%", re.IGNORECASE),                 # 10%, 40%
    re.compile(r"\bQRISK[23]?\b", re.IGNORECASE),
    re.compile(r"\batorvastatin\b", re.IGNORECASE),
    re.compile(r"\bezetimibe\b", re.IGNORECASE),
    re.compile(r"\bstatin[s]?\b", re.IGNORECASE),
    re.compile(r"(?:strong|conditional)\s+recommendation", re.IGNORECASE),
    re.compile(r"(?:high|moderate|low|very\s+low)[-–\s]*certainty\s+evidence", re.IGNORECASE),
    re.compile(r"WHO\s+(?:recommends|suggests)", re.IGNORECASE),
    re.compile(r"RECOMMENDATION\s+ON", re.IGNORECASE),
    re.compile(r"\[(?:(?:January|February|March|April|May|June|July|August|September|October|November|December|\d{4})[^\]]*)\]"), # Date markers [May 2023]
    re.compile(r"1\.(?:1[0-2]|[1-9])\.\d+"),              # Recommendation IDs
    re.compile(r"Why\s+the\s+committee\s+made\s+(?:the|these)?\s*recommendations?", re.IGNORECASE),
    re.compile(r"How\s+the\s+recommendations?\s+might\s+affect\s+(?:practice|services|the\s+NHS)", re.IGNORECASE),
]


# ---------------------------------------------------------------------------
# Noise detection
# ---------------------------------------------------------------------------

# Known boilerplate patterns (case-insensitive)
_BOILERPLATE_PATTERNS = [
    re.compile(r"^\s*ISBN\s", re.IGNORECASE),
    re.compile(r"^\s*[©\ufffd]?\s*NICE\s*\d{4}\..*", re.IGNORECASE),
    re.compile(r"^\s*conditions#notice-of-rights.*", re.IGNORECASE),
    re.compile(r"^\s*©\s", re.IGNORECASE),
    re.compile(r"^\s*Copyright\s", re.IGNORECASE),
    re.compile(r"^\s*All\s+rights\s+reserved", re.IGNORECASE),
    re.compile(r"^\s*https?://", re.IGNORECASE),
    re.compile(r"^\s*www\.", re.IGNORECASE),
    re.compile(r"^\s*Printed\s+in\s", re.IGNORECASE),
    re.compile(r"^\s*Published\s+by\s", re.IGNORECASE),
    re.compile(r"^\s*WHO/", re.IGNORECASE),
    re.compile(r"^\s*GUIDELINE\s+FOR\s+THE\s+PHARMACOLOGICAL\s+TREATMENT\s+OF\s+HYPERTENSION\s+IN\s+ADULTS\s*$", re.IGNORECASE),
    re.compile(r"^\s*Cardiovascular\s+disease:\s*risk\s+assessment\s+and\s+reduction.*lipid\s+modification\s*$", re.IGNORECASE),
    re.compile(r"^\s*\(NG238\)\s*$", re.IGNORECASE),
    re.compile(r"^\s*Page\s+\d+\s+of(?:\s+\d+)?\s*$", re.IGNORECASE),
    re.compile(r"^\s*RECOMMENDATIONS\s*$", re.IGNORECASE),
    re.compile(r"^\s*ANNEXES\s*$", re.IGNORECASE),
]


def _is_clinical_line(line: str) -> bool:
    """Return True if the line contains clinical content that must be kept."""
    stripped = line.strip()
    if not stripped:
        return False
    for pat in _CLINICAL_PATTERNS:
        if pat.search(stripped):
            return True
    for abbr in MEDICAL_ABBREVIATIONS:
        if re.search(r"\b" + re.escape(abbr) + r"\b", stripped):
            return True
    return False


def detect_noise_patterns(pages_text: List[str], min_frequency: float = 0.10) -> Set[str]:
    """Detect repeated lines across pages that are likely headers / footers.

    A line that appears on more than *min_frequency* fraction of pages
    (and is not clinical content) is considered noise.
    """
    line_counter: Counter = Counter()
    total_pages = len(pages_text)

    for text in pages_text:
        # De-duplicate within a single page to avoid double-counting
        seen_on_page: Set[str] = set()
        for line in text.split("\n"):
            normalized = line.strip()
            if normalized and normalized not in seen_on_page:
                seen_on_page.add(normalized)
                line_counter[normalized] += 1

    threshold = max(3, int(total_pages * min_frequency))
    noise: Set[str] = set()

    for line_text, count in line_counter.items():
        if count < threshold:
            continue
        # If it's a known boilerplate header, it's definitely noise
        if _is_boilerplate(line_text):
            noise.add(line_text)
            continue
        # Do NOT flag clinical content
        if _is_clinical_line(line_text):
            continue
        # Do not flag very short numeric lines (could be page numbers we handle separately)
        if line_text.isdigit():
            continue
        noise.add(line_text)
        logger.debug("Noise pattern detected (%d occurrences): %r", count, line_text[:80])

    logger.info("Detected %d noise patterns (threshold=%d pages)", len(noise), threshold)
    return noise


# ---------------------------------------------------------------------------
# Line-level cleaning
# ---------------------------------------------------------------------------

def _is_page_number_only(line: str) -> bool:
    """Return True if the line is just a standalone page number or roman numeral."""
    stripped = line.strip()
    if re.fullmatch(r"\d{1,3}", stripped):
        return True
    if re.fullmatch(r"[ivxlcdm]{1,6}", stripped, re.IGNORECASE):
        return True
    return False


def _is_boilerplate(line: str) -> bool:
    """Return True if the line matches known boilerplate patterns."""
    for pat in _BOILERPLATE_PATTERNS:
        if pat.search(line):
            return True
    return False


def clean_page_text(
    raw_text: str,
    noise_patterns: Set[str],
) -> str:
    """Clean a single page's text.

    Removes:
      - lines matching detected noise patterns
      - standalone page numbers
      - known boilerplate (ISBN, copyright, URLs repeated in footers)
      - fully empty lines (collapsed later)

    Preserves:
      - all clinical content
      - bullets, numbered lists
      - recommendation wording
    """
    lines = raw_text.split("\n")
    cleaned: List[str] = []

    for line in lines:
        stripped = line.strip()

        # Skip empty lines (will be normalised later)
        if not stripped:
            continue

        # Skip standalone page numbers
        if _is_page_number_only(stripped):
            continue

        # Skip known boilerplate headers/footers
        if _is_boilerplate(stripped):
            continue

        # Skip noise patterns (repeated headers/footers)
        if stripped in noise_patterns:
            continue

        cleaned.append(line)

    return "\n".join(cleaned)


# ---------------------------------------------------------------------------
# Chunk-level noise cleaning
# ---------------------------------------------------------------------------

_CHUNK_LEAK_PATTERNS = [
    re.compile(r"\bGUIDELINE\s+FOR\s+THE\s+PHARMACOLOGICAL\s+TREATMENT\s+OF\s+HYPERTENSION\s+IN\s+ADULTS\b", re.IGNORECASE),
    re.compile(r"\bGUIDELINE\s+FOR\s+T(?:HE)?\b", re.IGNORECASE),
    re.compile(r"\bCardiovascular\s+disease:\s*risk\s+assessment\s+and\s+reduction(?:,\s*including\s+lipid\s+modification)?\b", re.IGNORECASE),
    re.compile(r"\(NG238\)", re.IGNORECASE),
    re.compile(r"[©\ufffd]?\s*NICE\s*\d{4}\..*", re.IGNORECASE),
    re.compile(r"Subject\s+to\s+Notice\s+of\s+rights.*", re.IGNORECASE),
    re.compile(r"conditions#notice-of-rights\)?\.?", re.IGNORECASE),
    re.compile(r"Page\s+\d+\s+of(?:\s+\d+)?", re.IGNORECASE),
]


def clean_chunk_noise(text: str) -> str:
    """Strip running header/footer leaks and contamination from chunk text."""
    lines = text.split("\n")
    cleaned_lines = []
    for line in lines:
        stripped = line.strip()
        if not stripped:
            cleaned_lines.append("")
            continue
        # Skip pure boilerplate lines
        if _is_boilerplate(stripped):
            continue
        # Remove embedded leak patterns
        cur = line
        for pat in _CHUNK_LEAK_PATTERNS:
            cur = pat.sub("", cur)
        if cur.strip():
            cleaned_lines.append(cur)

    result = "\n".join(cleaned_lines)
    # Collapse multiple blank lines
    result = re.sub(r"\n{3,}", "\n\n", result)
    return result.strip()


# ---------------------------------------------------------------------------
# Text normalization
# ---------------------------------------------------------------------------

# Hyphenation caused by PDF line wrapping (NOT medical hyphens)
# e.g., "phar-\nmacological" → "pharmacological"
# But NOT "130-139 mmHg" or "thiazide-like"
_WRAP_HYPHEN_RE = re.compile(r"(\w)-\n\s*(\w)")


def _rejoin_wrapped_words(text: str) -> str:
    """Rejoin words split by PDF line-wrap hyphenation.

    Only removes hyphens at end-of-line followed by a lowercase letter,
    which indicates wrapping rather than a meaningful hyphen.
    """
    # Only rejoin when the second part starts with lowercase
    def _replacer(m: re.Match) -> str:
        before = m.group(1)
        after = m.group(2)
        if after.islower():
            return before + after
        return m.group(0)  # keep as-is

    return _WRAP_HYPHEN_RE.sub(_replacer, text)


def normalize_text(text: str) -> str:
    """Normalize text without altering medical meaning.

    - Collapse excessive whitespace
    - Rejoin PDF line-wrap hyphenation
    - Normalize Unicode bullets to standard bullet '•'
    - Collapse multiple blank lines to a single blank line
    - Preserve comparison operators: ≥ ≤ < >
    - Preserve en-dashes in ranges: 130–139
    - Preserve all medical terminology and units
    """
    # Rejoin wrapped words first (before collapsing newlines)
    text = _rejoin_wrapped_words(text)

    # Normalize various Unicode bullet characters
    text = re.sub(r"[▪▸►◦◆■●○‣⁃]", "•", text)

    # Collapse runs of whitespace within a line (tabs, multiple spaces)
    text = re.sub(r"[ \t]+", " ", text)

    # Collapse 3+ consecutive newlines to 2 (one blank line)
    text = re.sub(r"\n{3,}", "\n\n", text)

    # Strip trailing whitespace on each line
    text = "\n".join(line.rstrip() for line in text.split("\n"))

    return text.strip()


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def clean_all_pages(pages_raw_text: List[Tuple[int, str]]) -> List[Tuple[int, str]]:
    """Clean all pages.

    Parameters
    ----------
    pages_raw_text : list of (pdf_page, raw_text) tuples

    Returns
    -------
    list of (pdf_page, cleaned_text) tuples
    """
    # Step 1: detect repeated noise patterns
    noise = detect_noise_patterns([text for _, text in pages_raw_text])

    # Step 2: clean each page
    results: List[Tuple[int, str]] = []
    for pdf_page, raw_text in pages_raw_text:
        cleaned = clean_page_text(raw_text, noise)
        cleaned = normalize_text(cleaned)
        results.append((pdf_page, cleaned))

    logger.info("Cleaned %d pages", len(results))
    return results

