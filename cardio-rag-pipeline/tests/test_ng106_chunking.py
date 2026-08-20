"""
Unit and integration tests for NICE NG106 (Chronic Heart Failure) chunking and enrichment.
"""

import json
import os
import pytest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
CHUNKS_PATH = PROJECT_ROOT / "data" / "processed" / "NICE_NG106_chunks.json"


@pytest.fixture(scope="module")
def ng106_chunks():
    if not CHUNKS_PATH.exists():
        from src.pipelines.ng106_pipeline import run_ng106_pipeline
        chunks, _ = run_ng106_pipeline()
        return chunks
    with open(CHUNKS_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


class TestNg106Extraction:
    def test_chunk_count(self, ng106_chunks):
        assert len(ng106_chunks) >= 91, f"Expected at least 91 chunks, got {len(ng106_chunks)}"

    def test_all_major_recommendations_present(self, ng106_chunks):
        rec_ids = {c["metadata"]["recommendation_id"] for c in ng106_chunks if c["metadata"].get("recommendation_id")}
        essential_recs = [
            "1.1.1", "1.1.8", "1.2.1", "1.2.5", "1.4.1", "1.4.2", "1.4.5",
            "1.5.1", "1.6.1", "1.7.1", "1.7.3", "1.8.1", "1.9.1", "1.10.3",
            "1.11.1", "1.12.1", "1.12.5"
        ]
        for erec in essential_recs:
            assert erec in rec_ids, f"Recommendation {erec} missing from NG106 extractions"

    def test_provenance_and_token_bounds(self, ng106_chunks):
        for c in ng106_chunks:
            meta = c["metadata"]
            assert 1 <= meta["pdf_page_start"] <= 39, f"Invalid start page in {c['chunk_id']}"
            assert 1 <= meta["pdf_page_end"] <= 39, f"Invalid end page in {c['chunk_id']}"
            assert meta["pdf_page_start"] <= meta["pdf_page_end"]
            assert 15 <= c["token_count"] <= 2000, f"Token count out of bounds in {c['chunk_id']}: {c['token_count']}"

    def test_heart_failure_clinical_enrichment(self, ng106_chunks):
        by_id = {c["chunk_id"]: c for c in ng106_chunks}

        # 1.2.5 should mention NT-proBNP or BNP
        rec_1_2_5 = by_id.get("NG106_1.2.5_REC")
        assert rec_1_2_5 is not None
        assert "NT_proBNP" in rec_1_2_5["metadata"]["clinical_metadata"]["biomarkers_detected"] or \
               "BNP" in rec_1_2_5["metadata"]["clinical_metadata"]["biomarkers_detected"]

        # 1.4.1 should detect ACE inhibitors or ARBs
        rec_1_4_1 = by_id.get("NG106_1.4.1_REC")
        assert rec_1_4_1 is not None
        assert "ACE_inhibitors" in rec_1_4_1["metadata"]["clinical_metadata"]["drug_classes"] or \
               "beta_blockers" in rec_1_4_1["metadata"]["clinical_metadata"]["drug_classes"]
