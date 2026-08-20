"""
PDF extraction module for CardioRAG.

Uses PyMuPDF (fitz) for text extraction and font/layout metadata,
and pdfplumber for structured table extraction.

Designed so the text-extraction backend can be swapped later.
"""

import os
import re
import logging
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any

import fitz  # PyMuPDF

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class TextSpan:
    """A single span of text with font metadata."""
    text: str
    font: str
    size: float
    flags: int  # bold=16, italic=2, etc.
    bbox: tuple  # (x0, y0, x1, y1)

    @property
    def is_bold(self) -> bool:
        return bool(self.flags & 2**4)

    @property
    def is_italic(self) -> bool:
        return bool(self.flags & 2**1)


@dataclass
class PageData:
    """Extracted data for a single PDF page."""
    pdf_page: int               # 1-based physical page number
    page_label: Optional[str]   # printed page number if detected
    raw_text: str               # plain text extracted by PyMuPDF
    cleaned_text: str = ""      # filled later by clean_text module
    spans: List[TextSpan] = field(default_factory=list)


@dataclass
class TableData:
    """A table extracted from the PDF."""
    pdf_page: int
    table_index: int
    headers: List[str]
    rows: List[List[str]]
    markdown: str = ""
    caption: str = ""


@dataclass
class TocEntry:
    """An entry from the PDF Table of Contents."""
    level: int
    title: str
    page: int  # 1-based


@dataclass
class FigureInfo:
    """Metadata about a detected figure / algorithm page."""
    pdf_page: int
    figure_id: str
    description: str
    image_path: Optional[str] = None
    requires_manual_review: bool = True


# ---------------------------------------------------------------------------
# Text extraction
# ---------------------------------------------------------------------------

def _detect_page_label(raw_text: str, pdf_page: int) -> Optional[str]:
    """Try to detect the printed page number from the page text.

    WHO guideline PDFs typically print the page number alone on a line
    near the top or bottom of the page.
    """
    lines = raw_text.strip().split("\n")
    # Check last 3 lines and first 3 lines for a standalone number
    candidates = lines[-3:] + lines[:3]
    for line in candidates:
        stripped = line.strip()
        if stripped.isdigit() and 1 <= int(stripped) <= 500:
            return stripped
    return None


def extract_pages(pdf_path: str) -> List[PageData]:
    """Extract text and font metadata from every page of the PDF.

    Returns a list of PageData objects, one per physical PDF page.
    """
    doc = fitz.open(pdf_path)
    pages: List[PageData] = []

    for page_idx in range(len(doc)):
        page = doc[page_idx]
        raw_text = page.get_text("text")

        # --- page label ---
        page_label = _detect_page_label(raw_text, page_idx + 1)

        # --- span-level metadata (font, size, bold) ---
        spans: List[TextSpan] = []
        try:
            blocks = page.get_text("dict", flags=fitz.TEXT_PRESERVE_WHITESPACE)["blocks"]
            for block in blocks:
                if block.get("type", 1) != 0:
                    continue  # skip image blocks
                for line in block.get("lines", []):
                    for span in line.get("spans", []):
                        spans.append(TextSpan(
                            text=span["text"],
                            font=span["font"],
                            size=round(span["size"], 1),
                            flags=span["flags"],
                            bbox=tuple(span["bbox"]),
                        ))
        except Exception as exc:
            logger.warning("Failed to extract spans from page %d: %s", page_idx + 1, exc)

        pages.append(PageData(
            pdf_page=page_idx + 1,
            page_label=page_label,
            raw_text=raw_text,
            spans=spans,
        ))

    doc.close()
    logger.info("Extracted %d pages from %s", len(pages), pdf_path)
    return pages


# ---------------------------------------------------------------------------
# Table of Contents
# ---------------------------------------------------------------------------

def extract_toc(pdf_path: str) -> List[TocEntry]:
    """Extract the embedded Table of Contents from the PDF."""
    doc = fitz.open(pdf_path)
    raw_toc = doc.get_toc()
    doc.close()

    entries = [
        TocEntry(level=entry[0], title=entry[1].strip(), page=entry[2])
        for entry in raw_toc
    ]
    logger.info("Extracted %d TOC entries from %s", len(entries), pdf_path)
    return entries


# ---------------------------------------------------------------------------
# Table extraction (pdfplumber)
# ---------------------------------------------------------------------------

def _table_to_markdown(headers: List[str], rows: List[List[str]]) -> str:
    """Convert a parsed table into a Markdown pipe-table."""
    if not headers:
        return ""

    n_cols = len(headers)
    header_line = " | ".join(h.replace("\n", " ").strip() for h in headers)
    separator = " | ".join(["---"] * n_cols)

    body_lines: List[str] = []
    for row in rows:
        padded = list(row) + [""] * (n_cols - len(row))
        cells = [c.replace("\n", " ").strip() if c else "" for c in padded[:n_cols]]
        body_lines.append(" | ".join(cells))

    return "\n".join([header_line, separator] + body_lines)


def extract_tables(pdf_path: str) -> List[TableData]:
    """Extract tables from the PDF using pdfplumber.

    Falls back gracefully if pdfplumber is not installed.
    """
    tables: List[TableData] = []
    try:
        import pdfplumber
    except ImportError:
        logger.warning("pdfplumber not installed — skipping table extraction")
        return tables

    try:
        with pdfplumber.open(pdf_path) as pdf:
            for page_num, page in enumerate(pdf.pages, 1):
                page_tables = page.extract_tables()
                if not page_tables:
                    continue
                for tbl_idx, table in enumerate(page_tables):
                    if not table or len(table) < 2:
                        continue

                    # First non-empty row as headers
                    first_row = table[0]
                    headers = [str(h) if h else "" for h in first_row]
                    data_rows = [
                        [str(c) if c else "" for c in row]
                        for row in table[1:]
                    ]

                    md = _table_to_markdown(headers, data_rows)

                    tables.append(TableData(
                        pdf_page=page_num,
                        table_index=tbl_idx,
                        headers=headers,
                        rows=data_rows,
                        markdown=md,
                    ))
                    logger.info("Extracted table from page %d (index %d)", page_num, tbl_idx)
    except Exception as exc:
        logger.warning("Table extraction failed: %s", exc)

    logger.info("Total tables extracted: %d", len(tables))
    return tables


# ---------------------------------------------------------------------------
# Figure / algorithm detection
# ---------------------------------------------------------------------------

_FIGURE_RE = [
    re.compile(r"(?:figure|fig\.?)\s*(\d+)", re.IGNORECASE),
    re.compile(r"algorithm\s*(\d+)", re.IGNORECASE),
]


def detect_figures(
    pdf_path: str,
    output_dir: Optional[str] = None,
) -> List[FigureInfo]:
    """Detect pages containing figures or clinical algorithms.

    Optionally saves page screenshots as PNG to *output_dir*.
    """
    figures: List[FigureInfo] = []
    doc = fitz.open(pdf_path)

    for page_idx in range(len(doc)):
        page = doc[page_idx]
        images = page.get_images(full=True)
        text = page.get_text("text")

        # Look for figure / algorithm captions
        matched_label: Optional[str] = None
        description = ""
        for pat in _FIGURE_RE:
            m = pat.search(text)
            if m:
                matched_label = m.group(0)
                # Grab a short description from the caption line
                start = m.start()
                snippet = text[start: start + 300].split("\n")
                description = " ".join(snippet[:3]).strip()
                break

        # Heuristic: page has many images or a figure/algorithm caption
        significant_images = len(images) > 2
        if matched_label or significant_images:
            fig_id = f"fig_p{page_idx + 1:02d}"
            figure = FigureInfo(
                pdf_page=page_idx + 1,
                figure_id=fig_id,
                description=description or f"Figure/image content on page {page_idx + 1}",
                requires_manual_review=True,
            )

            # Save page as PNG
            if output_dir:
                try:
                    os.makedirs(output_dir, exist_ok=True)
                    pix = page.get_pixmap(dpi=150)
                    img_path = os.path.join(output_dir, f"WHO03_{fig_id}.png")
                    pix.save(img_path)
                    figure.image_path = img_path
                    logger.info("Saved figure page %d → %s", page_idx + 1, img_path)
                except Exception as exc:
                    logger.warning("Failed to save figure page %d: %s", page_idx + 1, exc)

            figures.append(figure)

    doc.close()
    logger.info("Detected %d figure pages", len(figures))
    return figures
