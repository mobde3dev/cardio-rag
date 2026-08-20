#!/usr/bin/env python3
"""
patch_chunks.py — Direct repair and synchronization for nice3_chunks.json and who03_chunks.json.

Operations:
 NICE3:
  1) Merge orphan fragments into parent recommendations (and remove fragment chunks).
  2) Complete truncated tails (dates/citations) with curated text from the official PDF.
  3) Strip leaking section and subheading headings from chunk ends.
  4) Extract buried recommendations (1.1.12–1.1.17 and 1.5.8) into standalone recommendation chunks.
  5) Fix page ranges and page labels matching official document pagination.
  6) Correct subsections, date metadata, and enforce clinical priority hierarchy.
  7) Retokenize and regenerate json, jsonl, and markdown preview files.

 WHO03:
  1) Flip duplicate/canonical relationship: Section 3.x recommendations become canonical
     (is_duplicate=False), and Executive Summary recommendations become duplicates (is_duplicate=True).
  2) Enrich canonical Section 3 recommendations with clinical Implementation remarks.
  3) Eliminate recommendation boxes misclassified as tables (e.g. WHO03_3.3_TBL_001),
     preventing section-boundary and topic bugs.
  4) Remove noisy multi-recommendation table spans (WHO03_0_TBL_003) and empty/corrupted table fragments.
  5) Correct algorithm sections, page numbers, and page labels.
  6) Retokenize and regenerate json, jsonl, and markdown preview files.

Usage:
    python patch_chunks.py [--nice data/processed/nice3_chunks.json]
                           [--who  data/processed/who03_chunks.json]
                           [--pdf  data/raw/NICE3.pdf]
"""

import json
import re
import sys
import shutil
import argparse
from pathlib import Path
from typing import List, Dict, Any

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
    from src.clean_text import clean_chunk_noise
except ImportError:
    try:
        from clean_text import clean_chunk_noise
    except ImportError:
        def clean_chunk_noise(t: str) -> str:
            return t

WS = re.compile(r"\s+")
def ws(s: str) -> str:
    return WS.sub("", s)


# ============================================================================
# NICE3 CONFIGURATION & FIXES
# ============================================================================

def tail_cut(text: str, pattern: str):
    """Strip trailing pattern ignoring whitespace differences."""
    t, p = ws(text), ws(pattern)
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

HDR = re.compile(r"^(?:Section:[^\n]*\n)?(?:Subheading:[^\n]*\n)?(?:Recommendation:[^\n]*\n)?\s*")
def body_of(fragment: str) -> str:
    return HDR.sub("", fragment, count=1)

NICE_MERGES = {
    "NICE3_1.1.1_REC":     ["NICE3_1.1_OTH_PRIMARY_PREVENTION_O_001"],
    "NICE3_1.5.5_REC":     ["NICE3_1.5_LAB_ALCOHOL_CONSUMPTION_001"],
    "NICE3_1.6.3_REC":     ["NICE3_1.6_LIFE_WEIGHT_MANAGEMENT_001"],
    "NICE3_1.1_IMPACT_001": ["NICE3_1.1_LIFE_PHYSICAL_ACTIVITY_001",
                             "NICE3_1.1_LIFE_ALCOHOL_CONSUMPTION_001"],
}

NICE_COMPLETIONS = {
    "NICE3_1.4.2_REC":  "amended December 2023]",
    "NICE3_1.6.3_REC":  "physical activity: exercise referral schemes and overweight and\nobesity management.) [May 2023]",
    "NICE3_1.7.2_REC":  "amended December 2023]",
    "NICE3_1.8.2_REC":  "amended December 2023]",
    "NICE3_1.9.1_REC":  "amended December 2023]",
    "NICE3_1.12.5_REC": "amended December 2023]",
}

NICE_LEAK_PATTERNS = [
    "Full formal risk assessment",
    "Discuss possible interactions between statins and other substances",
    "Treating comorbidities and secondary causes of dyslipidaemia",
    "Optimising statin treatment\nSee the section on optimising statin treatment.",
    "Assessing response to treatment\nSee the section on assessing response to treatment.",
    "Increase in blood glucose or HbA1c",
    "Restarting statins",
    "Fibrates",
    "Nicotinic acid",
    "Bile acid sequestrants (anion exchange resins)",
    "Omega 3 fatty acid compounds",
    "Combination treatment",
    "Adherence to statin treatment",
    "Healthy eating\nFor advice on healthy eating, see the NHS eat well guide.",
]

NICE_SPLITS = {
    "NICE3_1.1_IMPACT_001": re.compile(r"(?m)^(1\.1\.1[2-7])\n"),
    "NICE3_1.5_IMPACT_001": re.compile(r"(?m)^(?:Choice of drug based on clinical trials\n)?(1\.5\.8)\n"),
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

NICE_SUBSECTION_FIX = {
    **{f"NICE3_1.1.{i}_REC": "Identifying people for full formal risk assessment" for i in range(1, 7)},
    **{f"NICE3_1.1.{i}_REC": "Full formal risk assessment" for i in range(7, 12)},
    **{f"NICE3_1.1.{i}_REC": "Communication about risk assessment, lifestyle changes and treatment" for i in range(12, 19)},
    "NICE3_1.3.1_REC": "Behaviour change",
    "NICE3_1.5.6_REC": "Perform baseline blood tests and clinical assessment",
    "NICE3_1.5.7_REC": "Perform baseline blood tests and clinical assessment",
    "NICE3_1.6.4_REC": "Optimising lifestyle changes",
    "NICE3_1.6.5_REC": "Optimising lifestyle changes",
    "NICE3_1.6.6_REC": "Treating comorbidities and secondary causes of dyslipidaemia",
    "NICE3_1.11.6_REC": "Increase in blood glucose or HbA1c",
    "NICE3_1.11.7_REC": "Restarting statins",
    "NICE3_1.8.1_REC": None, "NICE3_1.8.2_REC": None, "NICE3_1.8.3_REC": None,
}

NICE_DATE_FIX = {  # (original_date, [amended])
    "NICE3_1.4.2_REC":  ("2014", ["December 2023"]),
    "NICE3_1.5.5_REC":  ("May 2023", ["December 2023"]),
    "NICE3_1.6.3_REC":  ("May 2023", []),
    "NICE3_1.7.2_REC":  ("May 2023", ["December 2023"]),
    "NICE3_1.8.2_REC":  ("May 2023", ["December 2023"]),
    "NICE3_1.9.1_REC":  ("May 2023", ["December 2023"]),
    "NICE3_1.12.5_REC": ("2014", ["December 2023"]),
    "NICE3_1.1.12_REC": ("2014", []), "NICE3_1.1.13_REC": ("2008", ["May 2023"]),
    "NICE3_1.1.14_REC": ("2008", []), "NICE3_1.1.15_REC": ("2008", []),
    "NICE3_1.1.16_REC": ("May 2023", []), "NICE3_1.1.17_REC": ("2008", ["2014"]),
    "NICE3_1.5.8_REC":  ("2008", []),
}

def set_nice_pages(chunk: Dict[str, Any], rng: tuple):
    m = chunk["metadata"]
    m["pdf_page_start"], m["pdf_page_end"] = rng
    m["printed_page_start"], m["printed_page_end"] = str(rng[0]), str(rng[1])


# ============================================================================
# WHO03 CONFIGURATION & FIXES
# ============================================================================

# Full mapping of (Canonical Section 3 Rec, Duplicate Exec Summary Rec)
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

# Section 3 Recommendation Box remarks to integrate directly into canonical recommendations
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
        "page_label_start": "iv",
        "page_label_end": "iv",
    },
}

# Redundant recommendation boxes (which masqueraded as tables with shifted subsections),
# multi-recommendation table blobs, and empty/corrupt table fragments to remove.
WHO_CHUNKS_TO_REMOVE = {
    # Section 3 Recommendation box tables (now consolidated into canonical recs)
    "WHO03_3_TBL_001",
    "WHO03_3.1_TBL_001",
    "WHO03_3.2_TBL_005",
    "WHO03_3.3_TBL_001",  # The notorious Section 3.4 box with 3.3 metadata
    "WHO03_3.4_TBL_001",
    "WHO03_3.5_TBL_001",
    "WHO03_3.6_TBL_001",
    "WHO03_3.8_TBL_001",
    # Exec summary duplicate/multi-spanning tables
    "WHO03_0_TBL_002",
    "WHO03_0_TBL_003",  # Dirty multi-recommendation table span
    "WHO03_0_TBL_004",
    # Empty or noise fragments
    "WHO03_0_TBL_001",
    "WHO03_0_TBL_017",
    "WHO03_3.2_TBL_002",
    "WHO03_3.2_TBL_003",
    "WHO03_3.2_TBL_004",
}


# ============================================================================
# PROCESSING PIPELINES
# ============================================================================

def retokenize(chunk: Dict[str, Any]):
    n = count_tokens(chunk["text"])
    chunk["token_count"] = n
    if isinstance(chunk.get("metadata"), dict):
        chunk["metadata"]["token_count"] = n


def patch_nice(chunks: List[Dict[str, Any]], report: Dict[str, Any]) -> List[Dict[str, Any]]:
    by_id = {c["chunk_id"]: c for c in chunks}

    # 1) Merge orphan fragments
    for target, frags in NICE_MERGES.items():
        if target not in by_id:
            continue
        t = by_id[target]
        for f in frags:
            if f in by_id:
                t["text"] += body_of(by_id.pop(f)["text"])
                report["merged"].append(f)

    # Prune duplicate supporting chunks
    chunks[:] = [c for c in chunks if c["chunk_id"] in by_id and c["chunk_id"] not in NICE_CHUNKS_TO_REMOVE]

    # 2) Complete truncated tails
    for cid, suffix in NICE_COMPLETIONS.items():
        if cid in by_id and not by_id[cid]["text"].rstrip().endswith("]"):
            by_id[cid]["text"] = by_id[cid]["text"].rstrip() + " " + suffix
            report["completed"].append(cid)

    # 3) Strip leaking section/subheading titles and running header/footer noise
    for c in chunks:
        changed = True
        while changed:
            changed = False
            for pat in NICE_LEAK_PATTERNS:
                new_text, ok = tail_cut(c["text"], pat)
                if ok:
                    c["text"] = new_text
                    changed = True
                    report["stripped"].append(c["chunk_id"])

        c["text"] = clean_chunk_noise(c["text"])

    # 4) Extract buried recommendations
    for cid, rx in NICE_SPLITS.items():
        src = by_id.get(cid)
        if not src:
            continue
        orig = src["text"]
        ms = list(rx.finditer(orig))
        if not ms:
            continue
        src["text"] = orig[:ms[0].start()].rstrip()
        for i, m in enumerate(ms):
            seg = orig[m.start(): ms[i+1].start() if i+1 < len(ms) else len(orig)].rstrip()
            rec = m.group(1)
            nc = json.loads(json.dumps(src))
            nc["chunk_id"] = f"NICE3_{rec}_REC"
            nc["text"] = (
                f"Section: {src['metadata']['section']}\n"
                f"Subheading: {NICE_SUBSECTION_FIX.get(nc['chunk_id'], src['metadata'].get('subsection'))}\n"
                f"Recommendation: {rec}\n\n{seg}"
            )
            md = nc["metadata"]
            md["content_type"] = "recommendation"
            md["recommendation_id"] = rec
            md["clinical_priority"] = 1
            chunks.append(nc)
            by_id[nc["chunk_id"]] = nc
            report["split_new"].append(nc["chunk_id"])

    # Clean 1.7.10 pure recommendation text
    if "NICE3_1.7.10_REC" in by_id:
        t = by_id["NICE3_1.7.10_REC"]["text"]
        why_idx = t.find("Why the committee made these recommendations")
        if why_idx != -1:
            by_id["NICE3_1.7.10_REC"]["text"] = t[:why_idx].rstrip()

    # 5) Page numbers, subsections, dates & priority hierarchy
    for c in chunks:
        cid = c["chunk_id"]
        if cid in NICE_PAGE_MAP:
            set_nice_pages(c, NICE_PAGE_MAP[cid])
        if cid in NICE_SUBSECTION_FIX:
            c["metadata"]["subsection"] = NICE_SUBSECTION_FIX[cid]
        if cid in NICE_DATE_FIX:
            o, a = NICE_DATE_FIX[cid]
            c["metadata"]["recommendation_original_date"] = o
            c["metadata"]["recommendation_amended_dates"] = a

        # Enforce canonicality & priority
        c["metadata"]["is_canonical"] = True
        c["metadata"]["is_duplicate"] = False
        c["metadata"]["canonical_chunk_id"] = None

        ct = c["metadata"].get("content_type", "other")
        if ct in ("recommendation", "drug_guidance", "lifestyle_guidance", "lipid_target", "specialist_referral"):
            c["metadata"]["clinical_priority"] = 1
        elif ct == "committee_rationale":
            c["metadata"]["clinical_priority"] = 2
        else:
            c["metadata"]["clinical_priority"] = 3

    for c in chunks:
        retokenize(c)

    return chunks


def patch_who(chunks: List[Dict[str, Any]], report: Dict[str, Any]) -> List[Dict[str, Any]]:
    by_id = {c["chunk_id"]: c for c in chunks}

    # 1) Enrich canonical Section 3 recommendations with Implementation remarks
    for cid, remarks in WHO_REMARKS_ENRICHMENT.items():
        if cid in by_id and remarks not in by_id[cid]["text"]:
            by_id[cid]["text"] = by_id[cid]["text"].rstrip() + remarks
            report["enriched_recs"].append(cid)

    # 2) Apply metadata updates (drug classes, age groups, algorithms)
    for cid, updates in WHO_METADATA_UPDATES.items():
        if cid in by_id:
            by_id[cid]["metadata"].update(updates)
            report["metadata_updated"].append(cid)

    # 3) Flip canonicality: Section 3.x is canonical, Exec Summary is duplicate
    for can_id, dup_id in WHO_CANONICAL_PAIRS:
        if can_id in by_id:
            by_id[can_id]["metadata"]["is_duplicate"] = False
            by_id[can_id]["metadata"]["is_canonical"] = True
            by_id[can_id]["metadata"]["canonical_chunk_id"] = None
            by_id[can_id]["metadata"]["clinical_priority"] = 1
        if dup_id in by_id:
            by_id[dup_id]["metadata"]["is_duplicate"] = True
            by_id[dup_id]["metadata"]["is_canonical"] = False
            by_id[dup_id]["metadata"]["canonical_chunk_id"] = can_id
            by_id[dup_id]["metadata"]["clinical_priority"] = 2
            report["flipped_pairs"].append((can_id, dup_id))

    # 4) Remove pseudo-table recommendation boxes, multi-spanning tables, and noise fragments
    removed_count = 0
    chunks[:] = [c for c in chunks if c["chunk_id"] not in WHO_CHUNKS_TO_REMOVE]
    for cid in WHO_CHUNKS_TO_REMOVE:
        if cid in by_id:
            report["removed_tables"].append(cid)
            removed_count += 1

    # 5) Clean noise & set canonical flags across all WHO chunks
    for c in chunks:
        c["text"] = clean_chunk_noise(c["text"])
        m = c["metadata"]
        m["is_canonical"] = not m.get("is_duplicate", False)
        retokenize(c)

    return chunks


# ============================================================================
# EXPORT HELPERS (.jsonl & _preview.md)
# ============================================================================

def write_json(chunks: List[Dict[str, Any]], path: Path):
    path.write_text(json.dumps(chunks, ensure_ascii=False, indent=2), encoding="utf-8")

def write_jsonl(chunks: List[Dict[str, Any]], path: Path):
    with open(path, "w", encoding="utf-8") as f:
        for c in chunks:
            f.write(json.dumps(c, ensure_ascii=False) + "\n")

def write_preview_md(chunks: List[Dict[str, Any]], path: Path, title: str):
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
            if p_start == p_end:
                lines.append(f"**Page:** {p_start}\n")
            else:
                lines.append(f"**Pages:** {p_start}–{p_end}\n")

        if meta.get("printed_page_start") or meta.get("page_label_start"):
            lbl_start = meta.get("printed_page_start") or meta.get("page_label_start")
            lbl_end = meta.get("printed_page_end") or meta.get("page_label_end")
            if lbl_start == lbl_end or not lbl_end:
                lines.append(f"**Printed page:** {lbl_start}\n")
            else:
                lines.append(f"**Printed pages:** {lbl_start}–{lbl_end}\n")

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
        if meta.get("subtopic"):
            lines.append(f"**Subtopic:** {meta['subtopic']}\n")
        if meta.get("content_type"):
            lines.append(f"**Type:** {meta['content_type']}\n")
        if meta.get("recommendation_strength"):
            lines.append(f"**Strength:** {meta['recommendation_strength']}\n")
        if meta.get("evidence_certainty"):
            lines.append(f"**Evidence certainty:** {meta['evidence_certainty']}\n")
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
# VALIDATION
# ============================================================================

def validate_all(nice_chunks: List[Dict[str, Any]], who_chunks: List[Dict[str, Any]]):
    if nice_chunks:
        nice_ids = [c["chunk_id"] for c in nice_chunks]
        assert len(nice_ids) == len(set(nice_ids)), "Duplicate chunk IDs in NICE3!"
        for f in {f for fs in NICE_MERGES.values() for f in fs}:
            assert f not in nice_ids, f"Fragment still present in NICE3: {f}"
        for c in nice_chunks:
            t = c["text"].rstrip()
            assert not any(ws(t).endswith(ws(p)) for p in NICE_LEAK_PATTERNS), f"Leak pattern in {c['chunk_id']}"
            m = c["metadata"]
            assert 1 <= m.get("pdf_page_start", 1) <= m.get("pdf_page_end", 1) <= 52, f"Page out of range: {c['chunk_id']}"
            if c["chunk_id"].endswith("_REC"):
                assert c["text"].count("[") == c["text"].count("]"), f"Unclosed bracket in {c['chunk_id']}"

    if who_chunks:
        who_ids = [c["chunk_id"] for c in who_chunks]
        assert len(who_ids) == len(set(who_ids)), "Duplicate chunk IDs in WHO03!"
        for removed_id in WHO_CHUNKS_TO_REMOVE:
            assert removed_id not in who_ids, f"Table {removed_id} was supposed to be removed!"

        by_id = {c["chunk_id"]: c for c in who_chunks}
        # Check canonical flips
        for can_id, dup_id in WHO_CANONICAL_PAIRS:
            if can_id in by_id:
                assert by_id[can_id]["metadata"]["is_duplicate"] is False, f"{can_id} must be canonical!"
                assert by_id[can_id]["metadata"]["canonical_chunk_id"] is None, f"{can_id} canonical_chunk_id must be None!"
            if dup_id in by_id:
                assert by_id[dup_id]["metadata"]["is_duplicate"] is True, f"{dup_id} must be duplicate!"
                assert by_id[dup_id]["metadata"]["canonical_chunk_id"] == can_id, f"{dup_id} must point to {can_id}!"

        # Check WHO03_3.4_REC_001 has remarks
        assert "WHO03_3.4_REC_001" in by_id
        assert "Implementation remarks:" in by_id["WHO03_3.4_REC_001"]["text"]
        assert "beta_blocker" in by_id["WHO03_3.4_REC_001"]["metadata"]["drug_class"]


# ============================================================================
# MAIN
# ============================================================================

def main():
    parser = argparse.ArgumentParser(description="Patch NICE3 and WHO03 chunks.")
    parser.add_argument("--nice", default="data/processed/nice3_chunks.json")
    parser.add_argument("--who",  default="data/processed/who03_chunks.json")
    args = parser.parse_args()

    nice_path = Path(args.nice)
    who_path = Path(args.who)

    nice_chunks = []
    who_chunks = []

    if nice_path.exists():
        nice_report = {"merged": [], "completed": [], "stripped": [], "split_new": []}
        nice_chunks = json.loads(nice_path.read_text(encoding="utf-8"))
        nice_chunks = patch_nice(nice_chunks, nice_report)

        # Backup
        shutil.copy2(nice_path, nice_path.with_suffix(".json.bak"))

        # Write json, jsonl, md
        write_json(nice_chunks, nice_path)
        write_jsonl(nice_chunks, nice_path.with_suffix(".jsonl"))
        write_preview_md(nice_chunks, nice_path.parent / "nice3_chunks_preview.md", "NICE3")

        print("=== NICE3 PATCH SUMMARY ===")
        print(f"Final chunk count: {len(nice_chunks)}")
        print(f"Merged fragments: {len(nice_report['merged'])}")
        print(f"Completed tails: {len(nice_report['completed'])}")
        print(f"Stripped leaks from: {len(set(nice_report['stripped']))} chunks")
        print(f"Extracted new recs: {nice_report['split_new']}")
        print(f"Backup saved to: {nice_path.with_suffix('.json.bak')}")

    if who_path.exists():
        who_report = {"enriched_recs": [], "metadata_updated": [], "flipped_pairs": [], "removed_tables": []}
        who_chunks = json.loads(who_path.read_text(encoding="utf-8"))
        who_chunks = patch_who(who_chunks, who_report)

        # Backup
        shutil.copy2(who_path, who_path.with_suffix(".json.bak"))

        # Write json, jsonl, md
        write_json(who_chunks, who_path)
        write_jsonl(who_chunks, who_path.with_suffix(".jsonl"))
        write_preview_md(who_chunks, who_path.parent / "who03_chunks_preview.md", "WHO03")

        print("\n=== WHO03 PATCH SUMMARY ===")
        print(f"Final chunk count: {len(who_chunks)}")
        print(f"Enriched canonical recommendations: {who_report['enriched_recs']}")
        print(f"Canonical flipped pairs: {len(who_report['flipped_pairs'])}")
        print(f"Removed pseudo-tables & noisy table spans: {len(who_report['removed_tables'])}")
        print(f"Backup saved to: {who_path.with_suffix('.json.bak')}")

    validate_all(nice_chunks, who_chunks)
    print("\n[OK] All validations passed successfully!")


if __name__ == "__main__":
    main()