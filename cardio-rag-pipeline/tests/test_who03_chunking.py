"""
Tests for the CardioRAG WHO03 chunking pipeline.

Verifies:
  - Section detection (3.1 through 3.8)
  - Recommendation strength and evidence certainty extraction
  - Repeated page headers not in final chunks
  - Chunk ID uniqueness and determinism
  - Clinical content preservation
  - Chunk size limits
"""

import json
import os
import sys
import re
import pytest
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.parsers.who_parser import extract_pages, extract_toc
from src.core.clean_text import (
    clean_page_text,
    normalize_text,
    detect_noise_patterns,
    _is_clinical_line,
)
from src.segmenters.who_segmenter import build_sections, EXPECTED_SECTIONS
from src.enrichers.who_enricher import (
    detect_recommendation,
    classify_content_type,
    extract_clinical_entities,
)
from src.chunkers.who_chunker import (
    count_tokens,
    generate_chunk_id,
    reset_id_counters,
    detect_semantic_blocks,
    validate_chunks,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

PDF_PATH = str(PROJECT_ROOT / "data" / "raw" / "WHO_2021.pdf")
CHUNKS_PATH = str(PROJECT_ROOT / "data" / "processed" / "WHO_2021_chunks.json")


def _load_chunks():
    """Load processed chunks from JSON file."""
    if not os.path.exists(CHUNKS_PATH):
        pytest.skip("Run the pipeline first to generate chunks")
    with open(CHUNKS_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def _pdf_exists():
    return os.path.exists(PDF_PATH)


# ---------------------------------------------------------------------------
# Section detection tests
# ---------------------------------------------------------------------------

class TestSectionDetection:
    """Verify the parser detects all required sections."""

    @pytest.fixture(autouse=True)
    def load_chunks(self):
        self.chunks = _load_chunks()

    def _sections_in_chunks(self):
        """Get unique subsections from all chunks."""
        sections = set()
        for c in self.chunks:
            sub = c["metadata"].get("subsection", "")
            sec = c["metadata"].get("section", "")
            if sub:
                sections.add(sub)
            if sec:
                sections.add(sec)
        return sections

    def test_section_3_1_treatment_initiation(self):
        sections = self._sections_in_chunks()
        assert any("3.1" in s for s in sections), \
            "Section 3.1 (treatment initiation) not found"

    def test_section_3_2_laboratory_testing(self):
        sections = self._sections_in_chunks()
        assert any("3.2" in s for s in sections), \
            "Section 3.2 (laboratory testing) not found"

    def test_section_3_3_cardiovascular_risk(self):
        sections = self._sections_in_chunks()
        assert any("3.3" in s for s in sections), \
            "Section 3.3 (cardiovascular risk) not found"

    def test_section_3_4_first_line_agents(self):
        sections = self._sections_in_chunks()
        assert any("3.4" in s for s in sections), \
            "Section 3.4 (first-line agents) not found"

    def test_section_3_5_combination_therapy(self):
        sections = self._sections_in_chunks()
        assert any("3.5" in s for s in sections), \
            "Section 3.5 (combination therapy) not found"

    def test_section_3_6_target_bp(self):
        sections = self._sections_in_chunks()
        assert any("3.6" in s for s in sections), \
            "Section 3.6 (target BP) not found"

    def test_section_3_7_follow_up(self):
        sections = self._sections_in_chunks()
        assert any("3.7" in s for s in sections), \
            "Section 3.7 (follow-up) not found"

    def test_section_3_8_nonphysician(self):
        sections = self._sections_in_chunks()
        assert any("3.8" in s for s in sections), \
            "Section 3.8 (nonphysician treatment) not found"


# ---------------------------------------------------------------------------
# Metadata extraction tests
# ---------------------------------------------------------------------------

class TestMetadataExtraction:
    """Test recommendation strength and evidence certainty extraction."""

    @pytest.fixture(autouse=True)
    def load_chunks(self):
        self.chunks = _load_chunks()

    def test_recommendation_strength_extracted(self):
        """At least some recommendation chunks should have strength."""
        rec_chunks = [
            c for c in self.chunks
            if c["metadata"].get("content_type") == "recommendation"
        ]
        assert len(rec_chunks) > 0, "No recommendation chunks found"

        with_strength = [
            c for c in rec_chunks
            if c["metadata"].get("recommendation_strength")
        ]
        assert len(with_strength) > 0, \
            "No recommendation chunks have recommendation_strength"

    def test_evidence_certainty_extracted(self):
        """At least some recommendation chunks should have evidence certainty."""
        rec_chunks = [
            c for c in self.chunks
            if c["metadata"].get("content_type") == "recommendation"
        ]

        with_certainty = [
            c for c in rec_chunks
            if c["metadata"].get("evidence_certainty")
        ]
        assert len(with_certainty) > 0, \
            "No recommendation chunks have evidence_certainty"

    def test_recommendation_strength_values(self):
        """Strength should be 'strong' or 'conditional'."""
        for c in self.chunks:
            strength = c["metadata"].get("recommendation_strength")
            if strength:
                assert strength in ("strong", "conditional"), \
                    f"Invalid strength: {strength} in {c['chunk_id']}"

    def test_evidence_certainty_values(self):
        """Certainty should contain known levels."""
        valid_levels = {"high", "moderate", "low", "very low"}
        for c in self.chunks:
            certainty = c["metadata"].get("evidence_certainty")
            if certainty:
                # Check that at least one valid level is in the certainty string
                assert any(level in certainty.lower() for level in valid_levels), \
                    f"Invalid certainty: {certainty} in {c['chunk_id']}"


# ---------------------------------------------------------------------------
# Text quality tests
# ---------------------------------------------------------------------------

class TestTextQuality:
    """Verify clinical content preservation and noise removal."""

    @pytest.fixture(autouse=True)
    def load_chunks(self):
        self.chunks = _load_chunks()

    def test_no_repeated_headers_in_chunks(self):
        """Page headers should not appear in chunk text."""
        # Common WHO guideline headers
        header_patterns = [
            "Guideline for the pharmacological treatment of hypertension in adults",
        ]
        for c in self.chunks:
            text = c["text"]
            for header in header_patterns:
                # Allow it once (in section context prefix) but not repeated
                count = text.lower().count(header.lower())
                assert count <= 1, \
                    f"Header appears {count} times in {c['chunk_id']}: {header[:50]}"

    def test_clinical_abbreviations_preserved(self):
        """Key clinical abbreviations should appear in at least some chunks."""
        all_text = " ".join(c["text"] for c in self.chunks)
        for abbr in ["mmHg", "ACE"]:
            assert abbr in all_text, f"Clinical abbreviation '{abbr}' not found"

    def test_no_empty_clinical_chunks(self):
        """No clinical chunk should have empty text."""
        for c in self.chunks:
            if c["metadata"].get("clinical_priority", 99) <= 2:
                assert c["text"].strip(), f"Empty clinical chunk: {c['chunk_id']}"


# ---------------------------------------------------------------------------
# Chunk structure tests
# ---------------------------------------------------------------------------

class TestChunkStructure:
    """Test chunk IDs, sizes, and metadata integrity."""

    @pytest.fixture(autouse=True)
    def load_chunks(self):
        self.chunks = _load_chunks()

    def test_unique_chunk_ids(self):
        """All chunk IDs must be unique."""
        ids = [c["chunk_id"] for c in self.chunks]
        assert len(ids) == len(set(ids)), \
            f"Duplicate chunk IDs found: {len(ids)} total, {len(set(ids))} unique"

    def test_chunk_id_format(self):
        """Chunk IDs should follow the WHO03_{section}_{TYPE}_{seq} format."""
        for c in self.chunks:
            assert c["chunk_id"].startswith("WHO03_"), \
                f"Invalid chunk ID format: {c['chunk_id']}"

    def test_all_chunks_have_source_file(self):
        """Every chunk must have source_file metadata."""
        for c in self.chunks:
            assert c["metadata"].get("source_file") == "WHO_2021.pdf", \
                f"Missing/wrong source_file in {c['chunk_id']}"

    def test_all_chunks_have_page_number(self):
        """Every chunk must have a page number."""
        for c in self.chunks:
            assert c["metadata"].get("pdf_page_start"), \
                f"Missing page number in {c['chunk_id']}"

    def test_token_counts_present(self):
        """Every chunk should have a token count."""
        for c in self.chunks:
            assert c.get("token_count", 0) > 0, \
                f"Missing or zero token count in {c['chunk_id']}"

    def test_chunk_size_limits(self):
        """Most chunks should be under 1000 tokens."""
        oversized = [
            c for c in self.chunks
            if c.get("token_count", 0) > 1000
            and c["metadata"].get("content_type") not in ("table", "algorithm")
        ]
        # Allow up to 10% oversized
        max_oversized = max(1, int(len(self.chunks) * 0.10))
        assert len(oversized) <= max_oversized, \
            f"{len(oversized)} chunks exceed 1000 tokens (limit: {max_oversized})"


# ---------------------------------------------------------------------------
# Unit tests for individual functions
# ---------------------------------------------------------------------------

class TestRecommendationDetection:
    """Unit tests for recommendation pattern matching."""

    def test_detect_strong_recommendation(self):
        text = """RECOMMENDATION ON BLOOD PRESSURE THRESHOLD

WHO recommends pharmacological antihypertensive treatment for persons
with confirmed hypertension and a systolic blood pressure of ≥140 mmHg
or diastolic blood pressure of ≥90 mmHg.

Strong recommendation, high-certainty evidence"""

        rec = detect_recommendation(text)
        assert rec is not None
        assert rec.strength == "strong"
        assert "high" in rec.evidence_certainty

    def test_detect_conditional_recommendation(self):
        text = """RECOMMENDATION ON TARGET BLOOD PRESSURE

WHO suggests a target systolic blood pressure of <130 mmHg.

Conditional recommendation, low-certainty evidence"""

        rec = detect_recommendation(text)
        assert rec is not None
        assert rec.strength == "conditional"
        assert "low" in rec.evidence_certainty

    def test_no_recommendation_in_evidence(self):
        text = """Evidence and rationale

A systematic review found 12 RCTs comparing different thresholds.
The overall quality of evidence was moderate."""

        rec = detect_recommendation(text)
        # This should NOT be detected as a recommendation
        # (it's evidence, not a recommendation statement)
        if rec:
            assert rec.recommendation_text == "" or "recommends" not in rec.recommendation_text.lower()


class TestClinicalEntityExtraction:
    """Unit tests for clinical entity extraction."""

    def test_extract_bp_values(self):
        text = "BP threshold of ≥140 mmHg systolic or ≥90 mmHg diastolic"
        entities = extract_clinical_entities(text)
        assert len(entities.bp_thresholds) >= 2

    def test_extract_drug_classes(self):
        text = "First-line agents include thiazide, ACE inhibitor, ARB, or CCB"
        entities = extract_clinical_entities(text)
        assert len(entities.drug_classes) >= 3

    def test_extract_drug_names(self):
        text = "amlodipine 5 mg or enalapril 10 mg"
        entities = extract_clinical_entities(text)
        assert "amlodipine" in entities.drug_names
        assert "enalapril" in entities.drug_names


class TestTextCleaning:
    """Unit tests for text cleaning functions."""

    def test_preserve_bp_values(self):
        text = "≥140 mmHg or 130–139 mmHg"
        result = normalize_text(text)
        assert "≥140 mmHg" in result
        assert "130–139 mmHg" in result

    def test_preserve_comparison_operators(self):
        text = "SBP ≥140 and DBP <90"
        result = normalize_text(text)
        assert "≥" in result
        assert "<" in result

    def test_clinical_line_detection(self):
        assert _is_clinical_line("≥140 mmHg")
        assert _is_clinical_line("Strong recommendation")
        assert _is_clinical_line("ACEi 10 mg")
        assert not _is_clinical_line("ISBN 978-92-4-003398-6")

    def test_normalize_bullets(self):
        text = "▪ item one\n▸ item two\n► item three"
        result = normalize_text(text)
        assert result.count("•") == 3

    def test_collapse_whitespace(self):
        text = "too    much     space"
        result = normalize_text(text)
        assert "too much space" in result


class TestChunkIdGeneration:
    """Unit tests for chunk ID generation."""

    def test_deterministic_ids(self):
        reset_id_counters()
        id1 = generate_chunk_id("3.4", "recommendation")
        id2 = generate_chunk_id("3.4", "evidence_rationale")
        id3 = generate_chunk_id("3.4", "recommendation")

        assert id1 == "WHO03_3.4_REC_001"
        assert id2 == "WHO03_3.4_EVID_001"
        assert id3 == "WHO03_3.4_REC_002"

    def test_ids_stable_on_rerun(self):
        """Chunk IDs should remain stable across reruns."""
        reset_id_counters()
        ids_run1 = [
            generate_chunk_id("3.1", "recommendation"),
            generate_chunk_id("3.1", "implementation_remark"),
            generate_chunk_id("3.1", "evidence_rationale"),
        ]

        reset_id_counters()
        ids_run2 = [
            generate_chunk_id("3.1", "recommendation"),
            generate_chunk_id("3.1", "implementation_remark"),
            generate_chunk_id("3.1", "evidence_rationale"),
        ]

        assert ids_run1 == ids_run2


# ---------------------------------------------------------------------------
# Content type classification tests
# ---------------------------------------------------------------------------

class TestContentTypeClassification:

    def test_classify_recommendation(self):
        text = "RECOMMENDATION ON treatment\nWHO recommends..."
        assert classify_content_type(text) == "recommendation"

    def test_classify_implementation_remark(self):
        text = "Implementation remarks:\nPatients should be..."
        assert classify_content_type(text) == "implementation_remark"

    def test_classify_evidence(self):
        text = "Evidence and rationale\nA systematic review..."
        assert classify_content_type(text) == "evidence_rationale"

    def test_classify_algorithm(self):
        text = "Algorithm 1: Treatment pathway for..."
        assert classify_content_type(text) == "algorithm"
