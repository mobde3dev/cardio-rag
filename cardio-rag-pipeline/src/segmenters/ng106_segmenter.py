"""
Section parser for the NICE NG106 guideline (Chronic heart failure in adults).

Detects:
  - Major NICE sections 1.1 through 1.12
  - Subheadings within each section (e.g. Symptoms, signs and investigations, Mildly reduced EF, etc.)
  - Committee rationale sections ("Why the committee made these recommendations")
  - Implementation impact sections ("How the recommendations might affect practice")
  - Terms, Research Recommendations, Context, Update Information
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
class Ng106Section:
    """A section or subsection of the NICE NG106 guideline."""
    number: str           # e.g. "1.1", "1.4", "terms", "rationale_and_impact"
    title: str
    level: int            # 1 = major, 2 = subsection
    page_start: int
    page_end: int = 0
    full_heading: str = ""
    parent_section: Optional[str] = None


@dataclass
class Ng106SectionBlock:
    """A block of text assigned to a specific section."""
    section: Ng106Section
    text: str
    pdf_page_start: int
    pdf_page_end: int
    page_label_start: Optional[str] = None
    page_label_end: Optional[str] = None


# ---------------------------------------------------------------------------
# Canonical NG106 section definitions
# ---------------------------------------------------------------------------

NG106_SECTION_DEFS = [
    ("recommendations", "Recommendations", r"^\s*Recommendations\s*$", 1),
    ("1.1", "Team working in the management of heart failure",
     r"^\s*1\.1\s+Team\s+working\s+in\s+the\s+management", 1),
    ("1.2", "Diagnosing heart failure",
     r"^\s*1\.2\s+Diagnosing\s+heart\s+failure", 1),
    ("1.3", "Giving information to people with heart failure",
     r"^\s*1\.3\s+Giving\s+information\s+to\s+people", 1),
    ("1.4", "Treating people with newly diagnosed and pre-existing heart failure with reduced ejection fraction",
     r"(?:^|\n)\s*1\.4\s+Treating\s+people", 1),
    ("1.5", "Treating people with newly diagnosed and pre-existing heart failure with mildly reduced or preserved ejection fraction",
     r"(?:^|\n)\s*1\.5\s+Treating\s+people", 1),
    ("1.6", "Treating heart failure in people with chronic kidney disease",
     r"(?:^|\n)\s*1\.6\s+Treating\s+heart\s+failure", 1),
    ("1.7", "Starting and monitoring medication use",
     r"(?:^|\n)\s*1\.7\s+Starting\s+and\s+monitoring", 1),
    ("1.8", "Clinical review",
     r"(?:^|\n)\s*1\.8\s+Clinical\s+review", 1),
    ("1.9", "Other treatments and advice for all types of heart failure",
     r"(?:^|\n)\s*1\.9\s+Other\s+treatments", 1),
    ("1.10", "Interventional procedures",
     r"(?:^|\n)\s*1\.10\s+Interventional", 1),
    ("1.11", "Cardiac rehabilitation",
     r"(?:^|\n)\s*1\.11\s+Cardiac\s+rehabilitation", 1),
    ("1.12", "Palliative care",
     r"(?:^|\n)\s*1\.12\s+Palliative", 1),
    ("terms", "Terms used in this guideline",
     r"^\s*Terms?\s+used\s+in\s+this\s+guideline", 1),
    ("research", "Recommendations for research",
     r"^\s*Recommendations?\s+for\s+research", 1),
    ("rationale_and_impact", "Rationale and impact",
     r"^\s*Rationale\s+and\s+impact\s*$", 1),
    ("context", "Context",
     r"^\s*Context\s*$", 1),
    ("finding_more", "Finding more information and committee details",
     r"^\s*Finding\s+more\s+information", 1),
    ("update_info", "Update information",
     r"^\s*Update\s+information", 1),
]

NG106_SUBHEADING_DEFS = [
    # 1.1
    ("Care after an acute event", r"Care\s+after\s+an\s+acute\s+event"),
    ("Writing a care plan", r"Writing\s+a\s+care\s+plan"),

    # 1.2
    ("Symptoms, signs and investigations", r"Symptoms,\s+signs\s+and\s+investigations"),
    ("Heart failure caused by valve disease", r"Heart\s+failure\s+caused\s+by\s+valve\s+disease"),
    ("Reviewing existing diagnoses", r"Reviewing\s+existing\s+diagnoses"),

    # 1.3
    ("First consultations for people with newly diagnosed heart failure",
     r"First\s+consultations?\s+for\s+people\s+with\s+newly\s+diagnosed"),

    # 1.4
    ("Treatment combinations", r"Treatment\s+combinations"),
    ("Alternative treatment combinations if certain medicines are not tolerated",
     r"Alternative\s+treatment\s+combinations"),
    ("Intravenous iron therapy", r"Intravenous\s+iron\s+therapy"),
    ("Specialist treatment", r"Specialist\s+treatment"),
    ("Ivabradine", r"^\s*Ivabradine\s*$"),
    ("Hydralazine in combination with nitrate", r"Hydralazine\s+in\s+combination\s+with\s+nitrate"),
    ("Digoxin", r"^\s*Digoxin\s*$"),
    ("Calcium-channel blockers", r"Calcium[- ]channel\s+blockers"),

    # 1.5
    ("Mildly reduced ejection fraction", r"Mildly\s+reduced\s+ejection\s+fraction"),
    ("Preserved ejection fraction", r"Preserved\s+ejection\s+fraction"),

    # 1.7
    ("Tailoring treatment", r"Tailoring\s+treatment"),
    ("ACE inhibitors, ARNIs, ARBs and MRAs", r"ACE\s+inhibitors,\s+ARNIs?,\s+ARBs?\s+and\s+MRAs?"),
    ("Beta-blockers", r"Beta[- ]blockers"),

    # 1.8
    ("People under 75 with normal renal function", r"People\s+under\s+75\s+with\s+normal\s+renal\s+function"),

    # 1.9
    ("Diuretics", r"^\s*Diuretics\s*$"),
    ("Amiodarone", r"^\s*Amiodarone\s*$"),
    ("Anticoagulants", r"^\s*Anticoagulants\s*$"),
    ("Vaccinations", r"^\s*Vaccinations\s*$"),
    ("Contraception and pregnancy", r"Contraception\s+and\s+pregnancy"),
    ("Salt and fluid restriction", r"Salt\s+and\s+fluid\s+restriction"),
    ("Air travel", r"Air\s+travel"),
    ("Driving", r"Driving"),

    # 1.10
    ("Coronary revascularisation", r"Coronary\s+revascularisation"),
    ("Cardiac transplantation", r"Cardiac\s+transplantation"),
    ("Implantable cardioverter defibrillators and cardiac resynchronisation therapy",
     r"Implantable\s+cardioverter\s+defibrillators"),

    # Committee rationale
    ("Why the committee made the recommendations",
     r"Why\s+the\s+committee\s+made\s+(?:the|these)?\s*recommendations?"),
    ("How the recommendations might affect practice",
     r"How\s+the\s+recommendations?\s+might\s+affect\s+(?:practice|services|the\s+NHS)"),
]

NG106_TOPIC_MAP: Dict[str, Dict[str, Optional[str]]] = {
    "1.1": {"topic": "multidisciplinary_team", "subtopic": "team_working"},
    "1.2": {"topic": "heart_failure_diagnosis", "subtopic": "investigations_and_biomarkers"},
    "1.3": {"topic": "patient_information", "subtopic": "consultations"},
    "1.4": {"topic": "pharmacological_treatment", "subtopic": "reduced_ejection_fraction_HFrEF"},
    "1.5": {"topic": "pharmacological_treatment", "subtopic": "preserved_and_mildly_reduced_EF"},
    "1.6": {"topic": "pharmacological_treatment", "subtopic": "chronic_kidney_disease"},
    "1.7": {"topic": "treatment_monitoring", "subtopic": "starting_and_monitoring"},
    "1.8": {"topic": "clinical_review", "subtopic": "routine_monitoring"},
    "1.9": {"topic": "lifestyle_and_other_treatments", "subtopic": None},
    "1.10": {"topic": "interventional_procedures", "subtopic": "devices_and_surgery"},
    "1.11": {"topic": "cardiac_rehabilitation", "subtopic": "exercise_programmes"},
    "1.12": {"topic": "palliative_care", "subtopic": "advanced_heart_failure"},
    "terms": {"topic": "definitions", "subtopic": None},
    "research": {"topic": "research_recommendations", "subtopic": None},
    "rationale_and_impact": {"topic": "committee_rationale", "subtopic": None},
    "context": {"topic": "context", "subtopic": None},
    "update_info": {"topic": "update_information", "subtopic": None},
}


def build_ng106_sections() -> List[Ng106Section]:
    """Build list of all canonical NG106 section objects."""
    sections = []
    for sec_id, title, _, level in NG106_SECTION_DEFS:
        sections.append(Ng106Section(
            number=sec_id,
            title=title,
            level=level,
            page_start=0,
            full_heading=f"{sec_id} {title}" if sec_id[0].isdigit() else title,
        ))
    return sections


def assign_pages_to_ng106_sections(
    pages: List[Tuple[int, str, Optional[str]]],
    total_pdf_pages: int = 39,
) -> List[Ng106SectionBlock]:
    """Assign page text blocks to NG106 sections based on headings."""
    compiled_secs = [
        (sec_id, title, re.compile(pat, re.MULTILINE | re.IGNORECASE), level)
        for sec_id, title, pat, level in NG106_SECTION_DEFS
    ]

    current_sec_id = "recommendations"
    current_sec_title = "Recommendations"
    blocks: List[Ng106SectionBlock] = []

    current_block_text: List[str] = []
    block_start_page = 6
    block_start_label = "6"

    for pdf_page, text, page_label in pages:
        if pdf_page < 5:
            continue

        detected_sec = None
        for sec_id, title, pattern, _ in compiled_secs:
            if pattern.search(text):
                detected_sec = (sec_id, title)
                break

        if detected_sec and detected_sec[0] != current_sec_id:
            if current_block_text:
                full_sec_text = "\n\n".join(current_block_text).strip()
                if full_sec_text:
                    sec_obj = Ng106Section(
                        number=current_sec_id,
                        title=current_sec_title,
                        level=1,
                        page_start=block_start_page,
                        page_end=pdf_page - 1,
                        full_heading=f"{current_sec_id} {current_sec_title}" if current_sec_id[0].isdigit() else current_sec_title,
                    )
                    blocks.append(Ng106SectionBlock(
                        section=sec_obj,
                        text=full_sec_text,
                        pdf_page_start=block_start_page,
                        pdf_page_end=pdf_page - 1,
                        page_label_start=block_start_label,
                        page_label_end=str(pdf_page - 1),
                    ))
            current_sec_id, current_sec_title = detected_sec
            current_block_text = [text]
            block_start_page = pdf_page
            block_start_label = page_label or str(pdf_page)
        else:
            current_block_text.append(text)

    if current_block_text:
        full_sec_text = "\n\n".join(current_block_text).strip()
        if full_sec_text:
            sec_obj = Ng106Section(
                number=current_sec_id,
                title=current_sec_title,
                level=1,
                page_start=block_start_page,
                page_end=total_pdf_pages,
                full_heading=f"{current_sec_id} {current_sec_title}" if current_sec_id[0].isdigit() else current_sec_title,
            )
            blocks.append(Ng106SectionBlock(
                section=sec_obj,
                text=full_sec_text,
                pdf_page_start=block_start_page,
                pdf_page_end=total_pdf_pages,
                page_label_start=block_start_label,
                page_label_end=str(total_pdf_pages),
            ))

    return blocks
