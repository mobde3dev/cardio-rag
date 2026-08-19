import json
import os
import uuid
from pathlib import Path

import numpy as np

from dotenv import load_dotenv
from supabase import create_client, Client


# ============================================================
# CONFIG
# ============================================================

load_dotenv()

SUPABASE_URL = os.environ["SUPABASE_URL"]
SUPABASE_SECRET_KEY = os.environ["SUPABASE_KEY"]

EMBEDDINGS_FILE = Path(
    "data/embeddings/cardiorag_embeddings.npy"
)

CHUNKS_FILE = Path(
    "data/embeddings/cardiorag_chunks.json"
)

BATCH_SIZE = 25


# ============================================================
# CLIENT
# ============================================================

supabase: Client = create_client(
    SUPABASE_URL,
    SUPABASE_SECRET_KEY
)


# ============================================================
# HELPERS
# ============================================================

def stable_uuid(chunk_id: str) -> str:

    return str(
        uuid.uuid5(
            uuid.NAMESPACE_URL,
            f"cardiorag:{chunk_id}"
        )
    )


def get_value(metadata, key, default=None):

    value = metadata.get(key)

    if value is None:
        return default

    return value


# ============================================================
# LOAD FILES
# ============================================================

print("=" * 70)
print("CARDIORAG → SUPABASE INGESTION")
print("=" * 70)


embeddings = np.load(
    EMBEDDINGS_FILE
)


with CHUNKS_FILE.open(
    "r",
    encoding="utf-8"
) as f:

    chunks = json.load(f)


print(
    f"Embeddings shape: {embeddings.shape}"
)

print(
    f"Chunks: {len(chunks)}"
)


# ============================================================
# VALIDATION
# ============================================================

if len(embeddings) != len(chunks):

    raise ValueError(
        "Embedding count does not match chunk count."
    )


if embeddings.shape[1] != 1024:

    raise ValueError(
        f"Expected BGE-M3 1024 dimensions, "
        f"got {embeddings.shape[1]}"
    )


if np.isnan(embeddings).any():

    raise ValueError(
        "NaN detected in embeddings."
    )


# ============================================================
# PREPARE ROWS
# ============================================================

rows = []


for index, chunk in enumerate(chunks):

    metadata = chunk.get(
        "metadata",
        {}
    )

    chunk_id = chunk["chunk_id"]

    section = metadata.get(
        "section"
    )

    # Canonical rule for WHO Executive Summary duplicates
    is_canonical = metadata.get(
        "is_canonical"
    )

    if is_canonical is None:

        if (
            section == "Executive summary"
            and "_REC_" in chunk_id
        ):
            is_canonical = False

        else:
            is_canonical = True


    publication_year = (
        metadata.get("publication_year")
        or metadata.get("year")
    )


    row = {

        "id": stable_uuid(
            chunk_id
        ),

        "chunk_id": chunk_id,

        "text": chunk["text"],

        "embedding":
            embeddings[index]
            .astype(float)
            .tolist(),

        "source_file":
            metadata.get(
                "source_file"
            ),

        "organization":
            metadata.get(
                "organization"
            ),

        "guideline_code":
            metadata.get(
                "guideline_code"
            ),

        "document_title":
            metadata.get(
                "document_title"
            ),

        "publication_year":
            publication_year,

        "pdf_page_start":
            metadata.get(
                "pdf_page_start"
            ),

        "pdf_page_end":
            metadata.get(
                "pdf_page_end"
            ),

        "section":
            section,

        "subsection":
            metadata.get(
                "subsection"
            ),

        "recommendation_id":
            metadata.get(
                "recommendation_id"
            ),

        "domain":
            metadata.get(
                "domain"
            ),

        "topic":
            metadata.get(
                "topic"
            ),

        "subtopic":
            metadata.get(
                "subtopic"
            ),

        "content_type":
            metadata.get(
                "content_type"
            ),

        "prevention_type":
            metadata.get(
                "prevention_type"
            ),

        "clinical_priority":
            metadata.get(
                "clinical_priority"
            ),

        "region_scope":
            metadata.get(
                "region_scope"
            ),

        "is_canonical":
            is_canonical,

        "historical_context":
            metadata.get(
                "historical_context",
                False
            ),

        "requires_manual_review":
            metadata.get(
                "requires_manual_review",
                False
            ),

        # Keep EVERYTHING
        "metadata":
            metadata

    }


    rows.append(row)


print(
    f"Prepared rows: {len(rows)}"
)


# ============================================================
# UPLOAD
# ============================================================

uploaded = 0


for start in range(
    0,
    len(rows),
    BATCH_SIZE
):

    batch = rows[
        start:start + BATCH_SIZE
    ]


    response = (

        supabase
        .table("medical_chunks")
        .upsert(
            batch,
            on_conflict="chunk_id"
        )
        .execute()

    )


    uploaded += len(batch)


    print(
        f"Uploaded: "
        f"{uploaded}/{len(rows)}"
    )


print()
print("=" * 70)
print("SUPABASE INGESTION COMPLETE")
print("=" * 70)