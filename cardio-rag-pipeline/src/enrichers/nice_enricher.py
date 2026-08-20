"""
Metadata extractor for the NICE3 (NG238) cardiovascular guideline.

Handles:
  - Content-type classification (17 types)
  - Clinical priority assignment (1/2/3)
  - Prevention type detection
  - Patient population extraction
  - Risk assessment metadata (QRISK3)
  - Lipid metadata (LDL, non-HDL targets)
  - Drug metadata (statins, ezetimibe, etc.)
  - Statin intolerance metadata
  - Laboratory/monitoring metadata
  - Referral metadata
  - Off-label statement detection
  - Historical context flagging
  - Full metadata schema assembly per spec §45
"""

import re
import logging
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any, Set

from src.segmenters.nice_segmenter import (
    NiceSection,
    NICE_TOPIC_MAP,
    NICE_SUBTOPIC_MAP,
    NICE_PREVENTION_MAP,
    get_topic_for_section,
    get_subtopic_for_subheading,
    get_prevention_type,
    is_committee_rationale,
    is_implementation_impact,
)
from src.segmenters.nice_rec_parser import NiceRecommendation

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Document-level constants
# ---------------------------------------------------------------------------

NICE3_DOCUMENT_METADATA = {
    "source_file": "NICE_2023.pdf",
    "organization": "NICE",
    "guideline_code": "NG238",
    "document_title": "Cardiovascular disease: risk assessment and reduction, including lipid modification",
    "original_publication_date": "2023-12-14",
    "region_scope": "England",
}


# ---------------------------------------------------------------------------
# Content type classification
# ---------------------------------------------------------------------------

# The 17 content types defined in the spec
CONTENT_TYPES = [
    "recommendation",
    "committee_rationale",
    "implementation_impact",
    "risk_assessment_guidance",
    "lifestyle_guidance",
    "drug_guidance",
    "lipid_target",
    "laboratory_guidance",
    "monitoring_guidance",
    "specialist_referral",
    "contraindication",
    "adverse_effect_guidance",
    "pregnancy_guidance",
    "definition",
    "technology_appraisal_reference",
    "research_recommendation",
    "context",
    "update_information",
    "other",
]

# Content type detection patterns (ordered by specificity — first match wins)
_CONTENT_TYPE_PATTERNS = [
    ("committee_rationale", [
        re.compile(r"Why\s+the\s+committee\s+made\s+these?\s+recommendations?", re.IGNORECASE),
    ]),
    ("implementation_impact", [
        re.compile(r"How\s+the\s+recommendations?\s+might\s+affect\s+practice", re.IGNORECASE),
    ]),
    ("specialist_referral", [
        re.compile(r"refer\s+(?:to\s+)?(?:a\s+)?specialist", re.IGNORECASE),
        re.compile(r"specialist\s+(?:review|referral|assessment)", re.IGNORECASE),
    ]),
    ("contraindication", [
        re.compile(r"contraindicated", re.IGNORECASE),
        re.compile(r"contraindication", re.IGNORECASE),
        re.compile(r"do\s+not\s+(?:offer|use|start|prescribe)", re.IGNORECASE),
    ]),
    ("pregnancy_guidance", [
        re.compile(r"pregnan(?:cy|t)", re.IGNORECASE),
        re.compile(r"women?\s+(?:of|who)\s+(?:childbearing|may\s+become\s+pregnant)", re.IGNORECASE),
    ]),
    ("adverse_effect_guidance", [
        re.compile(r"adverse\s+effect", re.IGNORECASE),
        re.compile(r"side\s+effect", re.IGNORECASE),
        re.compile(r"muscle\s+(?:symptoms?|pain|aches?)", re.IGNORECASE),
        re.compile(r"creatine\s+kinase", re.IGNORECASE),
    ]),
    ("lipid_target", [
        re.compile(r"lipid\s+target", re.IGNORECASE),
        re.compile(r"LDL\s+cholesterol\s+(?:level|target)", re.IGNORECASE),
        re.compile(r"non[- ]HDL\s+cholesterol\s+(?:level|target)", re.IGNORECASE),
    ]),
    ("monitoring_guidance", [
        re.compile(r"monitor(?:ing)?", re.IGNORECASE),
        re.compile(r"(?:repeat|recheck)\s+(?:blood\s+)?test", re.IGNORECASE),
        re.compile(r"annual\s+(?:medication\s+)?review", re.IGNORECASE),
    ]),
    ("laboratory_guidance", [
        re.compile(r"(?:blood|baseline)\s+test", re.IGNORECASE),
        re.compile(r"liver\s+transaminase", re.IGNORECASE),
        re.compile(r"full\s+lipid\s+profile", re.IGNORECASE),
        re.compile(r"renal\s+function", re.IGNORECASE),
        re.compile(r"HbA1c", re.IGNORECASE),
        re.compile(r"thyroid[- ]stimulating\s+hormone", re.IGNORECASE),
    ]),
    ("risk_assessment_guidance", [
        re.compile(r"QRISK3", re.IGNORECASE),
        re.compile(r"(?:cardiovascular|CVD)\s+risk\s+assessment", re.IGNORECASE),
        re.compile(r"10[- ]year\s+risk", re.IGNORECASE),
    ]),
    ("drug_guidance", [
        re.compile(r"atorvastatin", re.IGNORECASE),
        re.compile(r"ezetimibe", re.IGNORECASE),
        re.compile(r"statin", re.IGNORECASE),
        re.compile(r"alirocumab|evolocumab|inclisiran|bempedoic", re.IGNORECASE),
    ]),
    ("lifestyle_guidance", [
        re.compile(r"(?:cardioprotective\s+)?diet", re.IGNORECASE),
        re.compile(r"physical\s+activity", re.IGNORECASE),
        re.compile(r"weight\s+management", re.IGNORECASE),
        re.compile(r"alcohol", re.IGNORECASE),
        re.compile(r"smok(?:e|ing|cessation)", re.IGNORECASE),
        re.compile(r"plant\s+stanols?", re.IGNORECASE),
        re.compile(r"saturated\s+fat", re.IGNORECASE),
    ]),
    ("definition", [
        re.compile(r"^Terms?\s+used\s+in\s+this\s+guideline", re.IGNORECASE | re.MULTILINE),
    ]),
    ("research_recommendation", [
        re.compile(r"research\s+recommendation", re.IGNORECASE),
    ]),
    ("technology_appraisal_reference", [
        re.compile(r"\bTA\d{2,4}\b"),
    ]),
]


def classify_content_type(
    text: str,
    section: Optional[NiceSection] = None,
    is_recommendation: bool = False,
) -> str:
    """Classify a text block into one of the defined content types."""

    if is_recommendation:
        return "recommendation"

    # Check for committee rationale first
    if is_committee_rationale(text):
        return "committee_rationale"
    if is_implementation_impact(text):
        return "implementation_impact"

    # Section-based classification
    if section:
        if section.number == "terms":
            return "definition"
        if section.number == "research":
            return "research_recommendation"
        if section.number == "context":
            return "context"
        if section.number == "update_info":
            return "update_information"

    # Pattern-based classification
    text_scan = text[:3000]
    for content_type, patterns in _CONTENT_TYPE_PATTERNS:
        for pat in patterns:
            if pat.search(text_scan):
                return content_type

    return "other"


# ---------------------------------------------------------------------------
# Clinical priority
# ---------------------------------------------------------------------------

def determine_clinical_priority(content_type: str) -> int:
    """Assign a clinical priority (1=highest, 3=lowest).

    Per spec §19:
    - Priority 1: direct recommendations, thresholds, drug treatment, monitoring, referral, contraindications
    - Priority 2: committee rationale, explanatory text, risk tool explanation, evidence
    - Priority 3: implementation impact, research recommendations, context, update notes
    """
    priority_1 = {
        "recommendation", "drug_guidance", "lipid_target",
        "laboratory_guidance", "monitoring_guidance", "specialist_referral",
        "contraindication", "adverse_effect_guidance", "pregnancy_guidance",
        "risk_assessment_guidance",
    }
    priority_2 = {
        "committee_rationale", "lifestyle_guidance", "definition",
        "technology_appraisal_reference",
    }
    priority_3 = {
        "implementation_impact", "research_recommendation", "context",
        "update_information",
    }

    if content_type in priority_1:
        return 1
    if content_type in priority_2:
        return 2
    if content_type in priority_3:
        return 3
    return 3


# ---------------------------------------------------------------------------
# Population extraction
# ---------------------------------------------------------------------------

_POPULATION_PATTERNS = {
    "people_without_established_cvd": [
        re.compile(r"(?:people|adults?)\s+without\s+(?:established\s+)?(?:CVD|cardiovascular\s+disease)", re.IGNORECASE),
    ],
    "people_with_cvd": [
        re.compile(r"(?:people|adults?)\s+with\s+(?:established\s+)?(?:CVD|cardiovascular\s+disease)", re.IGNORECASE),
        re.compile(r"secondary\s+prevention\s+of\s+CVD", re.IGNORECASE),
    ],
    "people_at_high_cvd_risk": [
        re.compile(r"(?:high|increased)\s+(?:CVD\s+)?risk", re.IGNORECASE),
        re.compile(r"QRISK3\s+score\s+of\s+10%", re.IGNORECASE),
    ],
    "people_with_type_1_diabetes": [
        re.compile(r"type\s+1\s+diabetes", re.IGNORECASE),
    ],
    "people_with_type_2_diabetes": [
        re.compile(r"type\s+2\s+diabetes", re.IGNORECASE),
    ],
    "people_with_ckd": [
        re.compile(r"chronic\s+kidney\s+disease", re.IGNORECASE),
        re.compile(r"\bCKD\b"),
    ],
    "people_aged_85_or_older": [
        re.compile(r"(?:85\s+(?:years?\s+)?(?:or\s+)?(?:older|over))|(?:over\s+85)", re.IGNORECASE),
    ],
    "people_with_statin_intolerance": [
        re.compile(r"statin[s]?\s+(?:is|are)\s+not\s+tolerated", re.IGNORECASE),
        re.compile(r"statin\s+intoleran", re.IGNORECASE),
    ],
    "people_with_statin_contraindication": [
        re.compile(r"statin[s]?\s+(?:is|are)\s+contraindicated", re.IGNORECASE),
    ],
    "people_with_acute_coronary_syndrome": [
        re.compile(r"acute\s+coronary\s+syndrome", re.IGNORECASE),
        re.compile(r"\bACS\b"),
    ],
    "people_taking_lipid_lowering_treatment": [
        re.compile(r"(?:people|adults?)\s+(?:taking|on)\s+(?:lipid[- ]lowering|statin)\s+(?:treatment|therapy)", re.IGNORECASE),
    ],
}


def extract_populations(text: str) -> List[str]:
    """Extract patient populations mentioned in the text."""
    populations = []
    for pop_id, patterns in _POPULATION_PATTERNS.items():
        for pat in patterns:
            if pat.search(text):
                populations.append(pop_id)
                break
    return populations


# ---------------------------------------------------------------------------
# Risk assessment metadata
# ---------------------------------------------------------------------------

_QRISK3_RE = re.compile(r"QRISK3", re.IGNORECASE)
_RISK_HORIZON_RE = re.compile(r"(\d+)[- ]year\s+(?:risk|QRISK)", re.IGNORECASE)
_RISK_THRESHOLD_RE = re.compile(r"QRISK3\s+(?:score\s+(?:of\s+)?)?(\d+%)", re.IGNORECASE)
_AGE_RANGE_RE = re.compile(r"(?:aged?\s+)?(\d{2})\s*(?:to|–|-)\s*(\d{2})\s*(?:years?)?", re.IGNORECASE)


def extract_risk_assessment_meta(text: str) -> Dict[str, Any]:
    """Extract CVD risk assessment metadata."""
    meta: Dict[str, Any] = {}

    if _QRISK3_RE.search(text):
        meta["risk_tool"] = "QRISK3"

    horizon_m = _RISK_HORIZON_RE.search(text)
    if horizon_m:
        meta["risk_horizon"] = f"{horizon_m.group(1)} years"

    threshold_m = _RISK_THRESHOLD_RE.search(text)
    if threshold_m:
        meta["risk_threshold"] = threshold_m.group(1)

    age_m = _AGE_RANGE_RE.search(text)
    if age_m:
        meta["age_min"] = int(age_m.group(1))
        meta["age_max"] = int(age_m.group(2))

    return meta


# ---------------------------------------------------------------------------
# Lipid metadata
# ---------------------------------------------------------------------------

_LIPID_MEASURES = {
    "LDL": re.compile(r"\bLDL\s+cholesterol\b", re.IGNORECASE),
    "non-HDL": re.compile(r"\bnon[- ]HDL\s+cholesterol\b", re.IGNORECASE),
    "HDL": re.compile(r"(?<!\bnon[- ])\bHDL\s+cholesterol\b", re.IGNORECASE),
    "total cholesterol": re.compile(r"\btotal\s+cholesterol\b", re.IGNORECASE),
    "triglycerides": re.compile(r"\btriglycerides?\b", re.IGNORECASE),
}

_LIPID_TARGET_RE = re.compile(
    r"((?:LDL|non[- ]HDL|HDL|total)\s+cholesterol\s+(?:levels?\s+(?:of\s+)?)?)"
    r"([\d.]+\s+mmol\s+per\s+litre(?:\s+or\s+(?:less|more))?)",
    re.IGNORECASE,
)

_LIPID_VALUE_RE = re.compile(
    r"([\d.]+)\s*(?:mmol(?:\s+per\s+litre|/L|/l))",
    re.IGNORECASE,
)


def extract_lipid_metadata(text: str) -> Dict[str, Any]:
    """Extract lipid measurement metadata."""
    meta: Dict[str, Any] = {}

    measures = []
    for measure_name, pat in _LIPID_MEASURES.items():
        if pat.search(text):
            measures.append(measure_name)
    if measures:
        meta["lipid_measure"] = measures

    # Extract lipid targets
    targets = []
    for m in _LIPID_TARGET_RE.finditer(text):
        targets.append(m.group(0).strip())
    if targets:
        meta["lipid_target"] = targets[0] if len(targets) == 1 else targets

    return meta


# ---------------------------------------------------------------------------
# Drug metadata
# ---------------------------------------------------------------------------

_DRUG_PATTERNS = {
    "atorvastatin": re.compile(r"\batorvastatin\b", re.IGNORECASE),
    "simvastatin": re.compile(r"\bsimvastatin\b", re.IGNORECASE),
    "rosuvastatin": re.compile(r"\brosuvastatin\b", re.IGNORECASE),
    "pravastatin": re.compile(r"\bpravastatin\b", re.IGNORECASE),
    "fluvastatin": re.compile(r"\bfluvastatin\b", re.IGNORECASE),
    "ezetimibe": re.compile(r"\bezetimibe\b", re.IGNORECASE),
    "alirocumab": re.compile(r"\balirocumab\b", re.IGNORECASE),
    "evolocumab": re.compile(r"\bevolocumab\b", re.IGNORECASE),
    "inclisiran": re.compile(r"\binclisiran\b", re.IGNORECASE),
    "bempedoic acid": re.compile(r"\bbempedoic\s+acid\b", re.IGNORECASE),
    "aspirin": re.compile(r"\baspirin\b", re.IGNORECASE),
}

_DOSE_RE = re.compile(
    r"(\d+(?:\.\d+)?)\s*mg\b",
    re.IGNORECASE,
)

_DRUG_CLASS_MAP = {
    "atorvastatin": "statin",
    "simvastatin": "statin",
    "rosuvastatin": "statin",
    "pravastatin": "statin",
    "fluvastatin": "statin",
    "ezetimibe": "cholesterol_absorption_inhibitor",
    "alirocumab": "PCSK9_inhibitor",
    "evolocumab": "PCSK9_inhibitor",
    "inclisiran": "siRNA_PCSK9",
    "bempedoic acid": "ACL_inhibitor",
    "aspirin": "antiplatelet",
}


def extract_drug_metadata(text: str) -> Dict[str, Any]:
    """Extract drug information from text."""
    meta: Dict[str, Any] = {}

    drugs_found = []
    for drug_name, pat in _DRUG_PATTERNS.items():
        if pat.search(text):
            drugs_found.append(drug_name)

    if drugs_found:
        meta["drug_names"] = drugs_found
        # Get drug classes
        classes = list(set(_DRUG_CLASS_MAP.get(d, "unknown") for d in drugs_found))
        meta["drug_class"] = classes

    # Extract doses
    doses = []
    for m in _DOSE_RE.finditer(text):
        dose = f"{m.group(1)} mg"
        if dose not in doses:
            doses.append(dose)
    if doses:
        meta["dose"] = doses[0] if len(doses) == 1 else doses

    return meta


# ---------------------------------------------------------------------------
# Statin intolerance metadata
# ---------------------------------------------------------------------------

_STATIN_STATUS_PATTERNS = {
    "high_intensity_not_tolerated": re.compile(
        r"high[- ]intensity\s+statin\s+(?:is\s+)?not\s+tolerated", re.IGNORECASE,
    ),
    "statin_intolerant": re.compile(r"statin\s+intoleran", re.IGNORECASE),
    "statin_contraindicated": re.compile(r"statin[s]?\s+(?:is|are)\s+contraindicated", re.IGNORECASE),
    "muscle_symptoms": re.compile(r"muscle\s+(?:symptoms?|pain|aches?)", re.IGNORECASE),
}


def extract_statin_intolerance_meta(text: str) -> Dict[str, Any]:
    """Extract statin intolerance metadata."""
    meta: Dict[str, Any] = {}
    statuses = []
    for status, pat in _STATIN_STATUS_PATTERNS.items():
        if pat.search(text):
            statuses.append(status)
    if statuses:
        meta["statin_status"] = statuses
    return meta


# ---------------------------------------------------------------------------
# Laboratory / monitoring metadata
# ---------------------------------------------------------------------------

_TEST_PATTERNS = {
    "full lipid profile": re.compile(r"full\s+lipid\s+profile", re.IGNORECASE),
    "liver transaminase": re.compile(r"liver\s+transaminase", re.IGNORECASE),
    "creatine kinase": re.compile(r"creatine\s+kinase", re.IGNORECASE),
    "renal function": re.compile(r"renal\s+function", re.IGNORECASE),
    "HbA1c": re.compile(r"HbA1c", re.IGNORECASE),
    "fasting glucose": re.compile(r"fasting\s+(?:blood\s+)?glucose", re.IGNORECASE),
    "thyroid-stimulating hormone": re.compile(r"thyroid[- ]stimulating\s+hormone|TSH", re.IGNORECASE),
}

_TIMING_RE = re.compile(
    r"(\d+\s+to\s+\d+\s+months?\s+(?:after|before)[^.]*)",
    re.IGNORECASE,
)

_MONITORING_FREQ_RE = re.compile(
    r"(annual(?:ly)?|every\s+\d+\s+months?|(?:\d+\s+to\s+\d+\s+months?))",
    re.IGNORECASE,
)


def extract_laboratory_metadata(text: str) -> Dict[str, Any]:
    """Extract laboratory and monitoring metadata."""
    meta: Dict[str, Any] = {}

    tests = []
    for test_name, pat in _TEST_PATTERNS.items():
        if pat.search(text):
            tests.append(test_name)
    if tests:
        meta["test_names"] = tests

    timing_m = _TIMING_RE.search(text)
    if timing_m:
        meta["test_timing"] = timing_m.group(1).strip()

    freq_m = _MONITORING_FREQ_RE.search(text)
    if freq_m:
        meta["monitoring_interval"] = freq_m.group(1).strip()

    return meta


# ---------------------------------------------------------------------------
# Referral metadata
# ---------------------------------------------------------------------------

_REFERRAL_URGENCY_RE = re.compile(r"(urgent(?:ly)?|routine|consider\s+referr)", re.IGNORECASE)
_REFERRAL_TRIGGER_RE = re.compile(
    r"refer\s+(?:to\s+)?(?:a\s+)?specialist.*?(?:if|when|for)\s+([^.]+)",
    re.IGNORECASE,
)

_TRIGLYCERIDE_THRESHOLD_RE = re.compile(
    r"triglycerides?\s+(?:concentration\s+)?(?:of\s+)?(?:(?:greater\s+than|more\s+than|above|>|≥)\s*)?"
    r"([\d.]+\s*mmol(?:\s+per\s+litre|/L)?)",
    re.IGNORECASE,
)


def extract_referral_metadata(text: str) -> Dict[str, Any]:
    """Extract specialist referral metadata."""
    meta: Dict[str, Any] = {}

    urgency_m = _REFERRAL_URGENCY_RE.search(text)
    if urgency_m:
        raw = urgency_m.group(1).lower()
        meta["referral_urgency"] = "urgent" if "urgent" in raw else "routine"

    trigger_m = _REFERRAL_TRIGGER_RE.search(text)
    if trigger_m:
        meta["referral_trigger"] = trigger_m.group(1).strip()[:200]

    trig_m = _TRIGLYCERIDE_THRESHOLD_RE.search(text)
    if trig_m:
        meta["referral_threshold"] = trig_m.group(0).strip()

    return meta


# ---------------------------------------------------------------------------
# Special flags
# ---------------------------------------------------------------------------

_OFF_LABEL_RE = re.compile(r"off[- ]label", re.IGNORECASE)
_HISTORICAL_RE = re.compile(
    r"(?:previous(?:ly)?|former(?:ly)?|old(?:er)?)\s+(?:recommendation|guideline|threshold|target)",
    re.IGNORECASE,
)


def detect_off_label(text: str) -> bool:
    """Check if text contains an off-label statement."""
    return bool(_OFF_LABEL_RE.search(text))


def detect_historical_context(text: str) -> bool:
    """Check if text discusses historical/superseded recommendations."""
    return bool(_HISTORICAL_RE.search(text))


# ---------------------------------------------------------------------------
# Full metadata assembly
# ---------------------------------------------------------------------------

def build_nice3_chunk_metadata(
    text: str,
    section: Optional[NiceSection],
    pdf_page_start: int,
    pdf_page_end: int,
    page_label_start: Optional[str] = None,
    page_label_end: Optional[str] = None,
    content_type: Optional[str] = None,
    recommendation: Optional[NiceRecommendation] = None,
    subsection: Optional[str] = None,
    related_recommendations: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """Assemble the full metadata dict for a NICE3 chunk.

    Per spec §45, every chunk contains the complete metadata schema.
    """
    # Determine content type
    is_rec = recommendation is not None
    if content_type is None:
        content_type = classify_content_type(text, section, is_recommendation=is_rec)

    # Section info
    section_heading = ""
    if section:
        section_heading = section.full_heading or f"{section.number} {section.title}"

    # Topic mapping
    sec_num = section.number if section else ""
    topic_info = get_topic_for_section(sec_num)
    topic = topic_info.get("topic")
    subtopic = topic_info.get("subtopic")

    # Refine subtopic from subheading
    if subsection and get_subtopic_for_subheading(subsection):
        subtopic = get_subtopic_for_subheading(subsection)

    # Prevention type
    prevention_type = get_prevention_type(sec_num) if sec_num else None

    # Clinical priority
    clinical_priority = determine_clinical_priority(content_type)

    # Extract clinical entities
    populations = extract_populations(text)
    risk_meta = extract_risk_assessment_meta(text)
    lipid_meta = extract_lipid_metadata(text)
    drug_meta = extract_drug_metadata(text)
    statin_meta = extract_statin_intolerance_meta(text)
    lab_meta = extract_laboratory_metadata(text)
    referral_meta = extract_referral_metadata(text)

    # Recommendation-specific fields
    rec_id = None
    rec_original_date = None
    rec_amended_dates = []
    cross_refs = []
    ta_refs = []
    evidence_ref = None
    ext_guideline_refs = []

    if recommendation:
        rec_id = recommendation.recommendation_id
        rec_original_date = recommendation.original_date
        rec_amended_dates = recommendation.amended_dates
        cross_refs = recommendation.cross_refs
        ta_refs = recommendation.technology_appraisal_refs
        evidence_ref = recommendation.evidence_review_reference
        ext_guideline_refs = recommendation.external_guideline_references
    else:
        # Still extract from text for non-recommendation chunks
        from src.segmenters.nice_rec_parser import (
            extract_cross_references,
            extract_technology_appraisals,
            extract_evidence_review_reference,
            extract_external_guideline_references,
        )
        cross_refs = extract_cross_references(text)
        ta_refs = extract_technology_appraisals(text)
        evidence_ref = extract_evidence_review_reference(text)
        ext_guideline_refs = extract_external_guideline_references(text)

    # Special populations
    special_populations = []
    if sec_num == "1.8" or "chronic kidney disease" in text.lower() or "CKD" in text:
        special_populations.append("chronic_kidney_disease")
    if re.search(r"pregnan", text, re.IGNORECASE):
        special_populations.append("pregnancy")

    # Off-label and historical flags
    off_label = detect_off_label(text)
    historical = detect_historical_context(text)

    # Build the full metadata schema (§45)
    metadata = {
        # Document-level
        "source_file": NICE3_DOCUMENT_METADATA["source_file"],
        "organization": NICE3_DOCUMENT_METADATA["organization"],
        "guideline_code": NICE3_DOCUMENT_METADATA["guideline_code"],
        "document_title": NICE3_DOCUMENT_METADATA["document_title"],
        "original_publication_date": NICE3_DOCUMENT_METADATA["original_publication_date"],

        # Page provenance
        "pdf_page_start": pdf_page_start,
        "pdf_page_end": pdf_page_end,
        "printed_page_start": page_label_start,
        "printed_page_end": page_label_end,

        # Section hierarchy
        "section": section_heading,
        "subsection": subsection,

        # Recommendation metadata
        "recommendation_id": rec_id,
        "recommendation_original_date": rec_original_date,
        "recommendation_amended_dates": rec_amended_dates,

        # Clinical mapping
        "domain": "cardiovascular_disease",
        "topic": topic,
        "subtopic": subtopic,
        "content_type": content_type,
        "prevention_type": prevention_type,

        # Patient populations
        "population": populations if populations else [],
        "special_population": special_populations if special_populations else [],

        # Risk assessment
        "risk_tool": risk_meta.get("risk_tool"),
        "risk_threshold": risk_meta.get("risk_threshold"),

        # Lipid metadata
        "lipid_measure": lipid_meta.get("lipid_measure", []),
        "lipid_target": lipid_meta.get("lipid_target"),

        # Drug metadata
        "drug_names": drug_meta.get("drug_names", []),
        "dose": drug_meta.get("dose"),

        # Laboratory / monitoring
        "test_names": lab_meta.get("test_names", []),
        "monitoring_interval": lab_meta.get("monitoring_interval"),

        # Cross-references
        "external_guideline_references": ext_guideline_refs,
        "technology_appraisal_refs": ta_refs,
        "related_recommendation_ids": related_recommendations or cross_refs,
        "evidence_review_reference": evidence_ref,

        # Scope
        "region_scope": NICE3_DOCUMENT_METADATA["region_scope"],

        # Priority and flags
        "clinical_priority": clinical_priority,
        "is_canonical": True,
        "is_duplicate": False,
        "canonical_chunk_id": None,
        "historical_context": historical,
        "off_label_statement_present": off_label,

        # Manual review
        "requires_manual_review": False,
        "review_reason": None,

        # Token count (filled by chunker)
        "token_count": 0,
    }

    return metadata
