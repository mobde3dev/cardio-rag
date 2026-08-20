"""
Metadata extractor for the WHO03 hypertension guideline.

Handles:
  - Recommendation detection & strength/certainty extraction
  - Content-type classification
  - Clinical topic mapping from section numbers
  - Clinical entity extraction (Phase 1: regex-based)
  - Source metadata assembly
"""

import re
import logging
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any, Set

from src.segmenters.who_segmenter import Section

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Topic mapping
# ---------------------------------------------------------------------------

TOPIC_MAP: Dict[str, Dict[str, Optional[str]]] = {
    "3.1": {"topic": "treatment_initiation", "subtopic": None},
    "3.2": {"topic": "laboratory_testing", "subtopic": None},
    "3.3": {"topic": "cardiovascular_risk_assessment", "subtopic": None},
    "3.4": {"topic": "pharmacological_treatment", "subtopic": "first_line_agents"},
    "3.5": {"topic": "combination_therapy", "subtopic": None},
    "3.6": {"topic": "blood_pressure_target", "subtopic": None},
    "3.7": {"topic": "follow_up", "subtopic": "reassessment_frequency"},
    "3.8": {"topic": "healthcare_delivery", "subtopic": "nonphysician_management"},
    "4.1": {"topic": "special_setting", "subtopic": "disaster_or_humanitarian"},
    "4.2": {"topic": "special_setting", "subtopic": "covid_19"},
    "4.3": {"topic": "special_setting", "subtopic": "pregnancy"},
}

SPECIAL_SETTING_MAP: Dict[str, str] = {
    "4.1": "disaster_or_humanitarian",
    "4.2": "covid_19",
    "4.3": "pregnancy",
}


# ---------------------------------------------------------------------------
# Recommendation detection
# ---------------------------------------------------------------------------

@dataclass
class RecommendationMeta:
    """Parsed metadata from a recommendation block."""
    recommendation_text: str = ""
    recommendation_title: str = ""
    strength: Optional[str] = None       # "strong" or "conditional"
    evidence_certainty: Optional[str] = None  # "high", "moderate", "low", etc.
    recommendation_id: Optional[str] = None


# Patterns for recommendation detection
_REC_TITLE_RE = re.compile(
    r"RECOMMENDATION\s+(?:ON\s+|FOR\s+)?(.+?)(?:\n|$)",
    re.IGNORECASE,
)

_REC_TEXT_RE = re.compile(
    r"((?:(?:For\s+adults[^\n,.]*|When\s+starting[^\n,.]*),\s*)?WHO\s+(?:recommends|suggests)\b.+?)(?=\n\s*\n|\n\s*(?:Strong|Conditional)\s+recommendation|$)",
    re.IGNORECASE | re.DOTALL,
)

_STRENGTH_RE = re.compile(
    r"(Strong|Conditional)\s+recommendation",
    re.IGNORECASE,
)

_CERTAINTY_RE = re.compile(
    r"((?:very\s+)?(?:high|moderate|low)(?:\s*[-–to]+\s*(?:high|moderate|low))?)"
    r"\s*[-–]?\s*certainty\s+evidence",
    re.IGNORECASE,
)

_CERTAINTY_ALT_RE = re.compile(
    r"certainty\s+(?:of\s+)?(?:the\s+)?evidence\s*[:=]?\s*"
    r"((?:very\s+)?(?:high|moderate|low)(?:\s*[-–to]+\s*(?:high|moderate|low))?)",
    re.IGNORECASE,
)

# Robust full recommendation statement pattern
REC_STATEMENT_RE = re.compile(
    r"((?:(?:[0-9]+\.\s*)?RECOMMENDATION\s+(?:ON|FOR)[^\n]*\n+)?(?:(?:For\s+adults[^\n,.]*|When\s+starting[^\n,.]*),\s*)?WHO\s+(?:recommends|suggests)\b.+?\.\s*(?:\n\s*|\s*)(?:Strong|Conditional)\s+recommendation,\s*[^.\n]*?evidence)",
    re.IGNORECASE | re.DOTALL,
)


def detect_recommendation(text: str) -> Optional[RecommendationMeta]:
    """Detect and parse a WHO recommendation block from text.

    Returns None if no recommendation is found.
    """
    # Look for recommendation title
    title_match = _REC_TITLE_RE.search(text)
    rec_text_match = _REC_TEXT_RE.search(text)

    if not title_match and not rec_text_match:
        return None

    meta = RecommendationMeta()

    if title_match:
        meta.recommendation_title = title_match.group(1).strip()

    if rec_text_match:
        meta.recommendation_text = rec_text_match.group(1).strip()

    # Extract strength
    strength_match = _STRENGTH_RE.search(text)
    if strength_match:
        raw = strength_match.group(1).strip().lower()
        meta.strength = raw  # "strong" or "conditional"

    # Extract evidence certainty
    cert_match = _CERTAINTY_RE.search(text)
    if not cert_match:
        cert_match = _CERTAINTY_ALT_RE.search(text)
    if cert_match:
        raw = cert_match.group(1).strip().lower()
        # Normalize
        raw = re.sub(r"\s+", " ", raw)
        raw = raw.replace("–", "-").replace(" to ", "-")
        meta.evidence_certainty = raw

    return meta


def extract_recommendation_statements(text: str) -> List[Tuple[str, RecommendationMeta]]:
    """Extract individual self-contained recommendation statements from text.

    Returns a list of (statement_full_text, RecommendationMeta) tuples.
    """
    results: List[Tuple[str, RecommendationMeta]] = []

    # Find common section recommendation title if present
    common_title = ""
    tm = _REC_TITLE_RE.search(text)
    if tm:
        common_title = tm.group(1).strip()

    for m in REC_STATEMENT_RE.finditer(text):
        stmt_text = m.group(0).strip()
        rec_meta = detect_recommendation(stmt_text)
        if rec_meta:
            if not rec_meta.recommendation_title and common_title:
                rec_meta.recommendation_title = common_title
            results.append((stmt_text, rec_meta))

    return results


def detect_all_recommendations(text: str) -> List[RecommendationMeta]:
    """Detect multiple recommendations within a text block."""
    stmts = extract_recommendation_statements(text)
    if stmts:
        return [meta for _, meta in stmts]

    rec = detect_recommendation(text)
    return [rec] if rec else []


# ---------------------------------------------------------------------------
# Content type classification
# ---------------------------------------------------------------------------

# Ordered by specificity — first match wins
_CONTENT_TYPE_PATTERNS = [
    ("recommendation", [
        re.compile(r"RECOMMENDATION\s+ON", re.IGNORECASE),
        re.compile(r"WHO\s+(?:recommends|suggests)\b", re.IGNORECASE),
    ]),
    ("implementation_remark", [
        re.compile(r"implementation\s+remark", re.IGNORECASE),
        re.compile(r"remarks?\s+(?:for|on)\s+implementation", re.IGNORECASE),
    ]),
    ("evidence_to_decision", [
        re.compile(r"evidence[-\s]+to[-\s]+decision", re.IGNORECASE),
    ]),
    ("evidence_rationale", [
        re.compile(r"evidence\s+(?:and|&)\s+rationale", re.IGNORECASE),
        re.compile(r"(?:summary\s+of\s+)?evidence", re.IGNORECASE),
        re.compile(r"rationale", re.IGNORECASE),
    ]),
    ("algorithm", [
        re.compile(r"algorithm\s+\d", re.IGNORECASE),
    ]),
    ("table", [
        re.compile(r"^table\s+\d", re.IGNORECASE | re.MULTILINE),
    ]),
    ("definition", [
        re.compile(r"definition", re.IGNORECASE),
    ]),
    ("clinical_threshold", [
        re.compile(r"threshold", re.IGNORECASE),
        re.compile(r"target\s+(?:blood\s+)?pressure", re.IGNORECASE),
    ]),
    ("drug_guidance", [
        re.compile(r"(?:drug|medication)\s+(?:class|treatment|protocol)", re.IGNORECASE),
        re.compile(r"first[- ]line\s+(?:agent|drug|treatment)", re.IGNORECASE),
        re.compile(r"dose[- ]specific\s+protocol", re.IGNORECASE),
    ]),
    ("laboratory_guidance", [
        re.compile(r"laboratory\s+test", re.IGNORECASE),
    ]),
    ("risk_assessment", [
        re.compile(r"(?:cardiovascular|CVD)\s+risk", re.IGNORECASE),
        re.compile(r"risk\s+assessment", re.IGNORECASE),
    ]),
    ("follow_up", [
        re.compile(r"follow[- ]up", re.IGNORECASE),
        re.compile(r"reassessment", re.IGNORECASE),
    ]),
    ("special_setting", [
        re.compile(r"disaster|humanitarian|emergency", re.IGNORECASE),
        re.compile(r"COVID[- ]?19", re.IGNORECASE),
        re.compile(r"pregnancy", re.IGNORECASE),
    ]),
    ("research_methodology", [
        re.compile(r"PICO", re.IGNORECASE),
        re.compile(r"GRADE", re.IGNORECASE),
        re.compile(r"systematic\s+review", re.IGNORECASE),
        re.compile(r"guideline\s+development", re.IGNORECASE),
        re.compile(r"method(?:ology)?", re.IGNORECASE),
    ]),
]


def classify_content_type(
    text: str,
    section: Optional[Section] = None,
) -> str:
    """Classify a text block into one of the defined content types.

    Uses both text pattern matching and section context.
    """
    text_lower = text[:2000].lower()  # Only scan the first ~2000 chars

    for content_type, patterns in _CONTENT_TYPE_PATTERNS:
        for pat in patterns:
            if pat.search(text_lower):
                return content_type

    # Fallback based on section number
    if section and section.number:
        num = section.number
        if num.startswith("2"):
            return "research_methodology"
        if num.startswith("3"):
            return "background"
        if num.startswith("4"):
            return "special_setting"
        if num.startswith("6"):
            return "drug_guidance"

    return "other"


# ---------------------------------------------------------------------------
# Clinical entity extraction (Phase 1: regex)
# ---------------------------------------------------------------------------

@dataclass
class ClinicalEntities:
    """Extracted clinical entities from text."""
    population: Optional[str] = None
    condition: Optional[str] = None
    comorbidities: List[str] = field(default_factory=list)
    drug_classes: List[str] = field(default_factory=list)
    drug_names: List[str] = field(default_factory=list)
    bp_thresholds: List[str] = field(default_factory=list)
    target_bp: Optional[str] = None
    age_groups: List[str] = field(default_factory=list)
    special_population: Optional[str] = None
    entity_extraction_method: str = "regex_v1"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "population": self.population,
            "condition": self.condition,
            "comorbidity": self.comorbidities[0] if len(self.comorbidities) == 1
                           else ", ".join(self.comorbidities) if self.comorbidities else None,
            "drug_class": self.drug_classes if self.drug_classes else None,
            "drug_name": self.drug_names if self.drug_names else None,
            "bp_threshold": self.bp_thresholds[0] if len(self.bp_thresholds) == 1
                            else ", ".join(self.bp_thresholds) if self.bp_thresholds else None,
            "target_bp": self.target_bp,
            "age_group": self.age_groups[0] if self.age_groups else None,
            "special_population": self.special_population,
        }


# Drug class patterns
_DRUG_CLASSES = {
    "thiazide_or_thiazide_like": [
        re.compile(r"thiazide(?:\s*[-/]\s*like)?", re.IGNORECASE),
        re.compile(r"HCTZ", re.IGNORECASE),
        re.compile(r"hydrochlorothiazide", re.IGNORECASE),
        re.compile(r"chlorthalidone", re.IGNORECASE),
        re.compile(r"indapamide", re.IGNORECASE),
    ],
    "ace_inhibitor": [
        re.compile(r"ACE\s*inhibitor", re.IGNORECASE),
        re.compile(r"ACEi\b", re.IGNORECASE),
        re.compile(r"angiotensin[- ]converting[- ]enzyme", re.IGNORECASE),
        re.compile(r"\b(?:enalapril|lisinopril|ramipril|perindopril|captopril)\b", re.IGNORECASE),
    ],
    "arb": [
        re.compile(r"\bARB\b"),
        re.compile(r"angiotensin\s+(?:II\s+)?receptor\s+blocker", re.IGNORECASE),
        re.compile(r"\b(?:losartan|valsartan|telmisartan|candesartan|irbesartan|olmesartan)\b", re.IGNORECASE),
    ],
    "calcium_channel_blocker": [
        re.compile(r"CCB\b"),
        re.compile(r"calcium\s+channel\s+blocker", re.IGNORECASE),
        re.compile(r"dihydropyridine", re.IGNORECASE),
        re.compile(r"\b(?:amlodipine|nifedipine|felodipine)\b", re.IGNORECASE),
    ],
    "beta_blocker": [
        re.compile(r"beta[- ]?blocker", re.IGNORECASE),
        re.compile(r"\b(?:atenolol|bisoprolol|metoprolol|carvedilol|propranolol)\b", re.IGNORECASE),
    ],
}

# Comorbidity patterns
_COMORBIDITIES = {
    "cardiovascular_disease": re.compile(r"\b(?:CVD|cardiovascular\s+disease)\b", re.IGNORECASE),
    "diabetes_mellitus": re.compile(r"\b(?:diabetes|DM|T2DM|type\s+2\s+diabetes)\b", re.IGNORECASE),
    "chronic_kidney_disease": re.compile(r"\b(?:CKD|chronic\s+kidney\s+disease)\b", re.IGNORECASE),
    "heart_failure": re.compile(r"\b(?:heart\s+failure|HF)\b", re.IGNORECASE),
    "stroke": re.compile(r"\b(?:stroke|cerebrovascular)\b", re.IGNORECASE),
    "coronary_artery_disease": re.compile(r"\b(?:coronary\s+artery|CAD|ischaemic\s+heart)\b", re.IGNORECASE),
}

# BP value patterns
_BP_RE = re.compile(
    r"(?:[≥≤<>]?\s*)?\d{2,3}(?:\s*[-–/]\s*\d{2,3})?\s*mmHg",
    re.IGNORECASE,
)

# Age group patterns
_AGE_RE = re.compile(
    r"\b(\d{1,3})\s*(?:[-–]\s*(\d{1,3}))?\s*years?\s*(?:of\s+age|old)?\b",
    re.IGNORECASE,
)


def extract_clinical_entities(text: str) -> ClinicalEntities:
    """Extract clinical entities from text using regex patterns (Phase 1).

    Only extracts entities that are explicitly stated in the text.
    Does NOT infer medical facts from general knowledge.
    """
    entities = ClinicalEntities()

    # Drug classes
    for cls_name, patterns in _DRUG_CLASSES.items():
        for pat in patterns:
            if pat.search(text):
                if cls_name not in entities.drug_classes:
                    entities.drug_classes.append(cls_name)
                break

    # Drug names (extracted from the drug class patterns)
    drug_name_patterns = [
        re.compile(r"\b(amlodipine|nifedipine|felodipine|enalapril|lisinopril|ramipril|"
                   r"perindopril|captopril|losartan|valsartan|telmisartan|candesartan|"
                   r"irbesartan|olmesartan|hydrochlorothiazide|chlorthalidone|indapamide|"
                   r"atenolol|bisoprolol|metoprolol|carvedilol|propranolol|"
                   r"methyldopa|labetalol|hydralazine)\b", re.IGNORECASE),
    ]
    for pat in drug_name_patterns:
        for m in pat.finditer(text):
            name = m.group(1).lower()
            if name not in entities.drug_names:
                entities.drug_names.append(name)

    # Comorbidities
    for comorb_name, pat in _COMORBIDITIES.items():
        if pat.search(text):
            if comorb_name not in entities.comorbidities:
                entities.comorbidities.append(comorb_name)

    # BP values
    bp_matches = _BP_RE.findall(text)
    for bp in bp_matches:
        bp_clean = bp.strip()
        if bp_clean and bp_clean not in entities.bp_thresholds:
            entities.bp_thresholds.append(bp_clean)

    # Target BP (look for explicit "target" near a BP value)
    target_match = re.search(
        r"target\s+(?:blood\s+)?pressure\s*(?:of\s+)?([<>≤≥]?\s*\d{2,3}(?:\s*[-–/]\s*\d{2,3})?\s*mmHg)",
        text,
        re.IGNORECASE,
    )
    if target_match:
        entities.target_bp = target_match.group(1).strip()

    # Age groups
    for m in _AGE_RE.finditer(text):
        age_str = m.group(0).strip()
        if age_str not in entities.age_groups:
            entities.age_groups.append(age_str)

    # Population
    if re.search(r"adults?\s+with\s+(?:confirmed\s+)?hypertension", text, re.IGNORECASE):
        entities.population = "adults_with_confirmed_hypertension"
    elif re.search(r"adults?\s+(?:with|requiring)", text, re.IGNORECASE):
        entities.population = "adults"

    # Special population
    if re.search(r"pregnan", text, re.IGNORECASE):
        entities.special_population = "pregnant_women"
    elif re.search(r"older\s+adults|elderly", text, re.IGNORECASE):
        entities.special_population = "older_adults"

    return entities


# ---------------------------------------------------------------------------
# Clinical priority
# ---------------------------------------------------------------------------

def determine_clinical_priority(
    content_type: str,
    section: Optional[Section] = None,
) -> int:
    """Assign a clinical priority (1=highest, 5=lowest)."""
    if content_type == "recommendation":
        return 1
    if content_type in ("implementation_remark", "clinical_threshold", "drug_guidance",
                        "algorithm"):
        return 1
    if content_type in ("evidence_rationale", "evidence_to_decision", "laboratory_guidance",
                        "risk_assessment", "follow_up", "table"):
        return 2
    if content_type in ("special_setting",):
        return 2
    if content_type in ("research_methodology", "background"):
        return 3
    if content_type in ("definition",):
        return 3
    return 4


# ---------------------------------------------------------------------------
# Full metadata assembly
# ---------------------------------------------------------------------------

def build_chunk_metadata(
    text: str,
    section: Optional[Section],
    pdf_page_start: int,
    pdf_page_end: int,
    page_label_start: Optional[str],
    page_label_end: Optional[str],
    content_type: Optional[str] = None,
    recommendation_meta: Optional[RecommendationMeta] = None,
    recommendation_id: Optional[str] = None,
    is_duplicate: bool = False,
    canonical_chunk_id: Optional[str] = None,
    parent_recommendation: Optional[str] = None,
) -> Dict[str, Any]:
    """Assemble the full metadata dict for a chunk."""

    # Determine content type
    if content_type is None:
        content_type = classify_content_type(text, section)

    # Topic mapping
    sec_num = section.number if section else ""
    topic_info = TOPIC_MAP.get(sec_num, {})
    topic = topic_info.get("topic", "")
    subtopic = topic_info.get("subtopic")

    # If no specific topic mapped, try parent section
    if not topic and sec_num and "." in sec_num:
        parent_num = sec_num.rsplit(".", 1)[0]
        parent_info = TOPIC_MAP.get(parent_num, {})
        topic = parent_info.get("topic", "")

    # Special setting
    special_setting = SPECIAL_SETTING_MAP.get(sec_num)

    # Clinical entities
    entities = extract_clinical_entities(text)
    entity_dict = entities.to_dict()

    # Recommendation metadata
    rec_strength = None
    rec_certainty = None
    if recommendation_meta:
        rec_strength = recommendation_meta.strength
        rec_certainty = recommendation_meta.evidence_certainty
    elif content_type == "recommendation":
        # Try to detect from text
        rec = detect_recommendation(text)
        if rec:
            rec_strength = rec.strength
            rec_certainty = rec.evidence_certainty

    # Clinical priority
    priority = determine_clinical_priority(content_type, section)

    # Section info
    section_heading = ""
    subsection_heading = ""
    if section:
        if section.level <= 1:
            section_heading = section.full_heading or f"{section.number} {section.title}"
        else:
            # Find parent section number
            parts = section.number.split(".")
            parent_num = parts[0] if parts else ""
            section_heading = f"{parent_num} Recommendations" if parent_num == "3" else f"{parent_num}"
            subsection_heading = section.full_heading or f"{section.number} {section.title}"

    metadata = {
        "source_file": "WHO_2021.pdf",
        "organization": "WHO",
        "document_title": "Guideline for the pharmacological treatment of hypertension in adults",
        "publication_year": 2021,
        "domain": "hypertension",
        "pdf_page_start": pdf_page_start,
        "pdf_page_end": pdf_page_end,
        "page_label_start": page_label_start,
        "page_label_end": page_label_end,
        "section": section_heading,
        "subsection": subsection_heading,
        "recommendation_id": recommendation_id,
        "topic": topic,
        "subtopic": subtopic,
        "content_type": content_type,
        "recommendation_strength": rec_strength,
        "evidence_certainty": rec_certainty,
        "population": entity_dict.get("population"),
        "condition": entity_dict.get("condition"),
        "comorbidity": entity_dict.get("comorbidity"),
        "drug_class": entity_dict.get("drug_class"),
        "drug_name": entity_dict.get("drug_name"),
        "bp_threshold": entity_dict.get("bp_threshold"),
        "target_bp": entity_dict.get("target_bp"),
        "age_group": entity_dict.get("age_group"),
        "special_population": entity_dict.get("special_population"),
        "special_setting": special_setting,
        "region_scope": "global",
        "clinical_priority": priority,
        "is_canonical": not is_duplicate,
        "is_duplicate": is_duplicate,
        "canonical_chunk_id": canonical_chunk_id,
        "parent_recommendation": parent_recommendation,
        "entity_extraction_method": entities.entity_extraction_method,
    }

    return metadata
