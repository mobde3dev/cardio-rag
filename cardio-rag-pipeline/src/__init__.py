"""
CardioRAG — Clinical Guideline PDF Parsing & Semantic Chunking System.

A clean, modular architecture for parsing, segmenting, chunking, and enriching
cardiovascular and hypertension clinical guidelines (WHO 2021 & NICE NG238 2023).

Modules:
    parsers         - Low-level PDF layout and font metadata extraction
    segmenters      - Section boundary detection & clinical block parsing
    chunkers        - Guideline-aware semantic chunking engines
    enrichers       - Medical entity extraction & structured metadata
    postprocessors  - Idempotent chunk validation, repair, and patching
    pipelines       - End-to-end processing pipelines for each guideline
    core            - Text cleaning, normalization, and deduplication utilities
    pipeline        - Unified CLI orchestrator
"""

def run_cli():
    """Entry point for CLI execution."""
    from .pipeline import main
    return main()

__all__ = ["run_cli"]
