import json
from pathlib import Path

import numpy as np
import torch
from sentence_transformers import SentenceTransformer


# ============================================================
# CONFIG
# ============================================================

MODEL_NAME = "BAAI/bge-m3"

INPUT_FILES = [
    Path("data/processed/who03_chunks.json"),
    Path("data/processed/nice3_chunks.json"),
]

OUTPUT_DIR = Path("data/embeddings")

EMBEDDINGS_FILE = OUTPUT_DIR / "cardiorag_embeddings.npy"
CHUNKS_FILE = OUTPUT_DIR / "cardiorag_chunks.json"

BATCH_SIZE = 16


# ============================================================
# DEVICE
# ============================================================

if torch.cuda.is_available():
    DEVICE = "cuda"

elif torch.backends.mps.is_available():
    DEVICE = "mps"

else:
    DEVICE = "cpu"


print("=" * 70)
print("CARDIORAG EMBEDDING PIPELINE")
print("=" * 70)

print(f"Device: {DEVICE}")
print(f"Model: {MODEL_NAME}")


# ============================================================
# LOAD MODEL
# ============================================================

print("\nLoading embedding model...")

model = SentenceTransformer(
    MODEL_NAME,
    device=DEVICE
)

print("Model loaded successfully.")


# ============================================================
# LOAD CHUNKS
# ============================================================

def load_json(path: Path):

    if not path.exists():
        raise FileNotFoundError(
            f"Input file not found: {path}"
        )

    with path.open(
        "r",
        encoding="utf-8"
    ) as f:

        data = json.load(f)

    if not isinstance(data, list):
        raise ValueError(
            f"{path} must contain a JSON array."
        )

    return data


all_chunks = []


for input_file in INPUT_FILES:

    print(f"\nLoading: {input_file}")

    chunks = load_json(input_file)

    valid_count = 0

    for chunk in chunks:

        text = str(
            chunk.get("text", "")
        ).strip()

        if not text:
            continue

        chunk_id = chunk.get("chunk_id")

        if not chunk_id:
            print(
                "WARNING: skipping chunk without chunk_id"
            )
            continue

        all_chunks.append(chunk)

        valid_count += 1

    print(
        f"Valid chunks loaded: {valid_count}"
    )


if not all_chunks:
    raise RuntimeError(
        "No valid chunks were found."
    )


print("\n" + "-" * 70)
print(
    f"TOTAL CHUNKS: {len(all_chunks)}"
)
print("-" * 70)


# ============================================================
# PREPARE TEXT
# ============================================================

texts = [
    chunk["text"].strip()
    for chunk in all_chunks
]


# ============================================================
# GENERATE EMBEDDINGS
# ============================================================

print("\nGenerating embeddings...")

embeddings = model.encode(

    texts,

    batch_size=BATCH_SIZE,

    show_progress_bar=True,

    normalize_embeddings=True,

    convert_to_numpy=True
)


embeddings = embeddings.astype(
    np.float32
)


print("\nEmbedding generation finished.")

print(
    f"Embedding shape: {embeddings.shape}"
)

print(
    f"Number of vectors: {embeddings.shape[0]}"
)

print(
    f"Vector dimensions: {embeddings.shape[1]}"
)


# ============================================================
# VALIDATION
# ============================================================

if embeddings.shape[0] != len(all_chunks):

    raise RuntimeError(
        "Number of embeddings does not match number of chunks."
    )


if np.isnan(embeddings).any():

    raise RuntimeError(
        "NaN values detected in embeddings."
    )


if np.isinf(embeddings).any():

    raise RuntimeError(
        "Infinite values detected in embeddings."
    )


# ============================================================
# SAVE OUTPUT
# ============================================================

OUTPUT_DIR.mkdir(
    parents=True,
    exist_ok=True
)


np.save(
    EMBEDDINGS_FILE,
    embeddings
)


records = []


for index, chunk in enumerate(all_chunks):

    records.append({

        "vector_index": index,

        "chunk_id": chunk["chunk_id"],

        "text": chunk["text"],

        "metadata": chunk.get(
            "metadata",
            {}
        )

    })


with CHUNKS_FILE.open(
    "w",
    encoding="utf-8"
) as f:

    json.dump(
        records,
        f,
        ensure_ascii=False,
        indent=2
    )


print("\nFiles saved:")

print(
    f"Embeddings: {EMBEDDINGS_FILE}"
)

print(
    f"Chunks: {CHUNKS_FILE}"
)


# ============================================================
# TEST SEARCH
# ============================================================

def semantic_search(
    query: str,
    top_k: int = 5
):

    query_embedding = model.encode(

        query,

        normalize_embeddings=True,

        convert_to_numpy=True
    ).astype(np.float32)


    # Because embeddings are normalized,
    # dot product = cosine similarity
    scores = embeddings @ query_embedding


    top_indices = np.argsort(
        scores
    )[::-1][:top_k]


    print("\n")
    print("=" * 70)
    print("QUERY")
    print("=" * 70)

    print(query)

    print("\nTOP RESULTS")


    for rank, index in enumerate(
        top_indices,
        start=1
    ):

        chunk = all_chunks[index]

        metadata = chunk.get(
            "metadata",
            {}
        )


        print("\n" + "-" * 70)

        print(
            f"Rank: {rank}"
        )

        print(
            f"Score: {scores[index]:.4f}"
        )

        print(
            f"Chunk ID: {chunk.get('chunk_id')}"
        )

        print(
            f"Source: "
            f"{metadata.get('source_file')}"
        )

        print(
            f"Organization: "
            f"{metadata.get('organization')}"
        )

        print(
            f"Section: "
            f"{metadata.get('section')}"
        )

        print(
            f"Topic: "
            f"{metadata.get('topic')}"
        )

        print(
            f"Subtopic: "
            f"{metadata.get('subtopic')}"
        )

        page = (
            metadata.get("pdf_page_start")
            or metadata.get("page")
        )

        print(
            f"Page: {page}"
        )

        print(
            f"Clinical Priority: "
            f"{metadata.get('clinical_priority')}"
        )


        print("\nTEXT:")

        print(
            chunk["text"][:1000]
        )


# ============================================================
# RETRIEVAL SANITY TESTS
# ============================================================

TEST_QUERIES = [

    "What are the first-line medications for hypertension?",

    "ما هي أدوية الخط الأول لعلاج ارتفاع ضغط الدم؟",

    "What LDL cholesterol target is recommended for secondary prevention?",

    "ما هو مستوى LDL المستهدف للوقاية الثانوية من أمراض القلب؟",

]


for query in TEST_QUERIES:

    semantic_search(
        query,
        top_k=5
    )


print("\n" + "=" * 70)

print(
    "CARDIORAG EMBEDDING PIPELINE COMPLETED SUCCESSFULLY"
)

print("=" * 70)