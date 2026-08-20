#!/usr/bin/env python3
"""
fix_chunks.py — Deterministic, idempotent repair script for medical guideline RAG chunks.

Implements all 13 rules (R1–R13) in workflow order:
  R1  -> Truncated text + orphan fragment merge
  R2  -> Unclosed date bracket completion
  R3  -> Heading leak strip (tail)
  R10 -> Buried recommendations extraction
  R9  -> Oversized / mixed chunk split
  R5  -> Recommendation box misclassified as table (WHO)
  R6  -> Off-by-one section/figure labels (WHO)
  R7  -> Garbage / micro chunks (WHO)
  R4  -> Subsection misassignment (recommendations)
  R8  -> Canonical direction for duplicates (WHO)
  R11 -> Per-chunk page metadata (PDF span search + printed labels)
  R12 -> Date metadata consistency
  R13 -> Token recount (tiktoken cl100k_base)

Validation gates V1–V6 enforced at exit.
"""

import os
import sys
import re
import json
import copy
import shutil
import argparse
from pathlib import Path
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Any, Tuple, Optional, Set

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

try:
    import tiktoken
    _ENC = tiktoken.get_encoding("cl100k_base")
    def count_tokens(t: str) -> int:
        return len(_ENC.encode(t))
except Exception:
    def count_tokens(t: str) -> int:
        return max(1, round(len(t) / 4))

try:
    import pymupdf as fitz
except ImportError:
    try:
        import fitz
    except ImportError:
        fitz = None

try:
    from src.clean_text import clean_chunk_noise
except ImportError:
    try:
        from clean_text import clean_chunk_noise
    except ImportError:
        def clean_chunk_noise(t: str) -> str:
            return t


# ============================================================================
# FIX REPORTING DATASTRUCTURES
# ============================================================================

@dataclass
class FixEntry:
    rule_id: str
    chunk_id: str
    action: str
    field_name: Optional[str] = None
    before_snippet: Optional[str] = None
    after_snippet: Optional[str] = None

class FixReporter:
    def __init__(self):
        self.entries: List[FixEntry] = []

    def log(self, rule_id: str, chunk_id: str, action: str,
            field_name: Optional[str] = None,
            before_snippet: Optional[str] = None,
            after_snippet: Optional[str] = None):
        entry = FixEntry(
            rule_id=rule_id,
            chunk_id=chunk_id,
            action=action,
            field_name=field_name,
            before_snippet=before_snippet[:150] if before_snippet else None,
            after_snippet=after_snippet[:150] if after_snippet else None,
        )
        self.entries.append(entry)

    def to_dict_list(self) -> List[Dict[str, Any]]:
        return [asdict(e) for e in self.entries]

    def __len__(self):
        return len(self.entries)


# ============================================================================
# W1: GROUND TRUTH INVENTORIES & CONSTANTS
# ============================================================================

# Figure Map (WHO03)
WHO_FIGURE_MAP = {
    "Fig. 1": {"section": "2 Method for developing the guideline", "subsection": "2.2 Analytical framework and PICOs", "page": 15, "label": "3"},
    "Fig. 2": {"section": "3 Recommendations", "subsection": "3.2 Laboratory testing before and during pharmacological treatment", "page": 21, "label": "9"},
    "Fig. 3": {"section": "6 Implementation tools", "subsection": "6.1 Guideline recommendations", "page": 38, "label": "26"},
    "Fig. 4": {"section": "6 Implementation tools", "subsection": "6.1 Guideline recommendations", "page": 39, "label": "27"},
    "Fig. 5": {"section": "6 Implementation tools", "subsection": "6.2 Drug- and dose-specific protocols", "page": 40, "label": "28"},
    "Fig. 6": {"section": "6 Implementation tools", "subsection": "6.2 Drug- and dose-specific protocols", "page": 41, "label": "29"},
    "Fig. A3.1": {"section": "Annex 3: Treatment outcomes relevant to hypertension", "subsection": "", "page": 55, "label": "43"},
}

# NICE3 Recommendation ID -> Subheading Ground Truth
NICE_REC_SUBHEADINGS = {
    **{f"1.1.{i}": "Identifying people for full formal risk assessment" for i in range(1, 7)},
    **{f"1.1.{i}": "Full formal risk assessment" for i in range(7, 12)},
    **{f"1.1.{i}": "Communication about risk assessment, lifestyle changes and treatment" for i in range(12, 19)},
    "1.2.1": None,
    "1.3.1": "Behaviour change",
    **{f"1.3.{i}": "Cardioprotective diet" for i in range(2, 5)},
    **{f"1.3.{i}": "Physical activity" for i in range(5, 9)},
    "1.3.9": "Weight management",
    "1.3.10": "Alcohol consumption",
    "1.3.11": "Smoking cessation",
    "1.3.12": "Plant stanols and sterols",
    **{f"1.4.{i}": None for i in range(1, 9)},
    **{f"1.5.{i}": "Discuss risks and benefits of statins" for i in range(1, 4)},
    "1.5.4": "Discuss possible interactions between statins and other substances",
    **{f"1.5.{i}": "Perform baseline blood tests and clinical assessment" for i in range(5, 8)},
    "1.5.8": "Choice of drug based on clinical trials",
    "1.5.9": "Statins and pregnancy",
    "1.5.10": "Statins and pregnancy",
    "1.6.1": "Lipid target for people taking statins",
    **{f"1.6.{i}": "Optimising lifestyle changes" for i in range(2, 6)},
    "1.6.6": "Treating comorbidities and secondary causes of dyslipidaemia",
    **{f"1.6.{i}": "Statin treatment for people with and without type 2 diabetes" for i in range(7, 10)},
    **{f"1.6.{i}": "Statin treatment for people with type 1 diabetes" for i in range(10, 13)},
    "1.6.13": "Escalating treatment for people on statins",
    "1.7.1": "Lipid target for people taking lipid-lowering treatments",
    **{f"1.7.{i}": "Initial treatment" for i in range(2, 6)},
    "1.7.6": "Treating comorbidities and secondary causes of dyslipidaemia",
    **{f"1.7.{i}": "Escalating treatment for people on statins" for i in range(7, 11)},
    "1.8.1": None, "1.8.2": None, "1.8.3": None,
    "1.9.1": None, "1.9.2": None, "1.9.3": None, "1.9.4": None,
    "1.10.1": "Primary prevention of cardiovascular disease",
    "1.10.2": "Primary prevention of cardiovascular disease",
    "1.10.3": "Secondary prevention of cardiovascular disease",
    "1.10.4": "Secondary prevention of cardiovascular disease",
    "1.11.1": "When to repeat blood tests",
    "1.11.2": "When to repeat blood tests",
    "1.11.3": "When to measure creatine kinase",
    "1.11.4": "When to measure creatine kinase",
    "1.11.5": "When to measure creatine kinase",
    "1.11.6": "Increase in blood glucose or HbA1c",
    "1.11.7": "Restarting statins",
    **{f"1.11.{i}": "Annual medication review" for i in range(8, 13)},
    "1.12.1": "Adherence to statin treatment",
    "1.12.2": "Fibrates",
    "1.12.3": "Nicotinic acid",
    "1.12.4": "Bile acid sequestrants (anion exchange resins)",
    "1.12.5": "Omega 3 fatty acid compounds",
    "1.12.6": "Omega 3 fatty acid compounds",
    "1.12.7": "Combination treatment",
}

# Section -> Topic map for NICE
NICE_SECTION_TOPICS = {
    "1.1": {"topic": "cardiovascular_risk_assessment", "subtopic": "primary_prevention"},
    "1.2": {"topic": "antiplatelet_therapy", "subtopic": "primary_prevention"},
    "1.3": {"topic": "lifestyle", "subtopic": "primary_and_secondary"},
    "1.4": {"topic": "lipid_assessment", "subtopic": "primary_and_secondary"},
    "1.5": {"topic": "statin_pre_treatment_assessment", "subtopic": "primary_and_secondary"},
    "1.6": {"topic": "lipid_lowering_treatment", "subtopic": "primary_prevention"},
    "1.7": {"topic": "lipid_lowering_treatment", "subtopic": "secondary_prevention"},
    "1.8": {"topic": "lipid_lowering_treatment", "subtopic": "ckd_prevention"},
    "1.9": {"topic": "statin_optimization", "subtopic": "primary_and_secondary"},
    "1.10": {"topic": "statin_intolerance", "subtopic": "primary_and_secondary"},
    "1.11": {"topic": "treatment_monitoring", "subtopic": "primary_and_secondary"},
    "1.12": {"topic": "treatments_not_recommended", "subtopic": "lipid_modification"},
}

# Heading leak patterns to strip from chunk tails (NICE3)
NICE_LEAK_PATTERNS = [
    "Full formal risk assessment",
    "Full formal risk asses sment",
    "Discuss possible interactions between statins and other\nsubstances",
    "Discuss possible interactions between statins and other substances",
    "Treating comorbidities and secondary causes of dyslipidaemia",
    "Optimising statin treatment\nSee the section on optimising statin treatment.",
    "Optimising statin treatment",
    "Assessing response to treatment\nSee the section on assessing response to treatment.",
    "Assessing response to treatment",
    "Increase in blood glucose or HbA1c",
    "Restarting statins",
    "Fibrates",
    "Nicotinic acid",
    "Bile acid sequestrants (anion exchange resins)",
    "Omega 3 fatty acid compounds",
    "Combination treatment",
    "Adherence to statin treatment",
    "Healthy eating\nFor advice on healthy eating, see the NHS eat well guide.",
    "Healthy eating",
    "See the section on optimising statin treatment.",
    "See the section on assessing response to treatment.",
    "For advice on healthy eating, see the NHS eat well guide.",
    "Identifying people for",
    "1.2 Aspirin for",
    "1.3 Lifestyle changes for the primary and",
    "1.6 Lipid-lowering treatment for",
    "1.7 Lipid-lowering treatment for",
    "1.8 Statins for primary and",
]

# R1 Curated orphan mergers
NICE_ORPHAN_MERGES = {
    "NICE3_1.1.1_REC": ["NICE3_1.1_OTH_PRIMARY_PREVENTION_O_001"],
    "NICE3_1.5.5_REC": ["NICE3_1.5_LAB_ALCOHOL_CONSUMPTION_001"],
    "NICE3_1.6.3_REC": ["NICE3_1.6_LIFE_WEIGHT_MANAGEMENT_001"],
    "NICE3_1.1_IMPACT_001": [
        "NICE3_1.1_LIFE_PHYSICAL_ACTIVITY_001",
        "NICE3_1.1_LIFE_ALCOHOL_CONSUMPTION_001",
    ],
    "NICE3_update_info_UPDATE_001": [
        "NICE3_update_info_UPDATE_CARDIOPROTECTIVE_DIE_001",
        "NICE3_update_info_UPDATE_INITIAL_TREATMENT_001",
    ],
}

# R2 Curated date completions
NICE_DATE_COMPLETIONS = {
    "NICE3_1.4.2_REC": "amended December 2023]",
    "NICE3_1.6.3_REC": "physical activity: exercise referral schemes and overweight and\nobesity management.) [May 2023]",
    "NICE3_1.7.2_REC": "amended December 2023]",
    "NICE3_1.8.2_REC": "amended December 2023]",
    "NICE3_1.9.1_REC": "amended December 2023]",
    "NICE3_1.12.5_REC": "amended December 2023]",
}

# WHO Canonical/Duplicate pairs
WHO_CANONICAL_PAIRS = [
    ("WHO03_3.1_REC_001", "WHO03_0_REC_001"),
    ("WHO03_3.1_REC_002", "WHO03_0_REC_002"),
    ("WHO03_3.1_REC_003", "WHO03_0_REC_003"),
    ("WHO03_3.2_REC_001", "WHO03_0_REC_004"),
    ("WHO03_3.3_REC_001", "WHO03_0_REC_005"),
    ("WHO03_3.4_REC_001", "WHO03_0_REC_006"),
    ("WHO03_3.5_REC_001", "WHO03_0_REC_007"),
    ("WHO03_3.6_REC_001", "WHO03_0_REC_008"),
    ("WHO03_3.6_REC_002", "WHO03_0_REC_009"),
    ("WHO03_3.6_REC_003", "WHO03_0_REC_010"),
    ("WHO03_3.7_REC_001", "WHO03_0_REC_011"),
    ("WHO03_3.7_REC_002", "WHO03_0_REC_012"),
    ("WHO03_3.8_REC_001", "WHO03_0_REC_013"),
]

WHO_REMARKS_ENRICHMENT = {
    "WHO03_3.2_REC_001": (
        "\n\nImplementation remarks:\n"
        "• Suggested tests include serum electrolytes and creatinine, lipid panel, HbA1C or fasting glucose, urine dipstick, and electrocardiogram (ECG).\n"
        "• In low-resourced areas or non-clinical settings, where testing may not be possible because of additional costs, and lack of access to laboratories and ECG, treatment should not be delayed, and testing can be done subsequently.\n"
        "• Some medicines, such as long-acting dihydropyridine calcium-channel blockers (CCBs) are more suitable for initiation without testing, compared to diuretics or angiotensin-converting enzyme inhibitors (ACEi)/angiotensin-II receptor blockers (ARBs)."
    ),
    "WHO03_3.3_REC_001": (
        "\n\nImplementation remarks:\n"
        "• Most patients with SBP ≥140 or DBP ≥90 mmHg are high risk and indicated for pharmacological treatment; they do not require cardiovascular (CVD) risk assessment prior to initiating treatment. CVD risk assessment is most important for guiding decisions about initiating pharmacological treatment for hypertension (HTN) in those with lower SBP (130–139 mmHg). It is critical in those with HTN that other risk factors must be identified and treated appropriately to lower total cardiovascular risk.\n"
        "• Many CVD risk-assessment systems are available. In the absence of a calibrated equation for the local population, the choice should depend on resources available, acceptability and feasibility of application.\n"
        "• Whenever risk assessment may threaten timely initiation of HTN treatment and/or patient follow up, it should be postponed and included in the follow-up strategy, rather than taken as a first step to indicate treatment."
    ),
    "WHO03_3.4_REC_001": (
        "\n\nImplementation remarks:\n"
        "• Long-acting antihypertensives are preferred.\n"
        "• Examples of indications to consider specific agents include diuretics or CCBs in patients over 65 years or those of African descent, beta-blockers in ischaemic heart disease, ACEis/ARBs in patients with severe proteinuria, diabetes mellitus, heart failure or kidney disease."
    ),
    "WHO03_3.5_REC_001": (
        "\n\nImplementation remarks:\n"
        "• Combination medication therapy may be especially valuable when the baseline BP is ≥20/10 mmHg higher than the target blood pressure.\n"
        "• Single-pill combination therapy improves medication-taking adherence and persistence and BP control."
    ),
    "WHO03_3.8_REC_001": (
        "\n\nImplementation remarks:\n"
        "• Community health care workers (HCWs) may assist in tasks such as education, delivery of medications, blood pressure (BP) measurement and monitoring through an established collaborative care model. The scope of hypertension care practised by community HCWs depends on local regulations and currently varies by country.\n"
        "• Telemonitoring and community or home-based self-care are encouraged to enhance the control of BP as a part of an integrated management system, when deemed appropriate by the treating medical team and found feasible and affordable by patients.\n"
        "• Physician oversight can be done through innovative methods such as telemonitoring or similar to ensure access to treatment is not delayed."
    ),
}

WHO_METADATA_UPDATES = {
    "WHO03_3.4_REC_001": {
        "drug_class": ["thiazide_or_thiazide_like", "ace_inhibitor", "calcium_channel_blocker", "beta_blocker"],
        "age_group": "65 years",
        "comorbidity": "cardiovascular_disease, diabetes_mellitus, heart_failure, chronic_kidney_disease, ischaemic_heart_disease",
    },
    "WHO03_3.5_REC_001": {
        "bp_threshold": "≥20/10 mmHg higher than target",
    },
    "WHO03_3.8_REC_001": {
        "subtopic": "nonphysician_management",
    },
    "WHO03_5.5_ALGO_001": {
        "section": "6 Implementation tools",
        "subsection": "6.1 Guideline recommendations",
        "pdf_page_start": 38,
        "pdf_page_end": 38,
        "page_label_start": "26",
        "page_label_end": "26",
    },
    "WHO03_6_ALGO_001": {
        "section": "6 Implementation tools",
        "subsection": "",
        "pdf_page_start": 6,
        "pdf_page_end": 6,
        "page_label_start": "iv",
        "page_label_end": "iv",
    },
    "WHO03_6.1_ALGO_001": {
        "section": "6 Implementation tools",
        "subsection": "6.1 Guideline recommendations",
        "pdf_page_start": 39,
        "pdf_page_end": 39,
        "page_label_start": "27",
        "page_label_end": "27",
    },
    "WHO03_6.1_ALGO_002": {
        "section": "6 Implementation tools",
        "subsection": "6.2 Drug- and dose-specific protocols",
        "pdf_page_start": 40,
        "pdf_page_end": 40,
        "page_label_start": "28",
        "page_label_end": "28",
    },
}

WHO_TABLE_CHUNKS_TO_REMOVE = {
    "WHO03_3_TBL_001",
    "WHO03_3.1_TBL_001",
    "WHO03_3.2_TBL_005",
    "WHO03_3.3_TBL_001",
    "WHO03_3.4_TBL_001",
    "WHO03_3.5_TBL_001",
    "WHO03_3.6_TBL_001",
    "WHO03_3.6_TBL_002",
    "WHO03_3.8_TBL_001",
    "WHO03_0_TBL_002",
    "WHO03_0_TBL_003",
    "WHO03_0_TBL_004",
    "WHO03_0_TBL_001",
    "WHO03_0_TBL_017",
    "WHO03_3.2_TBL_002",
    "WHO03_3.2_TBL_003",
    "WHO03_3.2_TBL_004",
}

NICE_CHUNKS_TO_REMOVE = {
    "NICE3_1.7_IMPACT_002",
    "NICE3_1.7_RATIONALE_004",
}

NICE_PAGE_MAP = {
    "NICE3_1.1_OTH_001": (5, 5),
    **{f"NICE3_1.1.{i}_REC": (5, 5) for i in range(1, 8)},
    "NICE3_1.1.8_REC": (6, 6),
    "NICE3_1.1.9_REC": (6, 6),
    "NICE3_1.1.10_REC": (6, 7),
    "NICE3_1.1.11_REC": (7, 7),
    "NICE3_1.1_RATIONALE_001": (8, 9),
    "NICE3_1.1_RATIONALE_002": (9, 9),
    "NICE3_1.1_IMPACT_001": (10, 10),
    "NICE3_1.1_RISK_COMMUNICATION_ABOUT__001": (11, 11),
    "NICE3_1.1.12_REC": (11, 11),
    "NICE3_1.1.13_REC": (11, 11),
    "NICE3_1.1.14_REC": (11, 11),
    "NICE3_1.1.15_REC": (11, 11),
    "NICE3_1.1.16_REC": (11, 12),
    "NICE3_1.1.17_REC": (12, 12),
    "NICE3_1.1.18_REC": (11, 11),
    "NICE3_1.1_RATIONALE_003": (12, 12),
    "NICE3_1.1_IMPACT_002": (13, 13),
    "NICE3_1.2_OTH_001": (14, 14),
    "NICE3_1.2.1_REC": (14, 14),
    "NICE3_1.2_RATIONALE_001": (14, 14),
    "NICE3_1.3_OTH_001": (14, 14),
    "NICE3_1.3.1_REC": (14, 15),
    "NICE3_1.3.2_REC": (15, 15),
    "NICE3_1.3.3_REC": (15, 15),
    "NICE3_1.3.4_REC": (15, 15),
    "NICE3_1.3_RATIONALE_001": (15, 15),
    "NICE3_1.3_IMPACT_001": (15, 15),
    "NICE3_1.3.5_REC": (16, 16),
    "NICE3_1.3.6_REC": (16, 16),
    "NICE3_1.3.7_REC": (16, 17),
    "NICE3_1.3.8_REC": (17, 17),
    "NICE3_1.3.9_REC": (17, 17),
    "NICE3_1.3.10_REC": (17, 17),
    "NICE3_1.3.11_REC": (17, 17),
    "NICE3_1.3.12_REC": (17, 17),
    **{f"NICE3_1.4.{i}_REC": (17, 18) for i in range(1, 7)},
    "NICE3_1.4.7_REC": (18, 18),
    "NICE3_1.4.8_REC": (18, 18),
    "NICE3_1.5_DRUG_001": (18, 18),
    **{f"NICE3_1.5.{i}_REC": (18, 19) for i in range(1, 5)},
    "NICE3_1.5.5_REC": (19, 19),
    "NICE3_1.5.6_REC": (19, 19),
    "NICE3_1.5.7_REC": (20, 20),
    "NICE3_1.5_RATIONALE_001": (20, 20),
    "NICE3_1.5_IMPACT_001": (21, 21),
    "NICE3_1.5.8_REC": (20, 20),
    "NICE3_1.5.9_REC": (20, 20),
    "NICE3_1.5.10_REC": (20, 21),
    "NICE3_1.6_OTH_001": (22, 22),
    "NICE3_1.6_DRUG_PRIMARY_PREVENTION_O_001": (22, 22),
    "NICE3_1.6.1_REC": (22, 22),
    "NICE3_1.6.2_REC": (22, 22),
    "NICE3_1.6.3_REC": (22, 22),
    **{f"NICE3_1.6.{i}_REC": (22, 23) for i in range(4, 9)},
    "NICE3_1.6.9_REC": (23, 23),
    "NICE3_1.6.10_REC": (23, 23),
    "NICE3_1.6.11_REC": (23, 24),
    "NICE3_1.6.12_REC": (24, 24),
    "NICE3_1.6_RATIONALE_001": (24, 25),
    "NICE3_1.6_IMPACT_001": (25, 25),
    "NICE3_1.6.13_REC": (26, 26),
    "NICE3_1.7_OTH_001": (26, 26),
    "NICE3_1.7_DRUG_SECONDARY_PREVENTION_001": (26, 26),
    "NICE3_1.7.1_REC": (26, 26),
    "NICE3_1.7_RATIONALE_001": (27, 28),
    "NICE3_1.7_RATIONALE_002": (28, 28),
    "NICE3_1.7_RATIONALE_003": (29, 29),
    "NICE3_1.7_IMPACT_001": (29, 30),
    "NICE3_1.7.2_REC": (30, 30),
    "NICE3_1.7.3_REC": (30, 30),
    "NICE3_1.7.4_REC": (30, 30),
    "NICE3_1.7.5_REC": (30, 30),
    "NICE3_1.7_RATIONALE_INITIAL_TREATMEN_001": (31, 31),
    "NICE3_1.7_IMPACT_INITIAL_TREATMENT_001": (31, 31),
    "NICE3_1.7.6_REC": (31, 31),
    "NICE3_1.7.7_REC": (31, 32),
    "NICE3_1.7.8_REC": (32, 32),
    "NICE3_1.7.9_REC": (32, 32),
    "NICE3_1.7.10_REC": (32, 32),
    "NICE3_1.8_DRUG_001": (36, 36),
    "NICE3_1.8.1_REC": (36, 36),
    "NICE3_1.8.2_REC": (36, 36),
    "NICE3_1.8.3_REC": (36, 36),
    "NICE3_1.8_OTH_SECONDARY_PREVENTION_001": (36, 36),
    "NICE3_1.9.1_REC": (36, 37),
    "NICE3_1.9.2_REC": (37, 37),
    "NICE3_1.9.3_REC": (37, 37),
    "NICE3_1.9.4_REC": (37, 37),
    "NICE3_1.9_RATIONALE_001": (37, 38),
    "NICE3_1.9_IMPACT_001": (38, 38),
    "NICE3_1.10_CONTRA_001": (38, 38),
    **{f"NICE3_1.10.{i}_REC": (38, 39) for i in range(1, 5)},
    "NICE3_1.10_RATIONALE_001": (40, 40),
    "NICE3_1.10_IMPACT_001": (41, 41),
    "NICE3_1.11_OTH_001": (41, 41),
    "NICE3_1.11.1_REC": (41, 41),
    "NICE3_1.11.2_REC": (41, 41),
    "NICE3_1.11.3_REC": (41, 42),
    "NICE3_1.11.4_REC": (42, 42),
    "NICE3_1.11.5_REC": (42, 42),
    "NICE3_1.11.6_REC": (42, 42),
    "NICE3_1.11.7_REC": (42, 42),
    **{f"NICE3_1.11.{i}_REC": (42, 43) for i in range(8, 12)},
    "NICE3_1.11.12_REC": (43, 43),
    "NICE3_1.11_RATIONALE_001": (43, 44),
    "NICE3_1.11_IMPACT_001": (44, 44),
    "NICE3_1.12_DRUG_001": (44, 44),
    **{f"NICE3_1.12.{i}_REC": (44, 45) for i in range(1, 8)},
    "NICE3_TERM_THIS_SECTION_DEFINES_TERMS_THA_001": (45, 46),
    "NICE3_TERM_FULL_LIPID_PROFILE_THIS_INVOLV_001": (46, 46),
    "NICE3_TERM_SEVERE_MENTAL_ILLNESS_A_DIAGNO_001": (47, 47),
    "NICE3_research_RESEARCH_001": (48, 48),
    "NICE3_research_RATIONALE_001": (49, 49),
    "NICE3_context_CTX_001": (50, 50),
    "NICE3_finding_more_OTH_001": (51, 51),
    "NICE3_update_info_UPDATE_001": (52, 52),
    "NICE3_update_info_UPDATE_CARDIOPROTECTIVE_DIE_001": (52, 52),
    "NICE3_update_info_UPDATE_INITIAL_TREATMENT_001": (52, 52),
}


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

WS_RE = re.compile(r"\s+")
def norm_ws(s: str) -> str:
    return WS_RE.sub("", s)

HDR_RE = re.compile(r"^(?:Section:[^\n]*\n)?(?:Subheading:[^\n]*\n)?(?:Recommendation:[^\n]*\n)?\s*")
def extract_body(fragment: str) -> str:
    return HDR_RE.sub("", fragment, count=1)

def parse_date_bracket(text: str) -> Tuple[Optional[str], List[str]]:
    """Extract (original_date, [amended_dates]) from trailing date bracket in text."""
    matches = list(re.finditer(r"\[([^\]]+)\]", text))
    if not matches:
        return None, []
    raw = matches[-1].group(1).strip()
    raw_norm = re.sub(r"\s+", " ", raw)
    m = re.match(r"^([A-Za-z]+\s+\d{4}|\d{4})(?:[,\s]+amended\s+(.+))?$", raw_norm, re.IGNORECASE)
    if not m:
        return None, []
    orig = m.group(1).strip()
    amended = []
    if m.group(2):
        parts = re.split(r"\s+and\s+|,\s*", m.group(2))
        for p in parts:
            p_clean = p.strip()
            if p_clean:
                amended.append(p_clean)
    return orig, amended

def tail_cut(text: str, pattern: str) -> Tuple[str, bool]:
    """Strip trailing pattern ignoring whitespace differences."""
    t, p = norm_ws(text), norm_ws(pattern)
    if not p or not t.endswith(p):
        return text, False
    i, j = len(text), len(p)
    while i > 0 and j > 0:
        ch = text[i - 1]
        if ch.isspace():
            i -= 1
            continue
        if ch == p[j - 1]:
            i -= 1
            j -= 1
        else:
            break
    while i > 0 and text[i - 1].isspace():
        i -= 1
    return text[:i], True


# ============================================================================
# RULE IMPLEMENTATIONS (R1 -> R13)
# ============================================================================

def apply_r1_truncated_merge(chunks: List[Dict[str, Any]], reporter: FixReporter) -> List[Dict[str, Any]]:
    """
    R1: Detect truncated text and merge orphan continuation fragments.
    """
    by_id = {c["chunk_id"]: c for c in chunks}
    deleted_ids = set()

    for target_id, orphan_ids in NICE_ORPHAN_MERGES.items():
        if target_id not in by_id:
            continue
        target_chunk = by_id[target_id]
        for orphan_id in orphan_ids:
            if orphan_id in by_id and orphan_id not in deleted_ids:
                orphan_chunk = by_id[orphan_id]
                orphan_body = extract_body(orphan_chunk["text"])
                before_snippet = target_chunk["text"]
                sep = " " if not target_chunk["text"].endswith(("\n", " ")) and not orphan_body.startswith(("\n", " ")) else ""
                target_chunk["text"] = target_chunk["text"] + sep + orphan_body
                deleted_ids.add(orphan_id)
                reporter.log(
                    rule_id="R1",
                    chunk_id=target_id,
                    action=f"Merged orphan fragment {orphan_id} into {target_id}",
                    field_name="text",
                    before_snippet=before_snippet,
                    after_snippet=target_chunk["text"],
                )
                reporter.log(
                    rule_id="R1",
                    chunk_id=orphan_id,
                    action=f"Deleted orphan fragment {orphan_id} after merge",
                    field_name="chunk_id",
                    before_snippet=orphan_chunk["text"],
                    after_snippet=None,
                )

    return [c for c in chunks if c["chunk_id"] not in deleted_ids]


def apply_r2_unclosed_date_brackets(chunks: List[Dict[str, Any]], reporter: FixReporter) -> List[Dict[str, Any]]:
    """
    R2: Detect unclosed date brackets and complete them from ground truth / PDF text.
    """
    by_id = {c["chunk_id"]: c for c in chunks}
    
    for cid, suffix in NICE_DATE_COMPLETIONS.items():
        if cid in by_id:
            chunk = by_id[cid]
            text = chunk["text"].rstrip()
            if not text.endswith("]"):
                before = chunk["text"]
                if text.endswith("[2014,") or text.endswith("[May 2023,") or text.endswith("[2008,"):
                    chunk["text"] = text + " " + suffix
                else:
                    sep = " " if not text.endswith(" ") else ""
                    chunk["text"] = text + sep + suffix
                reporter.log(
                    rule_id="R2",
                    chunk_id=cid,
                    action=f"Completed unclosed date bracket with: '{suffix}'",
                    field_name="text",
                    before_snippet=before,
                    after_snippet=chunk["text"],
                )

    return chunks


def apply_r3_heading_leak_strip(chunks: List[Dict[str, Any]], reporter: FixReporter) -> List[Dict[str, Any]]:
    """
    R3: Strip leaked section/subheading titles and running header/footer noise from chunks.
    """
    for chunk in chunks:
        cid = chunk["chunk_id"]
        changed = True
        while changed:
            changed = False
            for pat in NICE_LEAK_PATTERNS:
                new_text, ok = tail_cut(chunk["text"], pat)
                if ok and new_text != chunk["text"]:
                    before = chunk["text"]
                    chunk["text"] = new_text
                    changed = True
                    reporter.log(
                        rule_id="R3",
                        chunk_id=cid,
                        action=f"Stripped leaked heading '{pat[:40]}...'",
                        field_name="text",
                        before_snippet=before,
                        after_snippet=new_text,
                    )

        # Strip any running header/footer leaks
        cleaned_noise = clean_chunk_noise(chunk["text"])
        if cleaned_noise != chunk["text"]:
            before = chunk["text"]
            chunk["text"] = cleaned_noise
            reporter.log(
                rule_id="R3",
                chunk_id=cid,
                action="Stripped running header/footer noise fragment",
                field_name="text",
                before_snippet=before,
                after_snippet=cleaned_noise,
            )

    return chunks


def apply_r10_buried_recommendations_extraction(chunks: List[Dict[str, Any]], reporter: FixReporter) -> List[Dict[str, Any]]:
    """
    R10: Extract buried recommendations from host chunks (e.g. 1.1.12–1.1.17 from 1.1_IMPACT_001, 1.5.8 from 1.5_IMPACT_001).
    """
    by_id = {c["chunk_id"]: c for c in chunks}
    new_chunks = []

    # 1. Extract 1.1.12 - 1.1.17 from NICE3_1.1_IMPACT_001
    host_1_1 = by_id.get("NICE3_1.1_IMPACT_001")
    if host_1_1:
        text = host_1_1["text"]
        rx = re.compile(r"(?m)^(1\.1\.1[2-7])\n")
        matches = list(rx.finditer(text))
        if matches:
            before_host = host_1_1["text"]
            cut_idx = matches[0].start()
            comm_heading_idx = text.rfind("Communication about risk assessment", 0, cut_idx)
            if comm_heading_idx != -1 and cut_idx - comm_heading_idx < 100:
                cut_idx = comm_heading_idx
            host_1_1["text"] = text[:cut_idx].rstrip()
            reporter.log(
                rule_id="R10",
                chunk_id="NICE3_1.1_IMPACT_001",
                action="Extracted buried recommendations 1.1.12–1.1.17 from host",
                field_name="text",
                before_snippet=before_host,
                after_snippet=host_1_1["text"],
            )

            for i, m in enumerate(matches):
                rec_id = m.group(1)
                cid = f"NICE3_{rec_id}_REC"
                if cid in by_id:
                    continue
                start_p = m.start()
                end_p = matches[i + 1].start() if i + 1 < len(matches) else len(text)
                seg = text[start_p:end_p].rstrip()
                
                subheading = NICE_REC_SUBHEADINGS.get(rec_id, "Communication about risk assessment, lifestyle changes and treatment")
                new_c = copy.deepcopy(host_1_1)
                new_c["chunk_id"] = cid
                new_c["text"] = (
                    f"Section: {host_1_1['metadata']['section']}\n"
                    f"Subheading: {subheading}\n"
                    f"Recommendation: {rec_id}\n\n"
                    f"{seg}"
                )
                md = new_c["metadata"]
                md["content_type"] = "recommendation"
                md["recommendation_id"] = rec_id
                md["subsection"] = subheading
                md["clinical_priority"] = 1
                new_chunks.append(new_c)
                by_id[cid] = new_c
                reporter.log(
                    rule_id="R10",
                    chunk_id=cid,
                    action=f"Created standalone recommendation chunk {cid}",
                    field_name="chunk_id",
                    before_snippet=None,
                    after_snippet=new_c["text"],
                )

    # 2. Extract 1.5.8 from NICE3_1.5_IMPACT_001
    host_1_5 = by_id.get("NICE3_1.5_IMPACT_001")
    if host_1_5:
        text = host_1_5["text"]
        rx = re.compile(r"(?m)^(?:Choice of drug based on clinical trials\n)?(1\.5\.8)\n")
        m = rx.search(text)
        if m:
            before_host = host_1_5["text"]
            host_1_5["text"] = text[:m.start()].rstrip()
            reporter.log(
                rule_id="R10",
                chunk_id="NICE3_1.5_IMPACT_001",
                action="Extracted buried recommendation 1.5.8 from host",
                field_name="text",
                before_snippet=before_host,
                after_snippet=host_1_5["text"],
            )

            cid = "NICE3_1.5.8_REC"
            if cid not in by_id:
                seg = text[m.start():].rstrip()
                subheading = "Choice of drug based on clinical trials"
                new_c = copy.deepcopy(host_1_5)
                new_c["chunk_id"] = cid
                new_c["text"] = (
                    f"Section: {host_1_5['metadata']['section']}\n"
                    f"Subheading: {subheading}\n"
                    f"Recommendation: 1.5.8\n\n"
                    f"{seg}"
                )
                md = new_c["metadata"]
                md["content_type"] = "recommendation"
                md["recommendation_id"] = "1.5.8"
                md["subsection"] = subheading
                md["clinical_priority"] = 1
                new_chunks.append(new_c)
                by_id[cid] = new_c
                reporter.log(
                    rule_id="R10",
                    chunk_id=cid,
                    action=f"Created standalone recommendation chunk {cid}",
                    field_name="chunk_id",
                    before_snippet=None,
                    after_snippet=new_c["text"],
                )

    chunks.extend(new_chunks)
    return chunks


def apply_r9_oversized_mixed_split(chunks: List[Dict[str, Any]], reporter: FixReporter) -> List[Dict[str, Any]]:
    """
    R9: Split oversized or mixed recommendation + rationale + impact chunks.
    """
    by_id = {c["chunk_id"]: c for c in chunks}
    new_chunks = []

    # Split NICE3_1.7.10_REC (1469 tokens -> REC + RATIONALE + IMPACT)
    c_1_7_10 = by_id.get("NICE3_1.7.10_REC")
    if c_1_7_10 and ("Why the committee" in c_1_7_10["text"] or "How the recommendations" in c_1_7_10["text"]):
        text = c_1_7_10["text"]
        why_idx = text.find("Why the committee made these recommendations")
        how_idx = text.find("How the recommendations might affect practice")
        if why_idx != -1 and how_idx != -1:
            rec_body = text[:why_idx].rstrip()
            before = c_1_7_10["text"]
            c_1_7_10["text"] = rec_body
            c_1_7_10["metadata"]["requires_manual_review"] = False
            c_1_7_10["metadata"]["review_reason"] = None
            reporter.log(
                rule_id="R9",
                chunk_id="NICE3_1.7.10_REC",
                action="Split oversized mixed chunk: retained pure recommendation text (deduplicated redundant rationale/impact)",
                field_name="text",
                before_snippet=before,
                after_snippet=c_1_7_10["text"],
            )

    # Prune duplicate supporting chunks if present
    chunks[:] = [c for c in chunks if c["chunk_id"] not in NICE_CHUNKS_TO_REMOVE]
    for cid in NICE_CHUNKS_TO_REMOVE:
        if cid in by_id:
            del by_id[cid]

    # Split NICE3_1.1.18_REC (REC + RATIONALE + IMPACT)
    c_1_1_18 = by_id.get("NICE3_1.1.18_REC")
    if c_1_1_18 and ("Why the committee" in c_1_1_18["text"] or "How the recommendations" in c_1_1_18["text"]):
        text = c_1_1_18["text"]
        why_idx = text.find("Why the committee made these recommendations")
        how_idx = text.find("How the recommendations might affect practice")
        if why_idx != -1 and how_idx != -1:
            rec_body = text[:why_idx].rstrip()
            why_body = text[why_idx:how_idx].rstrip()
            how_body = text[how_idx:].rstrip()

            before = c_1_1_18["text"]
            c_1_1_18["text"] = rec_body
            reporter.log(
                rule_id="R9",
                chunk_id="NICE3_1.1.18_REC",
                action="Split mixed chunk: retained pure recommendation text",
                field_name="text",
                before_snippet=before,
                after_snippet=c_1_1_18["text"],
            )

            cid_rat = "NICE3_1.1_RATIONALE_003"
            if cid_rat not in by_id:
                c_rat = copy.deepcopy(c_1_1_18)
                c_rat["chunk_id"] = cid_rat
                c_rat["text"] = (
                    f"Section: {c_1_1_18['metadata']['section']}\n"
                    f"Subheading: {c_1_1_18['metadata']['subsection']}\n\n"
                    f"{why_body}"
                )
                c_rat["metadata"]["content_type"] = "committee_rationale"
                c_rat["metadata"]["clinical_priority"] = 2
                c_rat["metadata"]["parent_recommendation"] = "1.1.18"
                c_rat["metadata"]["recommendation_id"] = None
                new_chunks.append(c_rat)
                by_id[cid_rat] = c_rat
                reporter.log(
                    rule_id="R9",
                    chunk_id=cid_rat,
                    action="Created committee rationale chunk from 1.1.18 split",
                    field_name="chunk_id",
                    before_snippet=None,
                    after_snippet=c_rat["text"],
                )

            cid_imp = "NICE3_1.1_IMPACT_002"
            if cid_imp not in by_id:
                c_imp = copy.deepcopy(c_1_1_18)
                c_imp["chunk_id"] = cid_imp
                c_imp["text"] = (
                    f"Section: {c_1_1_18['metadata']['section']}\n"
                    f"Subheading: {c_1_1_18['metadata']['subsection']}\n\n"
                    f"{how_body}"
                )
                c_imp["metadata"]["content_type"] = "implementation_impact"
                c_imp["metadata"]["clinical_priority"] = 3
                c_imp["metadata"]["parent_recommendation"] = "1.1.18"
                c_imp["metadata"]["recommendation_id"] = None
                new_chunks.append(c_imp)
                by_id[cid_imp] = c_imp
                reporter.log(
                    rule_id="R9",
                    chunk_id=cid_imp,
                    action="Created implementation impact chunk from 1.1.18 split",
                    field_name="chunk_id",
                    before_snippet=None,
                    after_snippet=c_imp["text"],
                )

    # Split NICE3_1.7.5_REC (clean attached rationale/impact)
    c_1_7_5 = by_id.get("NICE3_1.7.5_REC")
    if c_1_7_5 and ("Why the committee" in c_1_7_5["text"] or "How the recommendations" in c_1_7_5["text"]):
        text = c_1_7_5["text"]
        why_idx = text.find("Why the committee made these recommendations")
        if why_idx != -1:
            before = c_1_7_5["text"]
            c_1_7_5["text"] = text[:why_idx].rstrip()
            reporter.log(
                rule_id="R9",
                chunk_id="NICE3_1.7.5_REC",
                action="Split mixed chunk: retained pure recommendation text",
                field_name="text",
                before_snippet=before,
                after_snippet=c_1_7_5["text"],
            )

    chunks.extend(new_chunks)
    return chunks


def apply_r5_who_tables_and_enrichment(chunks: List[Dict[str, Any]], reporter: FixReporter) -> List[Dict[str, Any]]:
    """
    R5: Eliminate recommendation boxes misclassified as tables, enrich canonical recommendations with Implementation remarks.
    """
    by_id = {c["chunk_id"]: c for c in chunks}

    # Enrich canonical Section 3 recommendations with Implementation remarks
    for cid, remarks in WHO_REMARKS_ENRICHMENT.items():
        if cid in by_id and remarks.strip() not in by_id[cid]["text"]:
            before = by_id[cid]["text"]
            by_id[cid]["text"] = by_id[cid]["text"].rstrip() + remarks
            reporter.log(
                rule_id="R5",
                chunk_id=cid,
                action="Enriched canonical recommendation with Implementation remarks",
                field_name="text",
                before_snippet=before,
                after_snippet=by_id[cid]["text"],
            )

    # Remove misclassified / redundant table chunks
    deleted = set()
    for cid in WHO_TABLE_CHUNKS_TO_REMOVE:
        if cid in by_id:
            deleted.add(cid)
            reporter.log(
                rule_id="R5",
                chunk_id=cid,
                action=f"Removed redundant/misclassified table chunk {cid}",
                field_name="chunk_id",
                before_snippet=by_id[cid]["text"],
                after_snippet=None,
            )

    return [c for c in chunks if c["chunk_id"] not in deleted]


def apply_r6_who_section_figure_labels(chunks: List[Dict[str, Any]], reporter: FixReporter) -> List[Dict[str, Any]]:
    """
    R6: Correct algorithm and figure metadata labels.
    """
    by_id = {c["chunk_id"]: c for c in chunks}

    for cid, updates in WHO_METADATA_UPDATES.items():
        if cid in by_id:
            m = by_id[cid]["metadata"]
            for k, v in updates.items():
                if m.get(k) != v:
                    before_val = m.get(k)
                    m[k] = v
                    reporter.log(
                        rule_id="R6",
                        chunk_id=cid,
                        action=f"Updated metadata {k}: {before_val} -> {v}",
                        field_name=k,
                        before_snippet=str(before_val),
                        after_snippet=str(v),
                    )

    return chunks


def apply_r7_who_garbage_micro_chunks(chunks: List[Dict[str, Any]], reporter: FixReporter) -> List[Dict[str, Any]]:
    """
    R7: Detect and drop/merge table or micro chunks with <40 tokens of content or empty pipe grids.
    """
    by_id = {c["chunk_id"]: c for c in chunks}
    deleted = set()

    for chunk in chunks:
        cid = chunk["chunk_id"]
        ct = chunk.get("metadata", {}).get("content_type", "")
        text = chunk.get("text", "").strip()
        if ct == "table":
            clean_text = re.sub(r"[|\-\s:]+", "", text)
            if len(clean_text) < 15 or count_tokens(text) < 40:
                deleted.add(cid)
                reporter.log(
                    rule_id="R7",
                    chunk_id=cid,
                    action=f"Dropped micro/empty table chunk {cid}",
                    field_name="chunk_id",
                    before_snippet=text,
                    after_snippet=None,
                )

    return [c for c in chunks if c["chunk_id"] not in deleted]


def apply_r4_subsection_misassignment(chunks: List[Dict[str, Any]], reporter: FixReporter) -> List[Dict[str, Any]]:
    """
    R4: Overwrite misassigned subsections and correct clinical topics.
    """
    for chunk in chunks:
        cid = chunk["chunk_id"]
        m = chunk["metadata"]
        rec_id = m.get("recommendation_id")

        if rec_id and rec_id in NICE_REC_SUBHEADINGS:
            expected_sub = NICE_REC_SUBHEADINGS[rec_id]
            if m.get("subsection") != expected_sub:
                before_sub = m.get("subsection")
                m["subsection"] = expected_sub
                if "Subheading:" in chunk["text"]:
                    if expected_sub:
                        chunk["text"] = re.sub(r"(?m)^Subheading:[^\n]*$", f"Subheading: {expected_sub}", chunk["text"])
                    else:
                        chunk["text"] = re.sub(r"(?m)^Subheading:[^\n]*\n?", "", chunk["text"])
                elif expected_sub:
                    sec_match = re.search(r"(?m)^Section:[^\n]*\n", chunk["text"])
                    if sec_match:
                        ins_idx = sec_match.end()
                        chunk["text"] = chunk["text"][:ins_idx] + f"Subheading: {expected_sub}\n" + chunk["text"][ins_idx:]

                reporter.log(
                    rule_id="R4",
                    chunk_id=cid,
                    action=f"Corrected subsection for {rec_id}: '{before_sub}' -> '{expected_sub}'",
                    field_name="subsection",
                    before_snippet=str(before_sub),
                    after_snippet=str(expected_sub),
                )

        # Enforce clinical priority hierarchy
        if m.get("is_duplicate"):
            if m.get("clinical_priority") != 2:
                m["clinical_priority"] = 2
        else:
            ct = m.get("content_type", "other")
            if ct in ("recommendation", "drug_guidance", "lifestyle_guidance", "lipid_target", "specialist_referral"):
                if m.get("clinical_priority") != 1:
                    m["clinical_priority"] = 1
            elif ct == "committee_rationale":
                if m.get("clinical_priority") != 2:
                    m["clinical_priority"] = 2
            else:
                if m.get("clinical_priority") not in (2, 3):
                    m["clinical_priority"] = 3

    return chunks


def apply_r8_who_canonical_direction(chunks: List[Dict[str, Any]], reporter: FixReporter) -> List[Dict[str, Any]]:
    """
    R8: Enforce canonicality: Section 3.x is canonical (is_duplicate=False, is_canonical=True, priority=1),
    Executive summary is duplicate (is_duplicate=True, is_canonical=False, priority=2).
    """
    by_id = {c["chunk_id"]: c for c in chunks}

    for can_id, dup_id in WHO_CANONICAL_PAIRS:
        if can_id in by_id:
            can_meta = by_id[can_id]["metadata"]
            if can_meta.get("is_duplicate") is not False or can_meta.get("canonical_chunk_id") is not None or can_meta.get("is_canonical") is not True:
                can_meta["is_duplicate"] = False
                can_meta["is_canonical"] = True
                can_meta["canonical_chunk_id"] = None
                can_meta["clinical_priority"] = 1
                reporter.log(
                    rule_id="R8",
                    chunk_id=can_id,
                    action=f"Set canonical status on {can_id}",
                    field_name="is_duplicate",
                    before_snippet="is_duplicate=True",
                    after_snippet="is_duplicate=False",
                )

        if dup_id in by_id:
            dup_meta = by_id[dup_id]["metadata"]
            if (dup_meta.get("is_duplicate") is not True or 
                dup_meta.get("canonical_chunk_id") != can_id or 
                dup_meta.get("clinical_priority") != 2 or
                dup_meta.get("is_canonical") is not False):
                dup_meta["is_duplicate"] = True
                dup_meta["is_canonical"] = False
                dup_meta["canonical_chunk_id"] = can_id
                dup_meta["clinical_priority"] = 2
                reporter.log(
                    rule_id="R8",
                    chunk_id=dup_id,
                    action=f"Marked {dup_id} as duplicate pointing to canonical {can_id} with priority 2",
                    field_name="canonical_chunk_id",
                    before_snippet=str(dup_meta.get("canonical_chunk_id")),
                    after_snippet=can_id,
                )

    for c in chunks:
        m = c.get("metadata", {})
        m["is_canonical"] = not m.get("is_duplicate", False)

    return chunks


def apply_r11_page_metadata(chunks: List[Dict[str, Any]], pdf_path: Optional[Path], reporter: FixReporter) -> List[Dict[str, Any]]:
    """
    R11: Locate chunks within PDF pages and assign accurate page spans and printed page labels.
    """
    pdf_pages_norm = []
    page_labels = []
    if pdf_path and pdf_path.exists() and fitz:
        doc = fitz.open(str(pdf_path))
        for i, page in enumerate(doc):
            txt = page.get_text()
            norm_txt = norm_ws(re.sub(r"[^a-zA-Z0-9\s]", "", txt.lower()))
            pdf_pages_norm.append(norm_txt)
            lbl = page.get_label()
            page_labels.append(str(lbl) if lbl else str(i + 1))
        doc.close()

    is_who = any("WHO03" in c.get("chunk_id", "") for c in chunks)

    for chunk in chunks:
        cid = chunk["chunk_id"]
        # If chunk is explicitly positioned via WHO_METADATA_UPDATES, skip heuristic search
        if cid in WHO_METADATA_UPDATES and "pdf_page_start" in WHO_METADATA_UPDATES[cid]:
            continue

        m = chunk["metadata"]

        # Check NICE_PAGE_MAP for NICE chunks first
        if not is_who and cid in NICE_PAGE_MAP:
            p_start, p_end = NICE_PAGE_MAP[cid]
            cur_start = m.get("pdf_page_start")
            cur_end = m.get("pdf_page_end")
            m["pdf_page_start"] = p_start
            m["pdf_page_end"] = p_end
            if page_labels and 1 <= p_start <= len(page_labels) and 1 <= p_end <= len(page_labels):
                pl_start = page_labels[p_start - 1]
                pl_end = page_labels[p_end - 1]
                if "printed_page_start" in m or "printed_page_end" in m:
                    m["printed_page_start"] = pl_start
                    m["printed_page_end"] = pl_end
                if "page_label_start" in m or "page_label_end" in m:
                    m["page_label_start"] = pl_start
                    m["page_label_end"] = pl_end
            if cur_start != p_start or cur_end != p_end:
                reporter.log(
                    rule_id="R11",
                    chunk_id=cid,
                    action=f"Updated PDF page span via ground truth: ({cur_start}, {cur_end}) -> ({p_start}, {p_end})",
                    field_name="pdf_page_start",
                    before_snippet=f"{cur_start}-{cur_end}",
                    after_snippet=f"{p_start}-{p_end}",
                )
            continue

        text = chunk["text"]
        # Extract substantive lines (ignoring generic headers)
        subs = []
        for line in text.split("\n"):
            stripped = line.strip()
            if not stripped:
                continue
            if any(stripped.startswith(pfx) for pfx in [
                "Section:", "Subheading:", "Recommendation:", "Definition:",
                "Table:", "Figure:", "Why the committee made", "How the recommendations might affect",
                "Rationale and impact", "Terms used in this guideline", "Recommendations for research"
            ]):
                continue
            norm = norm_ws(stripped)
            if len(norm) >= 20:
                subs.append(norm)

        if not subs:
            subs = [norm_ws(l) for l in text.split("\n") if len(norm_ws(l)) >= 15]

        start_page = None
        end_page = None

        if pdf_pages_norm:
            search_start_idx = 0
            search_end_idx = len(pdf_pages_norm)
            if is_who and "Executive summary" not in m.get("section", "") and "0_" not in cid:
                search_start_idx = 12

            matched_pages = []
            for norm_line in subs:
                key = norm_line[:40]
                for p_idx in range(search_start_idx, search_end_idx):
                    if key in pdf_pages_norm[p_idx]:
                        if (p_idx + 1) not in matched_pages:
                            matched_pages.append(p_idx + 1)

            if matched_pages:
                start_page = min(matched_pages)
                end_page = max(matched_pages)

        if start_page and not end_page:
            end_page = start_page
        if end_page and not start_page:
            start_page = end_page
        if start_page and end_page and end_page < start_page:
            end_page = start_page

        if start_page and end_page:
            cur_start = m.get("pdf_page_start")
            cur_end = m.get("pdf_page_end")
            if cur_start != start_page or cur_end != end_page:
                m["pdf_page_start"] = start_page
                m["pdf_page_end"] = end_page
                reporter.log(
                    rule_id="R11",
                    chunk_id=cid,
                    action=f"Updated PDF page span: ({cur_start}, {cur_end}) -> ({start_page}, {end_page})",
                    field_name="pdf_page_start",
                    before_snippet=f"{cur_start}-{cur_end}",
                    after_snippet=f"{start_page}-{end_page}",
                )

            if page_labels and 1 <= start_page <= len(page_labels) and 1 <= end_page <= len(page_labels):
                pl_start = page_labels[start_page - 1]
                pl_end = page_labels[end_page - 1]
                if "printed_page_start" in m or "printed_page_end" in m:
                    m["printed_page_start"] = pl_start
                    m["printed_page_end"] = pl_end
                if "page_label_start" in m or "page_label_end" in m:
                    m["page_label_start"] = pl_start
                    m["page_label_end"] = pl_end

    return chunks


def apply_r12_date_metadata(chunks: List[Dict[str, Any]], reporter: FixReporter) -> List[Dict[str, Any]]:
    """
    R12: Ensure recommendation_original_date and recommendation_amended_dates match text date bracket.
    """
    for chunk in chunks:
        cid = chunk["chunk_id"]
        m = chunk["metadata"]
        text = chunk["text"]

        orig_date, amended_dates = parse_date_bracket(text)
        if orig_date is not None:
            cur_orig = m.get("recommendation_original_date")
            cur_amend = m.get("recommendation_amended_dates", [])
            cur_orig_norm = re.sub(r"\s+", " ", cur_orig).strip() if cur_orig else None
            
            if cur_orig_norm != orig_date:
                m["recommendation_original_date"] = orig_date
                reporter.log(
                    rule_id="R12",
                    chunk_id=cid,
                    action=f"Updated recommendation_original_date: '{cur_orig}' -> '{orig_date}'",
                    field_name="recommendation_original_date",
                    before_snippet=str(cur_orig),
                    after_snippet=orig_date,
                )
            if cur_amend != amended_dates:
                m["recommendation_amended_dates"] = amended_dates
                reporter.log(
                    rule_id="R12",
                    chunk_id=cid,
                    action=f"Updated recommendation_amended_dates: {cur_amend} -> {amended_dates}",
                    field_name="recommendation_amended_dates",
                    before_snippet=str(cur_amend),
                    after_snippet=str(amended_dates),
                )

    return chunks


def apply_r13_token_recount(chunks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    R13 / P5: Recompute token_count (top-level AND metadata) using tiktoken cl100k_base.
    """
    for chunk in chunks:
        n = count_tokens(chunk["text"])
        chunk["token_count"] = n
        if isinstance(chunk.get("metadata"), dict):
            chunk["metadata"]["token_count"] = n
            if n > 1000 and not chunk["metadata"].get("requires_manual_review"):
                chunk["metadata"]["requires_manual_review"] = True
                chunk["metadata"]["review_reason"] = "oversized chunk (>1000 tokens)"
    return chunks


# ============================================================================
# MASTER REPAIR PIPELINE (WORKFLOW W2)
# ============================================================================

def fix_guideline_chunks(
    chunks: List[Dict[str, Any]],
    pdf_path: Optional[Path],
    reporter: FixReporter,
) -> List[Dict[str, Any]]:
    """
    Execute fixes in exact specified order:
    R1 -> R2 -> R3 -> R10 -> R9 -> R5 -> R6 -> R7 -> R4 -> R8 -> R11 -> R12 -> R13
    """
    chunks = apply_r1_truncated_merge(chunks, reporter)
    chunks = apply_r2_unclosed_date_brackets(chunks, reporter)
    chunks = apply_r3_heading_leak_strip(chunks, reporter)
    chunks = apply_r10_buried_recommendations_extraction(chunks, reporter)
    chunks = apply_r9_oversized_mixed_split(chunks, reporter)
    chunks = apply_r5_who_tables_and_enrichment(chunks, reporter)
    chunks = apply_r6_who_section_figure_labels(chunks, reporter)
    chunks = apply_r7_who_garbage_micro_chunks(chunks, reporter)
    chunks = apply_r4_subsection_misassignment(chunks, reporter)
    chunks = apply_r8_who_canonical_direction(chunks, reporter)
    chunks = apply_r11_page_metadata(chunks, pdf_path, reporter)
    chunks = apply_r12_date_metadata(chunks, reporter)
    chunks = apply_r13_token_recount(chunks)

    return chunks


# ============================================================================
# VALIDATION GATES V1–V6 (WORKFLOW W3)
# ============================================================================

def validate_gates(nice_chunks: List[Dict[str, Any]], who_chunks: List[Dict[str, Any]]):
    """
    Run validation gates V1–V6. Fails loudly with AssertionError if any gate fails.
    """
    all_chunks = nice_chunks + who_chunks

    # V1: No chunk ends mid-sentence, with an unclosed bracket, or with a leaked heading line.
    for c in all_chunks:
        cid = c["chunk_id"]
        text = c["text"].rstrip()

        if cid.endswith("_REC") or c.get("metadata", {}).get("content_type") == "recommendation":
            assert text.count("[") == text.count("]"), f"Gate V1 Failed: Unclosed bracket in {cid}"

        for pat in NICE_LEAK_PATTERNS:
            assert not norm_ws(text).endswith(norm_ws(pat)), f"Gate V1 Failed: Leaked heading '{pat}' in {cid}"

        assert not text.endswith((",", "•", "• ")), f"Gate V1 Failed: Dangling trailing connector in {cid}"

    # V2: No Executive-summary chunk is canonical; no duplicate chunk_ids; no orphan continuation chunks remain.
    for dataset, name in [(nice_chunks, "NICE3"), (who_chunks, "WHO03")]:
        ids = [c["chunk_id"] for c in dataset]
        assert len(ids) == len(set(ids)), f"Gate V2 Failed: Duplicate chunk IDs in {name}"

    for c in who_chunks:
        cid = c["chunk_id"]
        sec = c.get("metadata", {}).get("section", "")
        if "Executive summary" in sec:
            assert c["metadata"].get("is_duplicate") is True, f"Gate V2 Failed: Executive summary chunk {cid} is marked canonical!"
            assert c["metadata"].get("canonical_chunk_id") is not None, f"Gate V2 Failed: Duplicate chunk {cid} has no canonical_chunk_id"

    all_ids = {c["chunk_id"] for c in all_chunks}
    for orphans in NICE_ORPHAN_MERGES.values():
        for orphan in orphans:
            assert orphan not in all_ids, f"Gate V2 Failed: Orphan chunk {orphan} still present!"

    # V3: Every "N. RECOMMENDATION" text lives in a chunk whose subsection number == N (for recommendations).
    for c in all_chunks:
        cid = c["chunk_id"]
        ct = c.get("metadata", {}).get("content_type", "")
        if ct != "recommendation":
            continue
        m = c.get("metadata", {})
        rec_m = re.search(r"^\s*(\d+)\.\s*RECOMMENDATION", c["text"], re.MULTILINE | re.IGNORECASE)
        if rec_m:
            rec_n = rec_m.group(1)
            sub = m.get("subsection", "")
            if sub:
                assert f"3.{rec_n}" in sub or f"{rec_n}." in sub or sub.startswith(rec_n), f"Gate V3 Failed: Rec {rec_n} in wrong subsection {sub} for {cid}"

    # V4: No content_type=="table" chunk matches ^\d+\.\s*RECOMMENDATION ON; no micro/garbage table chunks.
    for c in all_chunks:
        cid = c["chunk_id"]
        ct = c.get("metadata", {}).get("content_type", "")
        if ct == "table":
            assert not re.search(r"^\s*\d+\.\s*RECOMMENDATION ON", c["text"], re.MULTILINE | re.IGNORECASE), f"Gate V4 Failed: Recommendation table {cid} not reclassified/removed"
            assert c.get("token_count", 0) >= 30, f"Gate V4 Failed: Micro table {cid} has <30 tokens"

    # V5: No token_count>1000 without requires_manual_review=true.
    for c in all_chunks:
        cid = c["chunk_id"]
        tok = c.get("token_count", 0)
        if tok > 1000:
            assert c.get("metadata", {}).get("requires_manual_review") is True, f"Gate V5 Failed: Oversized chunk {cid} ({tok} tokens) without requires_manual_review=true"

    # V6: Metadata schema check (is_canonical present and boolean, is_canonical == not is_duplicate)
    for c in all_chunks:
        cid = c["chunk_id"]
        m = c.get("metadata", {})
        assert "is_canonical" in m and isinstance(m["is_canonical"], bool), f"Gate V6 Failed: {cid} missing is_canonical bool"
        assert m["is_canonical"] == (not m.get("is_duplicate", False)), f"Gate V6 Failed: {cid} is_canonical must equal (not is_duplicate)"

    # V7: No running header/footer contamination
    for c in all_chunks:
        cid = c["chunk_id"]
        t = c["text"]
        for pat_str in [
            r"GUIDELINE\s+FOR\s+THE\s+PHARMACOLOGICAL\s+TREATMENT\s+OF\s+HYPERTENSION\s+IN\s+ADULTS",
            r"GUIDELINE\s+FOR\s+T\b",
            r"Cardiovascular\s+disease:\s*risk\s+assessment\s+and\s+reduction,\s*including\s+lipid\s+modification",
            r"conditions#notice-of-rights",
        ]:
            assert not re.search(pat_str, t, re.IGNORECASE), f"Gate V7 Failed: Noise pattern '{pat_str}' in {cid}"


# ============================================================================
# EXPORT HELPERS
# ============================================================================

def write_json(chunks: List[Dict[str, Any]], path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(chunks, ensure_ascii=False, indent=2), encoding="utf-8")

def write_jsonl(chunks: List[Dict[str, Any]], path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        for c in chunks:
            f.write(json.dumps(c, ensure_ascii=False) + "\n")

def write_preview_md(chunks: List[Dict[str, Any]], path: Path, title: str):
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        f"# {title} Chunks Preview",
        f"\n**Total chunks:** {len(chunks)}",
        "\n---",
    ]
    for c in chunks:
        meta = c.get("metadata", {})
        cid = c.get("chunk_id", "")
        lines.append(f"\n\n## {cid}\n")

        p_start = meta.get("pdf_page_start")
        p_end = meta.get("pdf_page_end")
        if p_start is not None and p_end is not None:
            lines.append(f"**PDF Page:** {p_start}" if p_start == p_end else f"**PDF Pages:** {p_start}–{p_end}\n")

        lbl_start = meta.get("printed_page_start") or meta.get("page_label_start")
        lbl_end = meta.get("printed_page_end") or meta.get("page_label_end")
        if lbl_start:
            lines.append(f"**Printed page:** {lbl_start}" if lbl_start == lbl_end or not lbl_end else f"**Printed pages:** {lbl_start}–{lbl_end}\n")

        if meta.get("section"):
            lines.append(f"**Section:** {meta['section']}\n")
        if meta.get("subsection"):
            lines.append(f"**Subsection:** {meta['subsection']}\n")
        if meta.get("recommendation_id"):
            lines.append(f"**Recommendation:** {meta['recommendation_id']}\n")
        if meta.get("recommendation_original_date"):
            lines.append(f"**Date:** {meta['recommendation_original_date']}\n")
        if meta.get("recommendation_amended_dates"):
            lines.append(f"**Amended dates:** {', '.join(meta['recommendation_amended_dates'])}\n")
        if meta.get("topic"):
            lines.append(f"**Topic:** {meta['topic']}\n")
        if meta.get("content_type"):
            lines.append(f"**Type:** {meta['content_type']}\n")
        if meta.get("clinical_priority") is not None:
            lines.append(f"**Priority:** {meta['clinical_priority']}\n")
        if meta.get("is_duplicate"):
            lines.append(f"**⚠️ DUPLICATE of:** {meta.get('canonical_chunk_id')}\n")

        lines.append(f"**Tokens:** {c.get('token_count', 0)}\n")
        lines.append("\n### Text\n\n")
        lines.append(c.get("text", "") + "\n")
        lines.append("\n---")

    path.write_text("\n".join(lines), encoding="utf-8")


# ============================================================================
# CLI MAIN
# ============================================================================

def main():
    parser = argparse.ArgumentParser(description="Fix chunking defects in NICE3 and WHO03 guideline JSONs.")
    parser.add_argument("--nice", default="data/processed/nice3_chunks.json", help="Path to nice3_chunks.json")
    parser.add_argument("--who",  default="data/processed/who03_chunks.json", help="Path to who03_chunks.json")
    parser.add_argument("--nice-pdf", default="data/raw/NICE_2023.pdf", help="Path to NICE_2023.pdf")
    parser.add_argument("--who-pdf",  default="data/raw/WHO_2021.pdf",  help="Path to WHO_2021.pdf")
    parser.add_argument("--report", default="fix_report.json", help="Path to fix_report.json output")
    args = parser.parse_args()

    nice_path = Path(args.nice)
    who_path = Path(args.who)
    nice_pdf = Path(args.nice_pdf)
    who_pdf = Path(args.who_pdf)
    report_path = Path(args.report)

    reporter = FixReporter()
    nice_fixed = []
    who_fixed = []

    nice_bak = nice_path.with_suffix(".json.bak")
    if nice_bak.exists():
        nice_chunks = json.loads(nice_bak.read_text(encoding="utf-8"))
    elif nice_path.exists():
        shutil.copy2(nice_path, nice_bak)
        nice_chunks = json.loads(nice_path.read_text(encoding="utf-8"))
    else:
        nice_chunks = []

    if nice_chunks:
        nice_fixed = fix_guideline_chunks(nice_chunks, nice_pdf, reporter)
        fixed_path = nice_path.parent / (nice_path.stem + ".fixed.json")
        write_json(nice_fixed, fixed_path)
        write_json(nice_fixed, nice_path)
        write_jsonl(nice_fixed, nice_path.with_suffix(".jsonl"))
        write_preview_md(nice_fixed, nice_path.parent / "nice3_chunks_preview.md", "NICE3")

    who_bak = who_path.with_suffix(".json.bak")
    if who_bak.exists():
        who_chunks = json.loads(who_bak.read_text(encoding="utf-8"))
    elif who_path.exists():
        shutil.copy2(who_path, who_bak)
        who_chunks = json.loads(who_path.read_text(encoding="utf-8"))
    else:
        who_chunks = []

    if who_chunks:
        who_fixed = fix_guideline_chunks(who_chunks, who_pdf, reporter)
        fixed_path = who_path.parent / (who_path.stem + ".fixed.json")
        write_json(who_fixed, fixed_path)
        write_json(who_fixed, who_path)
        write_jsonl(who_fixed, who_path.with_suffix(".jsonl"))
        write_preview_md(who_fixed, who_path.parent / "who03_chunks_preview.md", "WHO03")

    report_entries = reporter.to_dict_list()
    write_json(report_entries, report_path)
    if report_path != Path("data/processed/fix_report.json"):
        write_json(report_entries, Path("data/processed/fix_report.json"))

    print(f"=== FIX CHUNKS COMPLETE ===")
    print(f"Total mutations logged: {len(reporter)}")
    print(f"NICE3 chunks: {len(nice_fixed)}")
    print(f"WHO03 chunks: {len(who_fixed)}")
    print(f"Fix report saved to: {report_path}")

    # Validate Gates V1-V5
    validate_gates(nice_fixed, who_fixed)
    print("[OK] All validation gates (V1–V5) passed!")

    # Test idempotency (Gate V6)
    reporter_idempotent = FixReporter()
    nice_run2 = fix_guideline_chunks(copy.deepcopy(nice_fixed), nice_pdf, reporter_idempotent)
    who_run2 = fix_guideline_chunks(copy.deepcopy(who_fixed), who_pdf, reporter_idempotent)
    assert len(reporter_idempotent) == 0, f"Gate V6 Failed: Second run generated {len(reporter_idempotent)} changes!"
    print("[OK] Idempotency gate (V6) verified: second run produces 0 changes.")


if __name__ == "__main__":
    main()
