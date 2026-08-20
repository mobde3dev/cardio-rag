"""Section segmenters — raw pages to structured sections."""
from .who_segmenter import build_sections as build_who_sections, assign_pages_to_sections as assign_who_pages
from .nice_segmenter import build_nice_sections, assign_pages_to_nice_sections
from .nice_rec_parser import extract_recommendations as extract_nice_recommendations

__all__ = [
    "build_who_sections",
    "assign_who_pages",
    "build_nice_sections",
    "assign_pages_to_nice_sections",
    "extract_nice_recommendations",
]
