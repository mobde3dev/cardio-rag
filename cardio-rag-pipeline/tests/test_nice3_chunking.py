"""
Automated unit and integration test suite for CardioRAG NICE3 (NG238) pipeline.

Tests:
  - Date parsing (§62)
  - Section definitions and detection (§60)
  - Recommendation ID format & detection (§55, §61)
  - Metadata extraction & schemas (§45)
  - Pipeline execution & chunk validation (§53, §54)
"""

import os
import pytest
from pathlib import Path

from src.segmenters.nice_rec_parser import (
    parse_date_marker,
    find_date_markers,
    validate_recommendation_id,
    extract_cross_references,
    extract_technology_appraisals,
    NiceRecommendation,
)
from src.segmenters.nice_segmenter import (
    NICE_SECTION_DEFS,
    get_topic_for_section,
    get_prevention_type,
)
from src.enrichers.nice_enricher import (
    classify_content_type,
    determine_clinical_priority,
    extract_populations,
    extract_risk_assessment_meta,
    extract_lipid_metadata,
    extract_drug_metadata,
)
from src.postprocessors.validator import validate_nice3_chunks
from src.chunkers.nice_chunker import NiceChunk

PROJECT_ROOT = Path(__file__).resolve().parent.parent


# ---------------------------------------------------------------------------
# Date Parsing Tests (§62)
# ---------------------------------------------------------------------------

class TestDateParsing:
    def test_single_month_year(self):
        orig, amended = parse_date_marker("May 2023")
        assert orig == "May 2023"
        assert amended == []

    def test_single_month_year_december(self):
        orig, amended = parse_date_marker("December 2023")
        assert orig == "December 2023"
        assert amended == []

    def test_year_only(self):
        orig, amended = parse_date_marker("2008")
        assert orig == "2008"
        assert amended == []

    def test_single_amendment(self):
        orig, amended = parse_date_marker("May 2023, amended December 2023")
        assert orig == "May 2023"
        assert amended == ["December 2023"]

    def test_multiple_amendments(self):
        orig, amended = parse_date_marker("2014, amended May 2023 and December 2023")
        assert orig == "2014"
        assert amended == ["May 2023", "December 2023"]

    def test_find_date_markers_in_text(self):
        text = "Offer atorvastatin 20 mg for primary prevention. [May 2023]\nAnother statement [2008, amended 2014]"
        markers = find_date_markers(text)
        assert len(markers) == 2
        assert markers[0][2] == "May 2023"
        assert markers[1][2] == "2008"
        assert markers[1][3] == ["2014"]


# ---------------------------------------------------------------------------
# Recommendation ID Tests (§55, §61)
# ---------------------------------------------------------------------------

class TestRecommendationIDs:
    def test_valid_recommendation_ids(self):
        valid_ids = [
            "1.1.7", "1.2.1", "1.3.2", "1.4.5", "1.5.5",
            "1.6.7", "1.7.1", "1.7.2", "1.8.1", "1.9.2",
            "1.10.3", "1.11.1", "1.12.1"
        ]
        for rid in valid_ids:
            assert validate_recommendation_id(rid) is True, f"Failed for {rid}"

    def test_invalid_recommendation_ids(self):
        invalid_ids = ["1.1.03", "10.3", "2.1.1", "1.13.1", "1.0.1", "abc", "1.1."]
        for rid in invalid_ids:
            assert validate_recommendation_id(rid) is False, f"Should be invalid for {rid}"

    def test_cross_reference_extraction(self):
        text = "For secondary prevention, see recommendation 1.7.1 and recommendations 1.9.2 and 1.9.3."
        refs = extract_cross_references(text)
        assert "1.7.1" in refs
        assert "1.9.2" in refs
        assert "1.9.3" in refs


# ---------------------------------------------------------------------------
# Technology Appraisal Extraction (§17)
# ---------------------------------------------------------------------------

class TestTechnologyAppraisal:
    def test_ta_extraction(self):
        text = "Refer to NICE technology appraisal guidance TA385, TA393, TA394, TA694 and TA733."
        tas = extract_technology_appraisals(text)
        assert "TA385" in tas
        assert "TA393" in tas
        assert "TA394" in tas
        assert "TA694" in tas
        assert "TA733" in tas


# ---------------------------------------------------------------------------
# Section and Clinical Topic Mapping Tests (§60)
# ---------------------------------------------------------------------------

class TestSectionMapping:
    def test_all_12_sections_defined(self):
        expected_sections = [
            "1.1", "1.2", "1.3", "1.4", "1.5", "1.6",
            "1.7", "1.8", "1.9", "1.10", "1.11", "1.12",
        ]
        defined_ids = [sec[0] for sec in NICE_SECTION_DEFS]
        for sec in expected_sections:
            assert sec in defined_ids, f"Section {sec} missing from definitions"

    def test_prevention_type_mapping(self):
        assert get_prevention_type("1.1") == "primary"
        assert get_prevention_type("1.2") == "primary"
        assert get_prevention_type("1.3") == "primary_and_secondary"
        assert get_prevention_type("1.6") == "primary"
        assert get_prevention_type("1.7") == "secondary"
        assert get_prevention_type("1.8") == "primary_and_secondary"

    def test_topic_mapping(self):
        assert get_topic_for_section("1.1")["topic"] == "cardiovascular_risk_assessment"
        assert get_topic_for_section("1.2")["topic"] == "antiplatelet_therapy"
        assert get_topic_for_section("1.3")["topic"] == "lifestyle"
        assert get_topic_for_section("1.4")["topic"] == "lipid_assessment"
        assert get_topic_for_section("1.5")["topic"] == "statin_pre_treatment_assessment"
        assert get_topic_for_section("1.6")["topic"] == "lipid_lowering_treatment"
        assert get_topic_for_section("1.7")["topic"] == "lipid_lowering_treatment"
        assert get_topic_for_section("1.8")["topic"] == "lipid_lowering_treatment"
        assert get_topic_for_section("1.9")["topic"] == "statin_optimization"
        assert get_topic_for_section("1.10")["topic"] == "statin_intolerance"
        assert get_topic_for_section("1.11")["topic"] == "treatment_monitoring"
        assert get_topic_for_section("1.12")["topic"] == "treatments_not_recommended"


# ---------------------------------------------------------------------------
# Metadata Extraction Tests
# ---------------------------------------------------------------------------

class TestMetadataExtraction:
    def test_clinical_priority(self):
        assert determine_clinical_priority("recommendation") == 1
        assert determine_clinical_priority("drug_guidance") == 1
        assert determine_clinical_priority("lipid_target") == 1
        assert determine_clinical_priority("specialist_referral") == 1
        assert determine_clinical_priority("committee_rationale") == 2
        assert determine_clinical_priority("implementation_impact") == 3
        assert determine_clinical_priority("research_recommendation") == 3
        assert determine_clinical_priority("update_information") == 3

    def test_population_extraction(self):
        text = "For people with chronic kidney disease (CKD) and adults without established CVD."
        pops = extract_populations(text)
        assert "people_with_ckd" in pops
        assert "people_without_established_cvd" in pops

    def test_risk_meta(self):
        text = "Use QRISK3 score with a 10-year risk horizon and QRISK3 score of 10% for adults aged 25 to 84 years."
        meta = extract_risk_assessment_meta(text)
        assert meta["risk_tool"] == "QRISK3"
        assert meta["risk_threshold"] == "10%"
        assert meta["risk_horizon"] == "10 years"
        assert meta["age_min"] == 25
        assert meta["age_max"] == 84

    def test_lipid_target(self):
        text = "Aim for LDL cholesterol levels of 2.0 mmol per litre or less, or non-HDL cholesterol levels of 2.6 mmol per litre or less."
        meta = extract_lipid_metadata(text)
        assert "LDL" in meta["lipid_measure"]
        assert "non-HDL" in meta["lipid_measure"]

    def test_drug_dose_extraction(self):
        text = "Offer atorvastatin 20 mg for primary prevention or atorvastatin 80 mg for secondary prevention with ezetimibe."
        meta = extract_drug_metadata(text)
        assert "atorvastatin" in meta["drug_names"]
        assert "ezetimibe" in meta["drug_names"]
        assert "20 mg" in meta["dose"] or meta["dose"] == ["20 mg", "80 mg"]


# ---------------------------------------------------------------------------
# Validation Engine Tests (§53)
# ---------------------------------------------------------------------------

class TestValidationEngine:
    def test_validation_detects_duplicate_id(self):
        c1 = NiceChunk(chunk_id="DUP_01", text="Text 1", metadata={"pdf_page_start": 1})
        c2 = NiceChunk(chunk_id="DUP_01", text="Text 2", metadata={"pdf_page_start": 2})
        report = validate_nice3_chunks([c1, c2], total_pdf_pages=50)
        assert report.is_valid is False
        assert any("Duplicate chunk ID" in e for e in report.errors)

    def test_validation_detects_invalid_priority_for_research(self):
        c = NiceChunk(
            chunk_id="RESEARCH_01",
            text="Research recommendation",
            metadata={
                "pdf_page_start": 1,
                "content_type": "research_recommendation",
                "clinical_priority": 1,  # INVALID: must not be 1
            }
        )
        report = validate_nice3_chunks([c], total_pdf_pages=50)
        assert report.is_valid is False
        assert any("Research recommendation must not be clinical priority 1" in e for e in report.errors)


# ---------------------------------------------------------------------------
# End-to-End Pipeline Output Verification (if PDF present)
# ---------------------------------------------------------------------------

class TestPipelineOutputs:
    @pytest.mark.skipif(
        not os.path.exists(str(PROJECT_ROOT / "data" / "raw" / "NICE_2023.pdf")),
        reason="NICE_2023.pdf raw file required for integration test"
    )
    def test_pipeline_execution(self):
        from src.pipelines.nice_pipeline import run_nice_pipeline

        chunks, stats = run_nice_pipeline()

        assert len(chunks) > 20
        assert stats["direct_recommendations"] > 0
        assert stats["total_pdf_pages"] > 0
        assert stats["validation_errors"] == 0

        # Verify output files exist
        assert os.path.exists(str(PROJECT_ROOT / "data" / "processed" / "NICE_2023_chunks.json"))
        assert os.path.exists(str(PROJECT_ROOT / "data" / "processed" / "NICE_2023_chunks.jsonl"))
        assert os.path.exists(str(PROJECT_ROOT / "data" / "processed" / "NICE_2023_chunks_preview.md"))
        assert os.path.exists(str(PROJECT_ROOT / "data" / "processed" / "NICE_2023_processing_report.json"))
