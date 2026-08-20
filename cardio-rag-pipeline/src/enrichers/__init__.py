"""Enrichers — add structured metadata to chunks."""
from .who_enricher import build_chunk_metadata as build_who_chunk_metadata, classify_content_type as classify_who_content_type
from .nice_enricher import build_nice3_chunk_metadata, classify_content_type as classify_nice_content_type

__all__ = [
    "build_who_chunk_metadata",
    "classify_who_content_type",
    "build_nice3_chunk_metadata",
    "classify_nice_content_type",
]
