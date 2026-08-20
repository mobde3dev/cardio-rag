"""
pipeline.py — Unified CardioRAG processing pipeline.

Usage:
    python -m src.pipeline --doc who   --pdf data/raw/WHO_2021.pdf
    python -m src.pipeline --doc nice  --pdf data/raw/NICE_2023.pdf
    python -m src.pipeline --doc all                  # process both
"""

import argparse
import json
import logging
import os
import sys
import time
from pathlib import Path
from typing import List

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger("cardiorag.pipeline")

# ---------------------------------------------------------------------------
# Document registry
# ---------------------------------------------------------------------------
# Maps short document key → (default PDF path, pipeline function)

DOCUMENT_REGISTRY = {
    "who": {
        "default_pdf": "data/raw/WHO_2021.pdf",
        "output_dir": "data/processed",
        "output_stem": "WHO_2021_chunks",
        "pipeline": "who",
    },
    "nice": {
        "default_pdf": "data/raw/NICE_2023.pdf",
        "output_dir": "data/processed",
        "output_stem": "NICE_2023_chunks",
        "pipeline": "nice",
    },
    "ng106": {
        "default_pdf": "data/raw/NICE_NG106.pdf",
        "output_dir": "data/processed",
        "output_stem": "NICE_NG106_chunks",
        "pipeline": "ng106",
    },
}


# ---------------------------------------------------------------------------
# Pipelines
# ---------------------------------------------------------------------------

from src.pipelines import run_who_pipeline as _exec_who_pipeline
from src.pipelines import run_nice_pipeline as _exec_nice_pipeline
from src.pipelines import run_ng106_pipeline as _exec_ng106_pipeline

def run_who_pipeline(pdf_path: Path, out_dir: Path, stem: str) -> List[dict]:
    """Run the WHO_2021 pipeline and return serialisable chunks."""
    return _exec_who_pipeline(pdf_path=str(pdf_path))


def run_nice_pipeline(pdf_path: Path, out_dir: Path, stem: str) -> List[dict]:
    """Run the NICE_2023 (NG238) pipeline and return serialisable chunks."""
    chunks, stats = _exec_nice_pipeline(pdf_path=str(pdf_path))
    return chunks


def run_ng106_pipeline(pdf_path: Path, out_dir: Path, stem: str) -> List[dict]:
    """Run the NICE NG106 (Heart Failure) pipeline and return serialisable chunks."""
    chunks, stats = _exec_ng106_pipeline(pdf_path=str(pdf_path))
    return chunks


# ---------------------------------------------------------------------------
# Output helpers
# ---------------------------------------------------------------------------

def write_outputs(chunks: List[dict], out_dir: Path, stem: str) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)

    # JSON (pretty)
    json_path = out_dir / f"{stem}.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(chunks, f, ensure_ascii=False, indent=2)
    logger.info("Wrote %d chunks -> %s", len(chunks), json_path)

    # JSONL (one chunk per line, for vector DBs)
    jsonl_path = out_dir / f"{stem}.jsonl"
    with open(jsonl_path, "w", encoding="utf-8") as f:
        for c in chunks:
            f.write(json.dumps(c, ensure_ascii=False) + "\n")
    logger.info("Wrote JSONL -> %s", jsonl_path)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="CardioRAG unified pipeline"
    )
    parser.add_argument(
        "--doc",
        choices=["who", "nice", "ng106", "all"],
        default="all",
        help="Which document to process (default: all)",
    )
    parser.add_argument(
        "--pdf",
        type=Path,
        default=None,
        help="Override PDF path (only valid with --doc who|nice|ng106)",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=Path("data/processed"),
        help="Output directory (default: data/processed)",
    )
    args = parser.parse_args()

    docs = ["who", "nice", "ng106"] if args.doc == "all" else [args.doc]

    for doc in docs:
        cfg = DOCUMENT_REGISTRY[doc]
        pdf = args.pdf or Path(cfg["default_pdf"])

        if not pdf.exists():
            logger.error("PDF not found: %s", pdf)
            sys.exit(1)

        out_dir = args.out or Path(cfg["output_dir"])
        stem = cfg["output_stem"]

        logger.info("=" * 60)
        logger.info("Processing: %s  (%s)", doc.upper(), pdf.name)
        logger.info("=" * 60)

        t0 = time.time()

        if cfg["pipeline"] == "who":
            chunks = run_who_pipeline(pdf, out_dir, stem)
        elif cfg["pipeline"] == "nice":
            chunks = run_nice_pipeline(pdf, out_dir, stem)
        else:
            chunks = run_ng106_pipeline(pdf, out_dir, stem)

        elapsed = time.time() - t0
        logger.info("Done %s in %.1fs", doc.upper(), elapsed)


if __name__ == "__main__":
    main()
