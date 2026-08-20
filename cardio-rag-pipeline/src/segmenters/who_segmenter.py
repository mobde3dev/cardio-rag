"""
Section parser for the WHO03 hypertension guideline.

Uses continuous text stream matching with regex patterns for ground-truth
section boundaries, with TOC fallback for metadata.

Assigns every text block to its containing section/subsection
so that downstream chunking respects the document hierarchy.
"""

import re
import logging
from dataclasses import dataclass, field
from typing import List, Optional, Tuple, Dict

from src.parsers.who_parser import TocEntry, PageData

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass
class Section:
    """A section or subsection of the guideline."""
    number: str          # e.g. "3", "3.4", "4.1"
    title: str           # e.g. "Drug classes to be used as first-line agents"
    level: int           # 1 = chapter, 2 = section, 3 = subsection
    page_start: int      # 1-based PDF page where section begins
    page_end: int = 0    # 1-based PDF page where section ends
    full_heading: str = ""  # e.g. "3.4 Drug classes to be used as first-line agents"


@dataclass
class SectionBlock:
    """A block of text assigned to a specific section."""
    section: Section
    text: str
    pdf_page_start: int
    pdf_page_end: int
    page_label_start: Optional[str] = None
    page_label_end: Optional[str] = None


# ---------------------------------------------------------------------------
# Canonical section definitions for WHO03
# ---------------------------------------------------------------------------

SECTION_DEFS = [
    ("exec", "Executive summary", r"^Executive\s+summary\s*$", 1),
    ("1", "Introduction", r"^1\s+Introduction\s*$", 1),
    ("2", "Method for developing the guideline", r"^2\s+Method\s+for\s+developing\s+the\s+guideline\s*$", 1),
    ("2.1", "Guideline contributors", r"^2\.1\s+Guideline\s+contributors\s*$", 2),
    ("2.2", "Analytical framework and PICOs", r"^2\.2\s+Analytical\s+framework\s+and\s+PICOs\s*$", 2),
    ("2.3", "Outcome importance rating", r"^2\.3\s+Outcome\s+importance\s+rating\s*$", 2),
    ("2.4", "Reviews of evidence", r"^2\.4\s+Reviews\s+of\s+evidence\s*$", 2),
    ("2.5", "Certainty of evidence and strength of recommendations", r"^2\.5\s+Certainty\s+of\s+evidence\s+and\s+strength\s+of\s+recommendations\s*$", 2),
    ("2.6", "Deciding upon recommendations", r"^2\.6\s+Deciding\s+upon\s+recommendations\s*$", 2),
    ("2.7", "Funding", r"^2\.7\s+Funding\s*$", 2),
    ("3", "Recommendations", r"^3\s+Recommendations\s*$", 1),
    ("3.1", "Blood pressure threshold for initiation of pharmacological treatment", r"^3\.1\s+Blood\s+pressure\s+threshold\s+for\s+initiation\s+of\s+pharmacological\s+treatment\s*$", 2),
    ("3.2", "Laboratory testing before and during pharmacological treatment", r"^3\.2\s+Laboratory\s+testing\s+before\s+and\s+during\s+pharmacological\s+treatment\s*$", 2),
    ("3.3", "Cardiovascular disease risk assessment as guide to initiation of antihypertensive medications", r"^3\.3\s+Cardiovascular\s+disease\s+risk\s+assessment\s+as\s+guide\s+to\s+initiation\s+of\s+antihypertensive\s+medications\s*$", 2),
    ("3.4", "Drug classes to be used as first-line agents", r"^3\.4\s+Drug\s+classes\s+to\s+be\s+used\s+as\s+first[- ]line\s+agents\s*$", 2),
    ("3.5", "Combination therapy", r"^3\.5\s+Combination\s+therapy\s*$", 2),
    ("3.6", "Target blood pressure", r"^3\.6\s+Target\s+blood\s+pressure\s*$", 2),
    ("3.7", "Frequency of re-assessment", r"^3\.7\s+Frequency\s+of\s+re[- ]assessment\s*$", 2),
    ("3.8", "Administration of treatment by nonphysician professionals", r"^3\.8\s+Administration\s+of\s+treatment\s+by\s+nonphysician\s+professionals\s*$", 2),
    ("4", "Special settings", r"^4\s+Special\s+settings\s*$", 1),
    ("4.1", "Hypertension in disaster, humanitarian and emergency settings", r"^4\.1\s+Hypertension\s+in\s+disaster,\s+humanitarian\s+and\s+emergency\s+settings\s*$", 2),
    ("4.2", "COVID-19 and hypertension", r"^4\.2\s+COVID[- ]19\s+and\s+hypertension\s*$", 2),
    ("4.3", "Pregnancy and hypertension", r"^4\.3\s+Pregnancy\s+and\s+hypertension\s*$", 2),
    ("5", "Publication, implementation, evaluation and research gaps", r"^5\s+Publication,\s+implementation,\s+evaluation\s+and\s+research\s+gaps\s*$", 1),
    ("5.1", "Publication", r"^5\.1\s+Publication\s*$", 2),
    ("5.2", "Implementation and dissemination", r"^5\.2\s+Implementation\s+and\s+dissemination\s*$", 2),
    ("5.3", "Evaluation", r"^5\.3\s+Evaluation\s*$", 2),
    ("5.4", "Future updating of the guideline", r"^5\.4\s+Future\s+updating\s+of\s+the\s+guideline\s*$", 2),
    ("5.5", "Research gaps", r"^5\.5\s+Research\s+gaps\s*$", 2),
    ("6", "Implementation tools", r"^6\s+Implementation\s+tools\s*$", 1),
    ("6.1", "Guideline recommendations", r"^6\.1\s+Guideline\s+recommendations\s*$", 2),
    ("6.2", "Drug- and dose-specific protocols", r"^6\.2\s+Drug[- ]\s*and\s+dose[- ]specific\s+protocols\s*$", 2),
    ("ref", "References", r"^References\s*$", 1),
    ("annex1", "Annex 1: List of contributors", r"^Annex\s+1[.:]?\s*List\s+of\s+contributors\s*$", 1),
    ("annex2", "Annex 2. Managing declarations of interest", r"^Annex\s+2[.:]?\s*Managing\s+declarations\s+of\s+interest", 1),
    ("annex3", "Annex 3: Treatment outcomes relevant to hypertension", r"^Annex\s+3[.:]?\s*Treatment\s+outcomes\s+relevant\s+to\s+hypertension\s*$", 1),
    ("annex4", "Annex 4: PICO questions", r"^Annex\s+4[.:]?\s*PICO\s+questions\s*$", 1),
]

EXPECTED_SECTIONS = {
    "1": "Introduction",
    "2": "Method for developing the guideline",
    "3": "Recommendations",
    "3.1": "Blood pressure threshold for initiation of pharmacological treatment",
    "3.2": "Laboratory testing before and during pharmacological treatment",
    "3.3": "Cardiovascular disease risk assessment as guide to initiation of antihypertensive medications",
    "3.4": "Drug classes to be used as first-line agents",
    "3.5": "Combination therapy",
    "3.6": "Target blood pressure",
    "3.7": "Frequency of reassessment",
    "3.8": "Administration of treatment by nonphysician professionals",
    "4": "Special settings",
    "4.1": "Hypertension in disaster, humanitarian and emergency settings",
    "4.2": "COVID-19 and hypertension",
    "4.3": "Pregnancy and hypertension",
    "5": "Publication, implementation, evaluation and research gaps",
    "6": "Implementation tools",
    "6.1": "Guideline recommendations",
    "6.2": "Drug- and dose-specific protocols",
}

# Administrative sections that should be excluded or low priority
ADMIN_SECTIONS = {
    "acknowledgements", "contributors", "declarations of interest",
    "abbreviations", "references", "annex 1", "annex 2",
}

# Annex priority
ANNEX_PRIORITY = {
    "annex 1": 5,  # contributors — exclude
    "annex 2": 5,  # declarations of interest — exclude
    "annex 3": 2,  # treatment outcomes — include
    "annex 4": 1,  # PICO questions — include
}


# ---------------------------------------------------------------------------
# Section detection & segmentation
# ---------------------------------------------------------------------------

def build_sections(
    toc_entries: List[TocEntry],
    pages: List[Tuple[int, str]],
    page_data: Optional[List[PageData]] = None,
) -> List[Section]:
    """Build canonical Section list from the document."""
    sections: List[Section] = []

    # Map TOC pages for quick lookup
    toc_pages = {e.title.strip().lower(): e.page for e in toc_entries}

    for sec_id, title, _, level in SECTION_DEFS:
        num = "" if sec_id in ("exec", "ref", "annex1", "annex2", "annex3", "annex4") else sec_id
        # Estimate page from TOC if available
        p_start = toc_pages.get(title.lower(), 1)
        full_h = f"{num} {title}".strip() if num else title
        sections.append(Section(
            number=num,
            title=title,
            level=level,
            page_start=p_start,
            full_heading=full_h,
        ))

    return sections


def assign_pages_to_sections(
    pages: List[Tuple[int, str, Optional[str]]],  # (pdf_page, cleaned_text, page_label)
    sections: List[Section],
    total_pdf_pages: int = 0,
) -> List[SectionBlock]:
    """Segment document text into SectionBlocks using exact section boundary detection.

    Concatenates cleaned pages with character-to-page tracking and slices
    at detected section headings.
    """
    page_labels = {p[0]: p[2] for p in pages}

    # Build continuous text stream starting from page 7 (main content)
    full_text = ""
    char_to_page: List[int] = []

    for pdf_page, text, _ in pages:
        if pdf_page < 7:  # Front matter / TOC pages
            continue
        for ch in text + "\n\n":
            full_text += ch
            char_to_page.append(pdf_page)

    if not full_text:
        return []

    # Find position of each section in stream
    found_sections: List[Tuple[int, str, str, int]] = []  # (pos, sec_id, title, level)
    for sec_id, title, pat_str, level in SECTION_DEFS:
        pat = re.compile(pat_str, re.IGNORECASE | re.MULTILINE)
        m = pat.search(full_text)
        if m:
            found_sections.append((m.start(), sec_id, title, level))

    found_sections.sort(key=lambda x: x[0])

    blocks: List[SectionBlock] = []
    for i, (pos, sec_id, title, level) in enumerate(found_sections):
        end_pos = found_sections[i + 1][0] if i + 1 < len(found_sections) else len(full_text)
        block_text = full_text[pos:end_pos].strip()

        p_start = char_to_page[pos] if pos < len(char_to_page) else total_pdf_pages
        p_end = char_to_page[end_pos - 1] if end_pos - 1 < len(char_to_page) else p_start

        num = "" if sec_id in ("exec", "ref", "annex1", "annex2", "annex3", "annex4") else sec_id
        sec = Section(
            number=num,
            title=title,
            level=level,
            page_start=p_start,
            page_end=p_end,
            full_heading=f"{num} {title}".strip() if num else title,
        )

        blocks.append(SectionBlock(
            section=sec,
            text=block_text,
            pdf_page_start=p_start,
            pdf_page_end=p_end,
            page_label_start=page_labels.get(p_start),
            page_label_end=page_labels.get(p_end),
        ))

    logger.info("Created %d exact section blocks", len(blocks))
    return blocks


def is_administrative_section(section: Section) -> bool:
    """Check if a section is administrative / should be excluded."""
    title_lower = section.title.lower()
    number_lower = section.number.lower()

    for admin in ADMIN_SECTIONS:
        if admin in title_lower or admin in number_lower:
            return True

    return False


def get_annex_priority(section: Section) -> Optional[int]:
    """Get the clinical priority for an annex section, or None if not an annex."""
    for key, priority in ANNEX_PRIORITY.items():
        if key in section.number.lower() or key in section.title.lower():
            return priority
    return None
