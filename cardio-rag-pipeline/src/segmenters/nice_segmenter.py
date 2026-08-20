"""
Section parser for the NICE3 (NG238) cardiovascular guideline.

Detects:
  - Major NICE sections 1.1 through 1.12
  - Lower-level subheadings (e.g., Cardioprotective diet, Physical activity)
  - Committee rationale sections ("Why the committee made these recommendations")
  - Implementation impact sections ("How the recommendations might affect practice")
  - Terms, Research Recommendations, Context, Update Information

Assigns every text block to its containing section/subsection.
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
class NiceSection:
    """A section or subsection of the NICE guideline."""
    number: str           # e.g. "1.1", "1.7", "terms", "context"
    title: str            # e.g. "Identifying and assessing cardiovascular disease risk..."
    level: int            # 1 = major section, 2 = subsection, 3 = sub-subsection
    page_start: int       # 1-based PDF page where section begins
    page_end: int = 0     # 1-based PDF page where section ends
    full_heading: str = ""  # e.g. "1.7 Lipid-lowering treatment for secondary prevention..."
    parent_section: Optional[str] = None  # parent section number


@dataclass
class NiceSectionBlock:
    """A block of text assigned to a specific section."""
    section: NiceSection
    text: str
    pdf_page_start: int
    pdf_page_end: int
    page_label_start: Optional[str] = None
    page_label_end: Optional[str] = None


# ---------------------------------------------------------------------------
# Canonical NICE3 section definitions
# ---------------------------------------------------------------------------

# (section_id, title, regex_pattern, level)
NICE_SECTION_DEFS = [
    # Recommendations header
    ("recommendations", "Recommendations", r"^\s*Recommendations\s*$", 1),

    # Major sections 1.1 through 1.12
    ("1.1", "Identifying and assessing cardiovascular disease risk for people without established cardiovascular disease",
     r"^\s*1\.1\s+Identifying\s+and\s+assessing", 1),
    ("1.2", "Aspirin for primary prevention of cardiovascular disease",
     r"^\s*1\.2\s+Aspirin\s+for\s+primary", 1),
    ("1.3", "Lifestyle changes for the primary and secondary prevention of cardiovascular disease",
     r"^\s*1\.3\s+Lifestyle\s+changes", 1),
    ("1.4", "Initial lipid measurement and referral for specialist review",
     r"^\s*1\.4\s+Initial\s+lipid\s+measurement", 1),
    ("1.5", "Discussions and assessment before starting statins",
     r"^\s*1\.5\s+Discussions?\s+and\s+assessment", 1),
    ("1.6", "Lipid-lowering treatment for primary prevention of cardiovascular disease",
     r"^\s*1\.6\s+Lipid[- ]lowering\s+treatment\s+for\s+primary", 1),
    ("1.7", "Lipid-lowering treatment for secondary prevention of cardiovascular disease",
     r"^\s*1\.7\s+Lipid[- ]lowering\s+treatment\s+for\s+secondary", 1),
    ("1.8", "Statins for primary and secondary prevention of cardiovascular disease in people with chronic kidney disease",
     r"^\s*1\.8\s+Statins?\s+for\s+primary\s+and\s+secondary", 1),
    ("1.9", "Optimising statin treatment",
     r"^\s*1\.9\s+Optimising\s+statin\s+treatment", 1),
    ("1.10", "Treatment if statins are contraindicated or not tolerated",
     r"^\s*1\.10\s+Treatment\s+if\s+statins?", 1),
    ("1.11", "Assessing response to treatment",
     r"^\s*1\.11\s+Assessing\s+response\s+to\s+treatment", 1),
    ("1.12", "Lipid-lowering treatments that should not be used or not used routinely",
     r"^\s*1\.12\s+Lipid[- ]lowering\s+treatments?", 1),

    # Non-numbered sections
    ("terms", "Terms used in this guideline",
     r"^\s*Terms?\s+used\s+in\s+this\s+guideline", 1),
    ("research", "Recommendations for research",
     r"^\s*Recommendations?\s+for\s+research", 1),
    ("context", "Context",
     r"^\s*Context\s*$", 1),
    ("finding_more", "Finding more information and committee details",
     r"^\s*Finding\s+more\s+information", 1),
    ("update_info", "Update information",
     r"^\s*Update\s+information", 1),
]

# Subheadings within major sections (level 2)
NICE_SUBHEADING_DEFS = [
    # Section 1.1 subheadings
    ("Full formal risk assessment", r"Full\s+formal\s+risk\s+assessment"),
    ("Communication about risk assessment, lifestyle changes and treatment",
     r"Communication\s+about\s+risk\s+assessment"),

    # Section 1.3 subheadings
    ("Cardioprotective diet", r"Cardioprotective\s+diet"),
    ("Physical activity", r"Physical\s+activity"),
    ("Weight management", r"Weight\s+management"),
    ("Alcohol consumption", r"Alcohol\s+consumption"),
    ("Smoking cessation", r"Smoking\s+cessation"),
    ("Plant stanols and sterols", r"Plant\s+stanols\s+and\s+sterols"),

    # Section 1.5 subheadings
    ("Discuss risks and benefits of statins", r"Discuss\s+risks?\s+and\s+benefits?\s+of\s+statins?"),
    ("Perform baseline blood tests and clinical assessment",
     r"Perform\s+baseline\s+blood\s+tests?\s+and\s+clinical\s+assessment"),
    ("Statins and pregnancy", r"Statins?\s+and\s+pregnancy"),

    # Section 1.6 subheadings
    ("Lipid target for people taking statins", r"Lipid\s+target\s+for\s+people\s+taking\s+statins"),

    # Section 1.7 subheadings
    ("Lipid target for people taking lipid-lowering treatments",
     r"Lipid\s+target\s+for\s+people\s+taking\s+lipid[- ]lowering\s+treatments?"),
    ("Initial treatment", r"Initial\s+treatment"),
    ("Escalating treatment for people on statins",
     r"Escalating\s+treatment\s+for\s+people\s+on\s+statins?"),

    # Section 1.9 subheadings
    ("Optimising lifestyle changes", r"Optimising\s+lifestyle\s+changes"),
    ("Statin treatment for people with and without type 2 diabetes",
     r"Statin\s+treatment\s+for\s+people\s+with\s+and\s+without\s+type\s+2\s+diabetes"),
    ("Statin treatment for people with type 1 diabetes",
     r"Statin\s+treatment\s+for\s+people\s+with\s+type\s+1\s+diabetes"),

    # Section 1.10 subheadings
    ("Primary prevention of cardiovascular disease",
     r"Primary\s+prevention\s+of\s+cardiovascular\s+disease"),
    ("Secondary prevention of cardiovascular disease",
     r"Secondary\s+prevention\s+of\s+cardiovascular\s+disease"),

    # Section 1.11 subheadings
    ("When to repeat blood tests", r"When\s+to\s+repeat\s+blood\s+tests?"),
    ("When to measure creatine kinase", r"When\s+to\s+measure\s+creatine\s+kinase"),
    ("Annual medication review", r"Annual\s+medication\s+review"),

    # Committee rationale (appears in many sections)
    ("Why the committee made these recommendations",
     r"Why\s+the\s+committee\s+made\s+(?:the|these)?\s*recommendations?"),

    # Implementation impact
    ("How the recommendations might affect practice",
     r"How\s+the\s+recommendations?\s+might\s+affect\s+(?:practice|services|the\s+NHS)"),
]


# ---------------------------------------------------------------------------
# Topic mapping (Section → clinical topic)
# ---------------------------------------------------------------------------

NICE_TOPIC_MAP: Dict[str, Dict[str, Optional[str]]] = {
    "1.1": {"topic": "cardiovascular_risk_assessment", "subtopic": "primary_prevention"},
    "1.2": {"topic": "antiplatelet_therapy", "subtopic": "aspirin_primary_prevention"},
    "1.3": {"topic": "lifestyle", "subtopic": None},
    "1.4": {"topic": "lipid_assessment", "subtopic": None},
    "1.5": {"topic": "statin_pre_treatment_assessment", "subtopic": None},
    "1.6": {"topic": "lipid_lowering_treatment", "subtopic": "primary_prevention"},
    "1.7": {"topic": "lipid_lowering_treatment", "subtopic": "secondary_prevention"},
    "1.8": {"topic": "lipid_lowering_treatment", "subtopic": "chronic_kidney_disease"},
    "1.9": {"topic": "statin_optimization", "subtopic": None},
    "1.10": {"topic": "statin_intolerance", "subtopic": None},
    "1.11": {"topic": "treatment_monitoring", "subtopic": None},
    "1.12": {"topic": "treatments_not_recommended", "subtopic": None},
    "terms": {"topic": "definitions", "subtopic": None},
    "research": {"topic": "research_recommendations", "subtopic": None},
    "context": {"topic": "context", "subtopic": None},
    "update_info": {"topic": "update_information", "subtopic": None},
}

# Subtopic refinements based on subheadings
NICE_SUBTOPIC_MAP: Dict[str, str] = {
    "Cardioprotective diet": "cardioprotective_diet",
    "Physical activity": "physical_activity",
    "Weight management": "weight_management",
    "Alcohol consumption": "alcohol",
    "Smoking cessation": "smoking_cessation",
    "Plant stanols and sterols": "plant_stanols_sterols",
    "Full formal risk assessment": "formal_risk_assessment",
    "Communication about risk assessment, lifestyle changes and treatment": "communication",
    "Discuss risks and benefits of statins": "shared_decision_making",
    "Perform baseline blood tests and clinical assessment": "baseline_testing",
    "Statins and pregnancy": "pregnancy",
    "Lipid target for people taking statins": "primary_prevention_lipid_target",
    "Lipid target for people taking lipid-lowering treatments": "secondary_prevention_lipid_target",
    "Initial treatment": "initial_treatment",
    "Escalating treatment for people on statins": "escalating_treatment",
    "Optimising lifestyle changes": "lifestyle_optimisation",
    "Statin treatment for people with and without type 2 diabetes": "type_2_diabetes",
    "Statin treatment for people with type 1 diabetes": "type_1_diabetes",
    "Primary prevention of cardiovascular disease": "primary_prevention",
    "Secondary prevention of cardiovascular disease": "secondary_prevention",
    "When to repeat blood tests": "blood_test_timing",
    "When to measure creatine kinase": "creatine_kinase",
    "Annual medication review": "annual_review",
}

# Prevention type mapping
NICE_PREVENTION_MAP: Dict[str, Optional[str]] = {
    "1.1": "primary",
    "1.2": "primary",
    "1.3": "primary_and_secondary",
    "1.4": None,
    "1.5": None,
    "1.6": "primary",
    "1.7": "secondary",
    "1.8": "primary_and_secondary",
    "1.9": "primary_and_secondary",
    "1.10": None,
    "1.11": None,
    "1.12": None,
}


# ---------------------------------------------------------------------------
# Section detection & segmentation
# ---------------------------------------------------------------------------

def build_nice_sections(
    pages: List[Tuple[int, str]],
) -> List[NiceSection]:
    """Build canonical NiceSection list from document text.

    Scans all pages to find section headings by regex pattern matching.
    """
    sections: List[NiceSection] = []

    # Concatenate text starting from main recommendations (page 5)
    full_text = ""
    char_to_page: List[int] = []
    for pdf_page, text in pages:
        if pdf_page < 5:
            continue
        for ch in text + "\n\n":
            full_text += ch
            char_to_page.append(pdf_page)

    if not full_text:
        return sections

    # Find major sections
    for sec_id, title, pat_str, level in NICE_SECTION_DEFS:
        pat = re.compile(pat_str, re.IGNORECASE | re.MULTILINE)
        m = pat.search(full_text)
        if m:
            pos = m.start()
            page = char_to_page[pos] if pos < len(char_to_page) else 5
            full_heading = f"{sec_id} {title}" if sec_id not in (
                "recommendations", "terms", "research", "context",
                "finding_more", "update_info"
            ) else title
            sections.append(NiceSection(
                number=sec_id,
                title=title,
                level=level,
                page_start=page,
                full_heading=full_heading,
            ))
            logger.debug("Found section %s: %s (page %d)", sec_id, title, page)
        else:
            logger.warning("Section not found: %s %s", sec_id, title)

    # Sort by position in document
    sections.sort(key=lambda s: s.page_start)

    # Set page_end for each section
    for i, sec in enumerate(sections):
        if i + 1 < len(sections):
            sec.page_end = sections[i + 1].page_start
        else:
            sec.page_end = max(char_to_page) if char_to_page else sec.page_start

    logger.info("Built %d NICE sections", len(sections))
    return sections


def assign_pages_to_nice_sections(
    pages: List[Tuple[int, str, Optional[str]]],  # (pdf_page, cleaned_text, page_label)
    total_pdf_pages: int = 0,
) -> List[NiceSectionBlock]:
    """Segment document text into NiceSectionBlocks.

    Concatenates pages into a continuous text stream (skipping front matter/TOC),
    finds section boundaries by regex, and slices at detected headings.
    """
    page_labels = {p[0]: p[2] for p in pages}

    # Build continuous text stream starting from page 5 (main content)
    full_text = ""
    char_to_page: List[int] = []

    for pdf_page, text, _ in pages:
        if pdf_page < 5:
            continue
        for ch in text + "\n\n":
            full_text += ch
            char_to_page.append(pdf_page)

    if not full_text:
        return []

    # Find positions of each section heading
    found_sections: List[Tuple[int, str, str, int]] = []  # (pos, sec_id, title, level)
    for sec_id, title, pat_str, level in NICE_SECTION_DEFS:
        pat = re.compile(pat_str, re.IGNORECASE | re.MULTILINE)
        m = pat.search(full_text)
        if m:
            found_sections.append((m.start(), sec_id, title, level))

    found_sections.sort(key=lambda x: x[0])

    blocks: List[NiceSectionBlock] = []
    for i, (pos, sec_id, title, level) in enumerate(found_sections):
        end_pos = found_sections[i + 1][0] if i + 1 < len(found_sections) else len(full_text)
        block_text = full_text[pos:end_pos].strip()

        p_start = char_to_page[pos] if pos < len(char_to_page) else total_pdf_pages
        p_end = char_to_page[min(end_pos - 1, len(char_to_page) - 1)] if end_pos > 0 else p_start

        full_heading = f"{sec_id} {title}" if sec_id not in (
            "recommendations", "terms", "research", "context",
            "finding_more", "update_info"
        ) else title

        sec = NiceSection(
            number=sec_id,
            title=title,
            level=level,
            page_start=p_start,
            page_end=p_end,
            full_heading=full_heading,
        )

        blocks.append(NiceSectionBlock(
            section=sec,
            text=block_text,
            pdf_page_start=p_start,
            pdf_page_end=p_end,
            page_label_start=page_labels.get(p_start),
            page_label_end=page_labels.get(p_end),
        ))

    logger.info("Created %d NICE section blocks", len(blocks))
    return blocks


def detect_subheadings(text: str) -> List[Tuple[int, str]]:
    """Detect subheadings within a section block.

    Returns list of (position, subheading_title).
    """
    found: List[Tuple[int, str]] = []
    for subheading_title, pat_str in NICE_SUBHEADING_DEFS:
        pat = re.compile(pat_str, re.IGNORECASE)
        m = pat.search(text)
        if m:
            found.append((m.start(), subheading_title))
    found.sort(key=lambda x: x[0])
    return found


def get_topic_for_section(section_number: str) -> Dict[str, Optional[str]]:
    """Get the clinical topic mapping for a section number."""
    return NICE_TOPIC_MAP.get(section_number, {"topic": None, "subtopic": None})


def get_subtopic_for_subheading(subheading: str) -> Optional[str]:
    """Get the subtopic for a subheading."""
    return NICE_SUBTOPIC_MAP.get(subheading)


def get_prevention_type(section_number: str) -> Optional[str]:
    """Get the prevention type for a section number."""
    return NICE_PREVENTION_MAP.get(section_number)


def is_committee_rationale(text: str) -> bool:
    """Check if text is a committee rationale section."""
    return bool(re.search(
        r"Why\s+the\s+committee\s+made\s+(?:the|these)?\s*recommendations?",
        text[:400],
        re.IGNORECASE,
    ))


def is_implementation_impact(text: str) -> bool:
    """Check if text is an implementation impact section."""
    return bool(re.search(
        r"How\s+the\s+recommendations?\s+might\s+affect\s+(?:practice|services|the\s+NHS)",
        text[:400],
        re.IGNORECASE,
    ))
