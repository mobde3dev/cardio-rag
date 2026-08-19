import os

from dotenv import load_dotenv

from sentence_transformers import SentenceTransformer

from supabase import create_client, Client


# ============================================================
# CONFIG
# ============================================================

load_dotenv()

SUPABASE_URL = os.environ[
    "SUPABASE_URL"
]

SUPABASE_SECRET_KEY = os.environ[
    "SUPABASE_KEY"
]

MODEL_NAME = "BAAI/bge-m3"


# ============================================================
# SUPABASE
# ============================================================

supabase: Client = create_client(
    SUPABASE_URL,
    SUPABASE_SECRET_KEY
)


# ============================================================
# EMBEDDING MODEL
# ============================================================

print(
    "Loading BGE-M3..."
)

model = SentenceTransformer(
    MODEL_NAME
)

print(
    "Model loaded."
)


# ============================================================
# SEARCH
# ============================================================
def rerank(results):

    reranked = []


    for row in results:

        score = float(
            row["similarity"]
        )


        # ----------------------------
        # Clinical priority
        # ----------------------------

        priority = row.get(
            "clinical_priority"
        )

        if priority == 1:
            score += 0.04

        elif priority == 2:
            score += 0.01

        elif priority == 3:
            score -= 0.02


        # ----------------------------
        # Canonical source
        # ----------------------------

        if row.get(
            "is_canonical"
        ) is True:

            score += 0.04


        # ----------------------------
        # Recommendation bonus
        # ----------------------------

        if row.get(
            "content_type"
        ) == "recommendation":

            score += 0.02


        # ----------------------------
        # Executive summary penalty
        # ----------------------------

        if (
            row.get("section")
            == "Executive summary"
        ):

            score -= 0.03


        row["rerank_score"] = score

        reranked.append(row)


    reranked.sort(

        key=lambda x:
            x["rerank_score"],

        reverse=True

    )


    return reranked
def semantic_search(

    query: str,

    match_count: int = 15,

    organization=None,

    topic=None,

    prevention_type=None

):


    query_embedding = model.encode(

        query,

        normalize_embeddings=True,

        convert_to_numpy=True

    ).astype(float).tolist()


    response = (

        supabase
        .rpc(

            "match_medical_chunks",

            {

                "query_embedding":
                    query_embedding,

                "match_count":
                    match_count,

                "filter_organization":
                    organization,

                "filter_topic":
                    topic,

                "filter_prevention_type":
                    prevention_type

            }

        )
        .execute()

    )


    return response.data


# ============================================================
# DISPLAY
# ============================================================

def print_results(
    query,
    results
):

    print("\n")
    print("=" * 80)

    print("QUERY:")
    print(query)

    print("=" * 80)


    for rank, row in enumerate(
        results,
        start=1
    ):


        print("\n" + "-" * 80)

        print(
            f"Rank: {rank}"
        )

        print(
            f"Similarity: "
            f"{row['similarity']:.4f}"
        )

        print(
            f"Chunk: "
            f"{row['chunk_id']}"
        )

        print(
            f"Organization: "
            f"{row['organization']}"
        )

        print(
            f"Topic: "
            f"{row['topic']}"
        )

        print(
            f"Subtopic: "
            f"{row['subtopic']}"
        )

        print(
            f"Priority: "
            f"{row['clinical_priority']}"
        )

        print(
            f"Canonical: "
            f"{row['is_canonical']}"
        )

        print(
            f"Page: "
            f"{row['pdf_page_start']}"
        )

        print("\nTEXT:")

        print(
            row["text"][:1000]
        )


# ============================================================
# TESTS
# ============================================================

TEST_QUERIES = [

    "ما هي أدوية الخط الأول لعلاج ارتفاع ضغط الدم؟",

    "What are the first-line medications for hypertension?",

    "What LDL cholesterol target is recommended for secondary prevention?",

    "ما هو مستوى LDL المستهدف للوقاية الثانوية من أمراض القلب؟",

]



for query in TEST_QUERIES:

    results = semantic_search(
        query,
        match_count=15
    )
   
    results = rerank(
        results
    )

    results = results[:5]

    print_results(
        query,
        results
    )