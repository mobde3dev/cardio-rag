"""
test_fix_rules.py — Comprehensive unit and integration test suite for fix_chunks.py.

Tests detection and fix for each of the 13 rules (R1–R13) using the designated fixtures:
  - R1: Truncated text + orphan fragment merge
  - R2: Unclosed date bracket completion
  - R3: Heading leak strip (tail)
  - R4: Subsection misassignment
  - R5: Recommendation box misclassified as table (WHO)
  - R6: Off-by-one section/figure labels (WHO)
  - R7: Garbage / micro chunks (WHO)
  - R8: Canonical direction for duplicates (WHO)
  - R9: Oversized / mixed chunk split
  - R10: Buried recommendations extraction
  - R11: Per-chunk page metadata
  - R12: Date metadata consistency
  - R13: Token recount
  - V1–V6: Validation gates
"""

import os
import json
import copy
import pytest
from pathlib import Path

from src.postprocessors.fixer import (
    FixReporter,
    count_tokens,
    apply_r1_truncated_merge,
    apply_r2_unclosed_date_brackets,
    apply_r3_heading_leak_strip,
    apply_r4_subsection_misassignment,
    apply_r5_who_tables_and_enrichment,
    apply_r6_who_section_figure_labels,
    apply_r7_who_garbage_micro_chunks,
    apply_r8_who_canonical_direction,
    apply_r9_oversized_mixed_split,
    apply_r10_buried_recommendations_extraction,
    apply_r11_page_metadata,
    apply_r12_date_metadata,
    apply_r13_token_recount,
    fix_guideline_chunks,
    validate_gates,
    parse_date_bracket,
    tail_cut,
    NICE_ORPHAN_MERGES,
    NICE_DATE_COMPLETIONS,
    NICE_LEAK_PATTERNS,
    NICE_REC_SUBHEADINGS,
    WHO_CANONICAL_PAIRS,
    WHO_METADATA_UPDATES,
)

PROJECT_ROOT = Path(__file__).resolve().parent.parent
NICE_RAW_JSON = PROJECT_ROOT / "data" / "processed" / "NICE_2023_chunks.json"
WHO_RAW_JSON = PROJECT_ROOT / "data" / "processed" / "WHO_2021_chunks.json"
NICE_PDF = PROJECT_ROOT / "data" / "raw" / "NICE_2023.pdf"
WHO_PDF = PROJECT_ROOT / "data" / "raw" / "WHO_2021.pdf"


@pytest.fixture
def raw_nice_chunks():
    path = NICE_RAW_JSON
    return json.loads(path.read_text(encoding="utf-8"))


@pytest.fixture
def raw_who_chunks():
    path = WHO_RAW_JSON
    return json.loads(path.read_text(encoding="utf-8"))


@pytest.fixture
def fixed_nice_chunks(raw_nice_chunks):
    rep = FixReporter()
    return fix_guideline_chunks(copy.deepcopy(raw_nice_chunks), NICE_PDF, rep)


@pytest.fixture
def fixed_who_chunks(raw_who_chunks):
    rep = FixReporter()
    return fix_guideline_chunks(copy.deepcopy(raw_who_chunks), WHO_PDF, rep)


# ============================================================================
# R1: TRUNCATED TEXT + ORPHAN FRAGMENT MERGE TESTS
# ============================================================================

class TestR1_TruncatedMerge:
    def test_r1_fixture_1_1_1_merge(self, raw_nice_chunks):
        rep = FixReporter()
        chunks = copy.deepcopy(raw_nice_chunks)
        chunks = apply_r1_truncated_merge(chunks, rep)
        by_id = {c["chunk_id"]: c for c in chunks}

        assert "NICE3_1.1_OTH_PRIMARY_PREVENTION_O_001" not in by_id
        assert "NICE3_1.1.1_REC" in by_id
        rec_text = by_id["NICE3_1.1.1_REC"]["text"]
        assert "primary prevention of cardiovascular disease" in rec_text
        assert "[2008, amended 2014]" in rec_text

    def test_r1_fixture_1_5_5_merge(self, raw_nice_chunks):
        rep = FixReporter()
        chunks = copy.deepcopy(raw_nice_chunks)
        chunks = apply_r1_truncated_merge(chunks, rep)
        by_id = {c["chunk_id"]: c for c in chunks}

        assert "NICE3_1.5_LAB_ALCOHOL_CONSUMPTION_001" not in by_id
        assert "NICE3_1.5.5_REC" in by_id
        rec_text = by_id["NICE3_1.5.5_REC"]["text"]
        assert "alcohol consumption" in rec_text
        assert "[May 2023, amended December 2023]" in rec_text

    def test_r1_fixture_1_6_3_merge(self, raw_nice_chunks):
        rep = FixReporter()
        chunks = copy.deepcopy(raw_nice_chunks)
        chunks = apply_r1_truncated_merge(chunks, rep)
        by_id = {c["chunk_id"]: c for c in chunks}

        assert "NICE3_1.6_LIFE_WEIGHT_MANAGEMENT_001" not in by_id
        assert "NICE3_1.6.3_REC" in by_id
        text_norm = " ".join(by_id["NICE3_1.6.3_REC"]["text"].lower().split())
        assert "weight management services" in text_norm

    def test_r1_fixture_1_1_impact_merge(self):
        rep = FixReporter()
        chunks = [
            {"chunk_id": "NICE3_1.1_IMPACT_001", "text": "Base impact text.\n", "metadata": {}},
            {"chunk_id": "NICE3_1.1_LIFE_PHYSICAL_ACTIVITY_001", "text": "physical activity, smoking", "metadata": {}},
            {"chunk_id": "NICE3_1.1_LIFE_ALCOHOL_CONSUMPTION_001", "text": "and alcohol consumption", "metadata": {}},
        ]
        chunks = apply_r1_truncated_merge(chunks, rep)
        by_id = {c["chunk_id"]: c for c in chunks}

        assert "NICE3_1.1_LIFE_PHYSICAL_ACTIVITY_001" not in by_id
        assert "NICE3_1.1_LIFE_ALCOHOL_CONSUMPTION_001" not in by_id
        assert "NICE3_1.1_IMPACT_001" in by_id
        impact_text = by_id["NICE3_1.1_IMPACT_001"]["text"]
        assert "physical activity, smoking and alcohol consumption" in impact_text.replace("\n", " ")


# ============================================================================
# R2: UNCLOSED DATE BRACKET COMPLETION TESTS
# ============================================================================

class TestR2_UnclosedDateBracket:
    @pytest.mark.parametrize("cid,expected_suffix", [
        ("NICE3_1.4.2_REC", "[2014, amended December 2023]"),
        ("NICE3_1.7.2_REC", "[May 2023, amended December 2023]"),
        ("NICE3_1.8.2_REC", "[May 2023, amended December 2023]"),
        ("NICE3_1.9.1_REC", "[May 2023, amended December 2023]"),
        ("NICE3_1.12.5_REC", "[2014, amended December 2023]"),
    ])
    def test_r2_unclosed_date_completion(self, raw_nice_chunks, cid, expected_suffix):
        rep = FixReporter()
        chunks = copy.deepcopy(raw_nice_chunks)
        chunks = apply_r2_unclosed_date_brackets(chunks, rep)
        by_id = {c["chunk_id"]: c for c in chunks}

        assert cid in by_id
        text = by_id[cid]["text"].strip()
        assert text.endswith("]")
        assert expected_suffix in text

    def test_r2_1_6_3_completion_post_r1(self, raw_nice_chunks):
        rep = FixReporter()
        chunks = copy.deepcopy(raw_nice_chunks)
        chunks = apply_r1_truncated_merge(chunks, rep)
        chunks = apply_r2_unclosed_date_brackets(chunks, rep)
        by_id = {c["chunk_id"]: c for c in chunks}

        assert "NICE3_1.6.3_REC" in by_id
        assert by_id["NICE3_1.6.3_REC"]["text"].strip().endswith("[May 2023]")


# ============================================================================
# R3: HEADING LEAK STRIP TESTS
# ============================================================================

class TestR3_HeadingLeakStrip:
    @pytest.mark.parametrize("cid,leaked_heading", [
        ("NICE3_1.1.6_REC", "Full formal risk assessment"),
        ("NICE3_1.5.3_REC", "Discuss possible interactions between statins and other substances"),
        ("NICE3_1.6.5_REC", "Treating comorbidities and secondary causes of dyslipidaemia"),
        ("NICE3_1.7.6_REC", "Optimising statin treatment"),
        ("NICE3_1.8.3_REC", "Assessing response to treatment"),
        ("NICE3_1.11.5_REC", "Increase in blood glucose or HbA1c"),
        ("NICE3_1.11.6_REC", "Restarting statins"),
        ("NICE3_1.12.1_REC", "Fibrates"),
        ("NICE3_1.12.2_REC", "Nicotinic acid"),
        ("NICE3_1.12.3_REC", "Bile acid sequestrants (anion exchange resins)"),
        ("NICE3_1.12.4_REC", "Omega 3 fatty acid compounds"),
        ("NICE3_1.12.6_REC", "Combination treatment"),
        ("NICE3_1.12_DRUG_001", "Adherence to statin treatment"),
        ("NICE3_1.3.1_REC", "Healthy eating"),
    ])
    def test_r3_heading_leaks_stripped(self, raw_nice_chunks, cid, leaked_heading):
        rep = FixReporter()
        chunks = copy.deepcopy(raw_nice_chunks)
        chunks = apply_r3_heading_leak_strip(chunks, rep)
        by_id = {c["chunk_id"]: c for c in chunks}

        assert cid in by_id
        tail = by_id[cid]["text"].strip().split("\n")[-1]
        assert leaked_heading not in tail


# ============================================================================
# R4: SUBSECTION MISASSIGNMENT TESTS
# ============================================================================

class TestR4_SubsectionMisassignment:
    @pytest.mark.parametrize("cid,expected_sub", [
        ("NICE3_1.1.1_REC", "Identifying people for full formal risk assessment"),
        ("NICE3_1.5.6_REC", "Perform baseline blood tests and clinical assessment"),
        ("NICE3_1.5.7_REC", "Perform baseline blood tests and clinical assessment"),
        ("NICE3_1.6.4_REC", "Optimising lifestyle changes"),
        ("NICE3_1.6.5_REC", "Optimising lifestyle changes"),
        ("NICE3_1.6.6_REC", "Treating comorbidities and secondary causes of dyslipidaemia"),
        ("NICE3_1.11.6_REC", "Increase in blood glucose or HbA1c"),
        ("NICE3_1.11.7_REC", "Restarting statins"),
        ("NICE3_1.3.1_REC", "Behaviour change"),
        ("NICE3_1.8.1_REC", None),
        ("NICE3_1.8.2_REC", None),
        ("NICE3_1.8.3_REC", None),
    ])
    def test_r4_subsection_corrections(self, raw_nice_chunks, cid, expected_sub):
        rep = FixReporter()
        chunks = copy.deepcopy(raw_nice_chunks)
        chunks = apply_r4_subsection_misassignment(chunks, rep)
        by_id = {c["chunk_id"]: c for c in chunks}

        assert cid in by_id
        assert by_id[cid]["metadata"]["subsection"] == expected_sub


# ============================================================================
# R5: RECOMMENDATION BOX AS TABLE RECLASSIFICATION (WHO)
# ============================================================================

class TestR5_RecommendationTableReclassification:
    def test_r5_no_recommendation_tables_remain(self, raw_who_chunks):
        rep = FixReporter()
        chunks = copy.deepcopy(raw_who_chunks)
        chunks = apply_r5_who_tables_and_enrichment(chunks, rep)
        by_id = {c["chunk_id"]: c for c in chunks}

        # Check redundant table chunks removed
        for tbl_id in ["WHO03_3_TBL_001", "WHO03_3.1_TBL_001", "WHO03_3.3_TBL_001", "WHO03_0_TBL_002"]:
            assert tbl_id not in by_id

        # Check canonical recommendations enriched with implementation remarks
        assert "WHO03_3.4_REC_001" in by_id
        assert "Implementation remarks:" in by_id["WHO03_3.4_REC_001"]["text"]
        assert "Long-acting antihypertensives are preferred." in by_id["WHO03_3.4_REC_001"]["text"]


# ============================================================================
# R6: OFF-BY-ONE SECTION & FIGURE LABELS (WHO)
# ============================================================================

class TestR6_SectionFigureLabels:
    def test_r6_algorithm_labels(self, raw_who_chunks):
        rep = FixReporter()
        chunks = copy.deepcopy(raw_who_chunks)
        if not any(c["chunk_id"] == "WHO03_5.5_ALGO_001" for c in chunks):
            chunks.append({
                "chunk_id": "WHO03_5.5_ALGO_001",
                "text": "Figure 1: Treatment algorithm for hypertension",
                "metadata": {"section": "5.5", "subsection": "", "pdf_page_start": 38, "page_label_start": "26"}
            })
        chunks = apply_r6_who_section_figure_labels(chunks, rep)
        by_id = {c["chunk_id"]: c for c in chunks}

        # WHO03_5.5_ALGO_001 -> section 6.1, page 38, label 26
        assert "WHO03_5.5_ALGO_001" in by_id
        m_5_5 = by_id["WHO03_5.5_ALGO_001"]["metadata"]
        assert m_5_5["section"] == "6 Implementation tools"
        assert m_5_5["subsection"] == "6.1 Guideline recommendations"
        assert m_5_5["pdf_page_start"] == 38
        assert m_5_5["page_label_start"] == "26"

        # WHO03_6_ALGO_001 -> page_label "iv"
        if "WHO03_6_ALGO_001" in by_id:
            m_6 = by_id["WHO03_6_ALGO_001"]["metadata"]
            assert m_6["page_label_start"] == "iv"


# ============================================================================
# R7: GARBAGE / MICRO CHUNKS (WHO)
# ============================================================================

class TestR7_GarbageMicroChunks:
    def test_r7_micro_chunks_dropped(self, raw_who_chunks):
        rep = FixReporter()
        # Create a dummy micro table chunk
        micro_c = {
            "chunk_id": "WHO03_TEST_MICRO_TBL",
            "text": "|---|---|\n| | |",
            "token_count": 5,
            "metadata": {"content_type": "table"}
        }
        chunks = [micro_c] + copy.deepcopy(raw_who_chunks)
        chunks = apply_r7_who_garbage_micro_chunks(chunks, rep)
        by_id = {c["chunk_id"]: c for c in chunks}

        assert "WHO03_TEST_MICRO_TBL" not in by_id


# ============================================================================
# R8: CANONICAL DIRECTION FOR DUPLICATES (WHO)
# ============================================================================

class TestR8_CanonicalDirection:
    def test_r8_canonical_direction(self, raw_who_chunks):
        rep = FixReporter()
        chunks = copy.deepcopy(raw_who_chunks)
        chunks = apply_r8_who_canonical_direction(chunks, rep)
        by_id = {c["chunk_id"]: c for c in chunks}

        for can_id, dup_id in WHO_CANONICAL_PAIRS:
            if can_id in by_id:
                assert by_id[can_id]["metadata"]["is_duplicate"] is False
                assert by_id[can_id]["metadata"]["is_canonical"] is True
                assert by_id[can_id]["metadata"]["canonical_chunk_id"] is None
                assert by_id[can_id]["metadata"]["clinical_priority"] == 1
            if dup_id in by_id:
                assert by_id[dup_id]["metadata"]["is_duplicate"] is True
                assert by_id[dup_id]["metadata"]["is_canonical"] is False
                assert by_id[dup_id]["metadata"]["canonical_chunk_id"] == can_id
                assert by_id[dup_id]["metadata"]["clinical_priority"] == 2

        assert by_id["WHO03_3.4_REC_001"]["metadata"]["is_canonical"] is True
        assert by_id["WHO03_3.4_REC_001"]["metadata"]["clinical_priority"] == 1
        assert by_id["WHO03_0_REC_006"]["metadata"]["is_canonical"] is False
        assert by_id["WHO03_0_REC_006"]["metadata"]["is_duplicate"] is True
        assert by_id["WHO03_0_REC_006"]["metadata"]["canonical_chunk_id"] == "WHO03_3.4_REC_001"
        assert by_id["WHO03_0_REC_006"]["metadata"]["clinical_priority"] == 2


# ============================================================================
# R9: OVERSIZED / MIXED CHUNK SPLIT TESTS
# ============================================================================

class TestR9_OversizedMixedSplit:
    def test_r9_fixture_1_7_10_split(self, raw_nice_chunks):
        rep = FixReporter()
        chunks = copy.deepcopy(raw_nice_chunks)
        chunks = apply_r9_oversized_mixed_split(chunks, rep)
        by_id = {c["chunk_id"]: c for c in chunks}

        assert "NICE3_1.7.10_REC" in by_id
        rec_text = by_id["NICE3_1.7.10_REC"]["text"]
        assert "Why the committee" not in rec_text
        assert "How the recommendations" not in rec_text
        assert count_tokens(rec_text) < 200

        # Redundant near-duplicates should not be created
        assert "NICE3_1.7_RATIONALE_004" not in by_id
        assert "NICE3_1.7_IMPACT_002" not in by_id

    def test_r9_fixture_1_1_18_split(self, raw_nice_chunks):
        rep = FixReporter()
        chunks = copy.deepcopy(raw_nice_chunks)
        chunks = apply_r9_oversized_mixed_split(chunks, rep)
        by_id = {c["chunk_id"]: c for c in chunks}

        assert "NICE3_1.1.18_REC" in by_id
        assert "Why the committee" not in by_id["NICE3_1.1.18_REC"]["text"]
        assert "NICE3_1.1_RATIONALE_003" in by_id
        assert "NICE3_1.1_IMPACT_002" in by_id

    def test_r9_fixture_1_7_5_split(self, raw_nice_chunks):
        rep = FixReporter()
        chunks = copy.deepcopy(raw_nice_chunks)
        chunks = apply_r9_oversized_mixed_split(chunks, rep)
        by_id = {c["chunk_id"]: c for c in chunks}

        assert "NICE3_1.7.5_REC" in by_id
        assert "Why the committee" not in by_id["NICE3_1.7.5_REC"]["text"]


# ============================================================================
# R10: BURIED RECOMMENDATIONS EXTRACTION TESTS
# ============================================================================

class TestR10_BuriedRecommendations:
    def test_r10_extract_1_1_12_to_1_1_17(self, raw_nice_chunks):
        rep = FixReporter()
        chunks = copy.deepcopy(raw_nice_chunks)
        chunks = apply_r1_truncated_merge(chunks, rep)
        chunks = apply_r10_buried_recommendations_extraction(chunks, rep)
        by_id = {c["chunk_id"]: c for c in chunks}

        for num in range(12, 18):
            cid = f"NICE3_1.1.{num}_REC"
            assert cid in by_id
            assert by_id[cid]["metadata"]["content_type"] == "recommendation"
            assert by_id[cid]["metadata"]["recommendation_id"] == f"1.1.{num}"
            assert by_id[cid]["metadata"]["clinical_priority"] == 1

        # Host chunk should no longer contain those recommendations
        host = by_id["NICE3_1.1_IMPACT_001"]["text"]
        assert "1.1.12" not in host
        assert "1.1.17" not in host

    def test_r10_extract_1_5_8(self, raw_nice_chunks):
        rep = FixReporter()
        chunks = copy.deepcopy(raw_nice_chunks)
        chunks = apply_r10_buried_recommendations_extraction(chunks, rep)
        by_id = {c["chunk_id"]: c for c in chunks}

        assert "NICE3_1.5.8_REC" in by_id
        assert by_id["NICE3_1.5.8_REC"]["metadata"]["content_type"] == "recommendation"
        assert by_id["NICE3_1.5.8_REC"]["metadata"]["recommendation_id"] == "1.5.8"
        assert "1.5.8" not in by_id["NICE3_1.5_IMPACT_001"]["text"]


# ============================================================================
# R11: PER-CHUNK PAGE METADATA TESTS
# ============================================================================

class TestR11_PageMetadata:
    @pytest.mark.skipif(not NICE_PDF.exists(), reason="NICE3.pdf required")
    def test_r11_pdf_page_spans(self, raw_nice_chunks):
        rep = FixReporter()
        chunks = copy.deepcopy(raw_nice_chunks)
        chunks = apply_r1_truncated_merge(chunks, rep)
        chunks = apply_r11_page_metadata(chunks, NICE_PDF, rep)
        by_id = {c["chunk_id"]: c for c in chunks}

        # Recommendation 1.1.1 is on PDF page 5
        assert by_id["NICE3_1.1.1_REC"]["metadata"]["pdf_page_start"] == 5
        assert by_id["NICE3_1.1.1_REC"]["metadata"]["printed_page_start"] == "5"

        # Recommendation 1.1.8 is on PDF page 6
        assert by_id["NICE3_1.1.8_REC"]["metadata"]["pdf_page_start"] == 6

        # Section 1.7 page provenance verification (must not match page 8 or 10)
        assert by_id["NICE3_1.7.1_REC"]["metadata"]["pdf_page_start"] == 26
        assert by_id["NICE3_1.7_RATIONALE_001"]["metadata"]["pdf_page_start"] == 27
        assert by_id["NICE3_1.7_RATIONALE_002"]["metadata"]["pdf_page_start"] == 28
        assert by_id["NICE3_1.7_RATIONALE_003"]["metadata"]["pdf_page_start"] == 29
        assert by_id["NICE3_1.7_IMPACT_001"]["metadata"]["pdf_page_start"] == 29
        assert by_id["NICE3_1.7.10_REC"]["metadata"]["pdf_page_start"] == 32


# ============================================================================
# R12: DATE METADATA CONSISTENCY TESTS
# ============================================================================

class TestR12_DateConsistency:
    @pytest.mark.parametrize("cid,expected_orig,expected_amend", [
        ("NICE3_1.5.5_REC", "May 2023", ["December 2023"]),
        ("NICE3_1.6.3_REC", "May 2023", []),
        ("NICE3_1.7.2_REC", "May 2023", ["December 2023"]),
        ("NICE3_1.8.2_REC", "May 2023", ["December 2023"]),
        ("NICE3_1.9.1_REC", "May 2023", ["December 2023"]),
        ("NICE3_1.10.1_REC", None, []),
        ("NICE3_1.10.2_REC", None, []),
    ])
    def test_r12_date_metadata(self, raw_nice_chunks, cid, expected_orig, expected_amend):
        rep = FixReporter()
        chunks = copy.deepcopy(raw_nice_chunks)
        chunks = apply_r1_truncated_merge(chunks, rep)
        chunks = apply_r2_unclosed_date_brackets(chunks, rep)
        chunks = apply_r12_date_metadata(chunks, rep)
        by_id = {c["chunk_id"]: c for c in chunks}

        assert cid in by_id
        assert by_id[cid]["metadata"]["recommendation_original_date"] == expected_orig
        assert by_id[cid]["metadata"]["recommendation_amended_dates"] == expected_amend


# ============================================================================
# R13: TOKEN RECOUNT TESTS
# ============================================================================

class TestR13_TokenRecount:
    def test_r13_token_recount_accuracy(self, raw_nice_chunks):
        chunks = copy.deepcopy(raw_nice_chunks)
        chunks = apply_r13_token_recount(chunks)
        for c in chunks:
            expected = count_tokens(c["text"])
            assert c["token_count"] == expected
            assert c["metadata"]["token_count"] == expected


# ============================================================================
# END-TO-END VALIDATION GATES V1–V6
# ============================================================================

class TestValidationGates:
    def test_all_validation_gates_pass(self, fixed_nice_chunks, fixed_who_chunks):
        validate_gates(fixed_nice_chunks, fixed_who_chunks)

    def test_v6_idempotency(self, fixed_nice_chunks, fixed_who_chunks):
        rep = FixReporter()
        nice_run2 = fix_guideline_chunks(copy.deepcopy(fixed_nice_chunks), NICE_PDF, rep)
        who_run2 = fix_guideline_chunks(copy.deepcopy(fixed_who_chunks), WHO_PDF, rep)
        assert len(rep) == 0, f"Fix script mutated {len(rep)} chunks on 2nd run (idempotency failure)!"
