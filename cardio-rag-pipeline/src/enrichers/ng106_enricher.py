"""
Metadata extractor for the NICE NG106 guideline (Chronic heart failure in adults).

Extracts:
  - Heart failure phenotypes (HFrEF, HFmrEF, HFpEF)
  - Natriuretic peptides (NT-proBNP, BNP) and referral thresholds
  - Diagnostic modalities (Echocardiography, Cardiac MRI, ECG)
  - Core pharmacological classes:
      * ACE inhibitors / ARBs
      * ARNI (Sacubitril valsartan)
      * Beta-blockers (Bisoprolol, Carvedilol, Nebivolol)
      * MRAs (Spironolactone, Eplerenone)
      * SGLT2 inhibitors (Dapagliflozin, Empagliflozin)
      * Loop diuretics, Ivabradine, Digoxin, Hydralazine + Nitrate
      * Intravenous iron therapy
  - Device therapy (ICD, CRT-P, CRT-D) and interventions
  - Content types, dates, clinical priorities and provenance
"""

import re
import logging
from typing import List, Optional, Dict, Any, Set

from src.segmenters.ng106_segmenter import (
    Ng106Section,
    NG106_TOPIC_MAP,
)
from src.segmenters.nice_rec_parser import NiceRecommendation

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Document metadata
# ---------------------------------------------------------------------------

NG106_DOCUMENT_METADATA = {
    "source_file": "NICE_NG106.pdf",
    "organization": "NICE",
    "guideline_code": "NG106",
    "document_title": "Chronic heart failure in adults: diagnosis and management",
    "original_publication_date": "2018-09-12",
    "last_updated_date": "2025-09-03",
    "region_scope": "England",
}

# ---------------------------------------------------------------------------
# Regex extractors
# ---------------------------------------------------------------------------

_PHENOTYPE_PATTERNS = {
    "HFrEF": re.compile(r"\b(?:reduced\s+ejection\s+fraction|HFrEF|LVEF\s*(?:<|<=|≤)\s*40%?)\b", re.I),
    "HFmrEF": re.compile(r"\b(?:mildly\s+reduced\s+ejection\s+fraction|HFmrEF)\b", re.I),
    "HFpEF": re.compile(r"\b(?:preserved\s+ejection\s+fraction|HFpEF|LVEF\s*(?:>|>=|≥)\s*50%?)\b", re.I),
    "valve_disease": re.compile(r"\b(?:valvular|valve\s+disease|aortic\s+stenosis|mitral\s+regurgitation)\b", re.I),
    "chronic_kidney_disease": re.compile(r"\b(?:chronic\s+kidney\s+disease|CKD|eGFR)\b", re.I),
    "iron_deficiency": re.compile(r"\b(?:iron\s+deficiency|ferritin|transferrin\s+saturation|TSAT)\b", re.I),
}

_BIOMARKER_PATTERNS = {
    "NT_proBNP": re.compile(r"\bNT[- ]?proBNP\b", re.I),
    "BNP": re.compile(r"\bBNP\b"),
    "serum_potassium": re.compile(r"\b(?:serum\s+potassium|potassium|hyperkalaemia)\b", re.I),
    "serum_creatinine": re.compile(r"\b(?:serum\s+creatinine|creatinine|eGFR)\b", re.I),
}

_DRUG_CLASS_PATTERNS = {
    "ACE_inhibitors": re.compile(r"\b(?:ACE\s+inhibitors?|enalapril|ramipril|lisinopril|perindopril|captopril)\b", re.I),
    "ARBs": re.compile(r"\b(?:angiotensin\s+II\s+receptor\s+(?:blockers?|antagonists?)|ARBs?|candesartan|losartan|valsartan)\b", re.I),
    "ARNI": re.compile(r"\b(?:sacubitril\s+valsartan|ARNI)\b", re.I),
    "beta_blockers": re.compile(r"\b(?:beta[- ]blockers?|bisoprolol|carvedilol|nebivolol)\b", re.I),
    "MRAs": re.compile(r"\b(?:mineralocorticoid\s+receptor\s+antagonists?|MRAs?|spironolactone|eplerenone)\b", re.I),
    "SGLT2_inhibitors": re.compile(r"\b(?:SGLT2\s+inhibitors?|dapagliflozin|empagliflozin)\b", re.I),
    "diuretics": re.compile(r"\b(?:loop\s+diuretics?|furosemide|bumetanide|torasemide|diuretic)\b", re.I),
    "ivabradine": re.compile(r"\bivabradine\b", re.I),
    "digoxin": re.compile(r"\bdigoxin\b", re.I),
    "hydralazine_nitrate": re.compile(r"\b(?:hydralazine|nitrates?)\b", re.I),
    "intravenous_iron": re.compile(r"\b(?:intravenous\s+iron|ferric\s+derisomaltose|ferric\s+carboxymaltose)\b", re.I),
    "calcium_channel_blockers": re.compile(r"\b(?:calcium[- ]channel\s+blockers?|amlodipine|verapamil|diltiazem)\b", re.I),
}

_INTERVENTION_PATTERNS = {
    "ICD": re.compile(r"\b(?:implantable\s+cardioverter\s+defibrillators?|ICDs?)\b", re.I),
    "CRT": re.compile(r"\b(?:cardiac\s+resynchronisation\s+therapy|CRT[- ]?[PD]?)\b", re.I),
    "cardiac_rehabilitation": re.compile(r"\b(?:cardiac\s+rehabilitation|rehabilitation\s+programme)\b", re.I),
    "coronary_revascularisation": re.compile(r"\b(?:coronary\s+revascularisation|CABG|PCI)\b", re.I),
    "valve_surgery": re.compile(r"\b(?:valve\s+replacement|valve\s+repair|TAVI)\b", re.I),
    "heart_transplantation": re.compile(r"\b(?:cardiac\s+transplantation|heart\s+transplant)\b", re.I),
}


def extract_heart_failure_metadata(text: str) -> Dict[str, Any]:
    """Extract clinical entities specific to Heart Failure."""
    phenotypes = [p for p, pat in _PHENOTYPE_PATTERNS.items() if pat.search(text)]
    biomarkers = [b for b, pat in _BIOMARKER_PATTERNS.items() if pat.search(text)]
    drug_classes = [d for d, pat in _DRUG_CLASS_PATTERNS.items() if pat.search(text)]
    interventions = [i for i, pat in _INTERVENTION_PATTERNS.items() if pat.search(text)]

    # Threshold checks
    urgent_referral = bool(re.search(r"2\s*weeks?|2[- ]week|urgently", text, re.I) and "NT_proBNP" in biomarkers)
    bnp_thresholds = []
    if re.search(r"2[,\s]?000\s*(?:ng|pg)", text, re.I):
        bnp_thresholds.append(">2000 ng/L")
    if re.search(r"400\s*(?:to|-)\s*2[,\s]?000", text, re.I):
        bnp_thresholds.append("400-2000 ng/L")
    if re.search(r"(?:below|<)\s*400", text, re.I):
        bnp_thresholds.append("<400 ng/L")

    return {
        "heart_failure_phenotypes": phenotypes,
        "biomarkers_detected": biomarkers,
        "drug_classes": drug_classes,
        "interventions_and_devices": interventions,
        "bnp_thresholds": bnp_thresholds,
        "urgent_2_week_referral": urgent_referral,
    }


def build_ng106_chunk_metadata(
    rec: Optional[NiceRecommendation],
    section: Ng106Section,
    subheading: Optional[str],
    content_type: str,
    pdf_page_start: int,
    pdf_page_end: int,
    text: str,
) -> Dict[str, Any]:
    """Build full metadata dictionary for an NG106 chunk."""
    topic_info = NG106_TOPIC_MAP.get(section.number, {"topic": "unclassified", "subtopic": None})
    topic = topic_info.get("topic", "unclassified")
    subtopic = topic_info.get("subtopic") or subheading

    hf_meta = extract_heart_failure_metadata(text)

    # Priority
    if content_type == "recommendation":
        clinical_priority = 1
    elif content_type in ("committee_rationale", "implementation_impact"):
        clinical_priority = 2
    else:
        clinical_priority = 3

    meta = {
        **NG106_DOCUMENT_METADATA,
        "pdf_page_start": pdf_page_start,
        "pdf_page_end": pdf_page_end,
        "section": section.full_heading or section.title,
        "subsection": subheading or section.title,
        "recommendation_id": rec.recommendation_id if rec else None,
        "recommendation_original_date": rec.original_date if rec else None,
        "recommendation_amended_dates": rec.amended_dates if rec else [],
        "domain": "chronic_heart_failure",
        "topic": topic,
        "subtopic": subtopic,
        "content_type": content_type,
        "clinical_priority": clinical_priority,
        "cross_references": rec.cross_refs if rec else [],
        "technology_appraisals": rec.technology_appraisal_refs if rec else [],
        "clinical_metadata": hf_meta,
        "historical_context": False,
        "requires_manual_review": False,
    }

    return meta
