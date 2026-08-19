import os
from typing import Optional

from dotenv import load_dotenv
from supabase import create_client
import requests
import numpy as np
import math

from .query_classifier import (
    classify_query,
    QueryProfile,
)
import sys


# ============================================================
# UTF-8 OUTPUT FIX FOR WINDOWS
# ============================================================

if sys.stdout is not None:
    sys.stdout.reconfigure(
        encoding="utf-8",
        errors="replace"
    )

if sys.stderr is not None:
    sys.stderr.reconfigure(
        encoding="utf-8",
        errors="replace"
    )

# ============================================================
# CONFIG
# ============================================================

load_dotenv(
    override=True
)

SUPABASE_URL = os.environ[
    "SUPABASE_URL"
]

SUPABASE_SECRET_KEY = os.environ[
    "SUPABASE_KEY"
]

CLOUDFLARE_ACCOUNT_ID = os.environ[
    "CLOUDFLARE_ACCOUNT_ID"
]

CLOUDFLARE_API_TOKEN = os.environ[
    "CLOUDFLARE_API_TOKEN"
]

CLOUDFLARE_EMBED_MODEL = os.getenv(
    "CLOUDFLARE_EMBED_MODEL",
    "@cf/baai/bge-m3"
)

MODEL_NAME = "BAAI/bge-m3"

def encode_query(query: str):

    url = (
        "https://api.cloudflare.com/client/v4/accounts/"
        f"{CLOUDFLARE_ACCOUNT_ID}/ai/v1/embeddings"
    )

    response = requests.post(
        url,
        headers={
            "Authorization":
                f"Bearer {CLOUDFLARE_API_TOKEN}",

            "Content-Type":
                "application/json",
        },
        json={
            "model":
                CLOUDFLARE_EMBED_MODEL,

            "input":
                query,
        },
        timeout=30,
    )

    response.raise_for_status()

    data = response.json()

    embedding = np.asarray(
        data["data"][0]["embedding"],
        dtype=np.float32,
    )

    if embedding.shape != (1024,):
        raise ValueError(
            "Unexpected embedding dimension: "
            f"{embedding.shape}"
        )

    return embedding.tolist()



# ============================================================
# CLIENTS
# ============================================================



supabase = create_client(
    SUPABASE_URL,
    SUPABASE_SECRET_KEY
)

def encode_query(
    query: str
) -> list[float]:

    url = (
        "https://api.cloudflare.com/"
        "client/v4/accounts/"
        f"{CLOUDFLARE_ACCOUNT_ID}"
        "/ai/run/"
        f"{CLOUDFLARE_EMBED_MODEL}"
    )

    response = requests.post(
        url,
        headers={
            "Authorization":
                f"Bearer {CLOUDFLARE_API_TOKEN}",

            "Content-Type":
                "application/json",
        },
        json={
            "text": [
                query
            ]
        },
        timeout=30,
    )

    if not response.ok:

        raise RuntimeError(
            "Cloudflare embedding request failed "
            f"({response.status_code}): "
            f"{response.text}"
        )

    payload = response.json()

    if not payload.get(
        "success",
        False
    ):

        raise RuntimeError(
            "Cloudflare returned an unsuccessful "
            f"response: {payload}"
        )

    result = payload.get(
        "result"
    )

    if not result:

        raise RuntimeError(
            "Cloudflare response does not contain "
            "'result'."
        )

    # Expected Workers AI embedding response:
    #
    # result = {
    #   "shape": [1, 1024],
    #   "data": [[...1024 floats...]]
    # }

    data = result.get(
        "data"
    )

    if not data:

        raise RuntimeError(
            "Cloudflare response does not contain "
            "embedding data."
        )

    embedding = data[0]

    if len(
        embedding
    ) != 1024:

        raise RuntimeError(
            "Unexpected Cloudflare embedding "
            f"dimension: {len(embedding)} "
            "(expected 1024)"
        )

    # Normalize explicitly because your existing
    # pgvector pipeline was built around normalized
    # BGE-M3 embeddings.
    norm = math.sqrt(
        sum(
            value * value
            for value in embedding
        )
    )

    if norm == 0:
        raise RuntimeError(
            "Cloudflare returned a zero embedding."
        )

    normalized_embedding = [
        float(value / norm)
        for value in embedding
    ]

    return normalized_embedding

# ============================================================
# VECTOR SEARCH
# ============================================================

def vector_search_by_embedding(

    query_embedding,

    limit: int = 15,

    organization: Optional[str] = None,

):

    response = (

        supabase
        .rpc(

            "match_medical_chunks",

            {

                "query_embedding":
                    query_embedding,

                "match_count":
                    limit,

                # Organization is safe as a hard filter
                # when explicitly requested or during
                # cross-guideline balanced retrieval.
                "filter_organization":
                    organization,

                # Topic stays SOFT.
                "filter_topic":
                    None,

                "filter_prevention_type":
                    None,

            }

        )
        .execute()

    )

    return response.data or []


def vector_search(

    query: str,

    limit: int = 15,

    organization: Optional[str] = None,

):

    embedding = encode_query(
        query
    )

    return vector_search_by_embedding(

        query_embedding=embedding,

        limit=limit,

        organization=organization,

    )


# ============================================================
# EXACT RECOMMENDATION LOOKUP
# ============================================================

def exact_recommendation_lookup(

    recommendation_id: str,

    organization: Optional[str] = None,

):

    columns = (

        "id,"
        "chunk_id,"
        "text,"
        "organization,"
        "source_file,"
        "guideline_code,"
        "section,"
        "subsection,"
        "recommendation_id,"
        "domain,"
        "topic,"
        "subtopic,"
        "content_type,"
        "prevention_type,"
        "clinical_priority,"
        "pdf_page_start,"
        "pdf_page_end,"
        "is_canonical,"
        "metadata"

    )


    query_builder = (

        supabase
        .table(
            "medical_chunks"
        )
        .select(
            columns
        )
        .eq(
            "recommendation_id",
            recommendation_id
        )

    )


    if organization:

        query_builder = (
            query_builder
            .eq(
                "organization",
                organization
            )
        )


    response = (
        query_builder
        .execute()
    )


    return response.data or []


# ============================================================
# DEDUPLICATION
# ============================================================

def deduplicate_results(
    rows
):

    seen = set()

    unique = []


    for row in rows:

        chunk_id = row.get(
            "chunk_id"
        )

        if not chunk_id:
            continue

        if chunk_id in seen:
            continue

        seen.add(
            chunk_id
        )

        unique.append(
            row
        )


    return unique


# ============================================================
# CONTENT TYPE NORMALIZATION
# ============================================================

def infer_content_type(
    row
):

    content_type = (

        row.get(
            "content_type"
        )

        or ""

    ).lower().strip()


    chunk_id = (

        row.get(
            "chunk_id"
        )

        or ""

    ).upper()


    aliases = {

        "committee_rationale":
            "rationale",

        "why_the_committee_made_these_recommendations":
            "rationale",

        "implementation_impact":
            "implementation_impact",

        "evidence_to_decision":
            "evidence_to_decision",

        "recommendation":
            "recommendation",

        "evidence":
            "evidence",

        "table":
            "table",

        "algorithm":
            "algorithm",

        "drug_guidance":
            "drug_guidance",

    }


    if content_type in aliases:

        return aliases[
            content_type
        ]


    if "_REC" in chunk_id:
        return "recommendation"


    if "_RATIONALE_" in chunk_id:
        return "rationale"


    if "_IMPACT_" in chunk_id:
        return "implementation_impact"


    if "_E2D_" in chunk_id:
        return "evidence_to_decision"


    if "_EVID_" in chunk_id:
        return "evidence"


    if "_TBL_" in chunk_id:
        return "table"


    return (
        content_type
        or "other"
    )


# ============================================================
# INTENT-SPECIFIC LEXICAL BONUS
# ============================================================

def calculate_intent_bonus(

    row,
    profile: QueryProfile,

):

    text = (

        row.get(
            "text"
        )

        or ""

    ).lower()


    content_type = (
        infer_content_type(row)
    )


    intent = profile.intent


    bonus = 0.0

    reasons = []


    # --------------------------------------------------------
    # Risk underestimation
    # --------------------------------------------------------

    if intent == "risk_underestimation":

        if (
            "underestimate risk"
            in text
            or
            "may underestimate"
            in text
        ):

            bonus += 0.140

            reasons.append(
                (
                    "risk_underestimation_exact",
                    0.140
                )
            )


    # --------------------------------------------------------
    # Groups where risk tool should NOT be used
    # --------------------------------------------------------

    elif intent == "no_risk_tool":

        if (
            "do not use a risk assessment tool"
            in text
        ):

            bonus += 0.140

            reasons.append(
                (
                    "no_risk_tool_exact",
                    0.140
                )
            )


    # --------------------------------------------------------
    # Urgent triglyceride specialist review
    # --------------------------------------------------------

    elif intent == "urgent_triglyceride_referral":

        if (
            "triglyceride" in text
            and
            (
                "urgent" in text
                or
                "specialist" in text
            )
        ):

            bonus += 0.120

            reasons.append(
                (
                    "urgent_triglyceride_match",
                    0.120
                )
            )


    # --------------------------------------------------------
    # Nonphysician management
    # --------------------------------------------------------

    elif intent == "nonphysician_management":

        if any(
            term in text
            for term in [
                "nonphysician",
                "non-physician",
                "pharmacist",
                "nurse",
            ]
        ):

            bonus += 0.120

            reasons.append(
                (
                    "nonphysician_match",
                    0.120
                )
            )


    # --------------------------------------------------------
    # Statin intensity table
    # --------------------------------------------------------

    elif intent == "statin_intensity":

        if (
            "statin" in text
            and
            "intensity" in text
        ):

            bonus += 0.090

            reasons.append(
                (
                    "statin_intensity_match",
                    0.090
                )
            )

        if (
            profile.requires_table
            and
            content_type == "table"
        ):

            bonus += 0.060

            reasons.append(
                (
                    "table_match",
                    0.060
                )
            )


    # --------------------------------------------------------
    # Follow up
    # --------------------------------------------------------

    elif intent == "follow_up":

        if any(
            term in text
            for term in [
                "follow-up",
                "follow up",
                "reassessment",
                "monthly",
                "month",
            ]
        ):

            bonus += 0.080

            reasons.append(
                (
                    "follow_up_match",
                    0.080
                )
            )


    # --------------------------------------------------------
    # Baseline statin assessment
    # --------------------------------------------------------

    elif intent == "baseline_statin_assessment":

        if (
            "before offering a statin"
            in text
            or
            "baseline" in text
        ):

            bonus += 0.100

            reasons.append(
                (
                    "baseline_statin_match",
                    0.100
                )
            )


    # --------------------------------------------------------
    # CK
    # --------------------------------------------------------

    elif intent == "ck_management":

        if (
            "creatine kinase"
            in text
        ):

            bonus += 0.100

            reasons.append(
                (
                    "creatine_kinase_match",
                    0.100
                )
            )


    # --------------------------------------------------------
    # Algorithm
    # --------------------------------------------------------

    elif intent == "algorithm_1":

        if (
            "algorithm 1"
            in text
            or
            "single-pill combination"
            in text
            or
            "single pill combination"
            in text
        ):

            bonus += 0.120

            reasons.append(
                (
                    "algorithm_match",
                    0.120
                )
            )

        if (
            profile.requires_algorithm
            and
            content_type in [
                "algorithm",
                "table",
            ]
        ):

            bonus += 0.050

            reasons.append(
                (
                    "algorithm_content_type",
                    0.050
                )
            )


    # --------------------------------------------------------
    # Pregnancy
    # --------------------------------------------------------

    elif intent == "pregnancy":

        if any(
            term in text
            for term in [
                "pregnan",
                "conception",
                "breastfeeding",
            ]
        ):

            bonus += 0.100

            reasons.append(
                (
                    "pregnancy_match",
                    0.100
                )
            )


    # --------------------------------------------------------
    # Lab/risk must not delay treatment
    # --------------------------------------------------------

    elif intent == "lab_and_risk_delay":

        if any(
            term in text
            for term in [
                "does not delay",
                "does not impede",
                "does not delay treatment",
                "does not delay or impede",
            ]
        ):

            bonus += 0.100

            reasons.append(
                (
                    "no_delay_match",
                    0.100
                )
            )


    # --------------------------------------------------------
    # Treatments not recommended
    # --------------------------------------------------------

    elif intent == "treatments_not_recommended":

        if any(
            term in text
            for term in [
                "do not offer",
                "should not be offered",
                "not recommended",
            ]
        ):

            bonus += 0.110

            reasons.append(
                (
                    "do_not_offer_match",
                    0.110
                )
            )


    # --------------------------------------------------------
    # Statin intolerance
    # --------------------------------------------------------

    elif intent == "statin_intolerance":

        if any(
            term in text
            for term in [
                "contraindicated",
                "not tolerated",
                "statin intolerant",
                "intolerance",
            ]
        ):

            bonus += 0.100

            reasons.append(
                (
                    "statin_intolerance_match",
                    0.100
                )
            )


    # --------------------------------------------------------
    # Diabetes + CKD
    # --------------------------------------------------------

    elif intent == "diabetes_ckd":

        local_bonus = 0.0

        if "diabetes" in text:

            local_bonus += 0.035

        if (
            "chronic kidney disease"
            in text
            or
            "ckd" in text
            or
            "egfr" in text
        ):

            local_bonus += 0.035

        if local_bonus:

            bonus += local_bonus

            reasons.append(
                (
                    "diabetes_ckd_match",
                    local_bonus
                )
            )


    # --------------------------------------------------------
    # Lifestyle
    # --------------------------------------------------------

    elif intent == "lifestyle":

        if any(
            term in text
            for term in [
                "lifestyle",
                "diet",
                "physical activity",
                "weight",
                "saturated fat",
            ]
        ):

            bonus += 0.070

            reasons.append(
                (
                    "lifestyle_match",
                    0.070
                )
            )


    # --------------------------------------------------------
    # Statin muscle adverse effects
    # --------------------------------------------------------

    elif intent == "statin_muscle_adverse_effects":

        if (
            "high-intensity statin"
            in text
            and
            "adverse effects"
            in text
        ):

            bonus += 0.160

            reasons.append(
                (
                    "statin_muscle_strategy_exact",
                    0.160
                )
            )


        elif (
            "statin" in text
            and
            any(
                phrase in text
                for phrase in [
                    "muscle symptoms",
                    "muscle pain",
                    "muscle",
                ]
            )
        ):

            bonus += 0.070

            reasons.append(
                (
                    "statin_muscle_related",
                    0.070
                )
            )


    # --------------------------------------------------------
    # SBP 130–139
    # --------------------------------------------------------

    elif intent == "sbp_130_139":

        if (
            "130" in text
            and
            "139" in text
        ):

            bonus += 0.100

            reasons.append(
                (
                    "sbp_130_139_match",
                    0.100
                )
            )


    # --------------------------------------------------------
    # BP target
    # --------------------------------------------------------

    elif intent == "blood_pressure_target":

        if (
            "target blood pressure"
            in text
            or
            "target systolic"
            in text
        ):

            bonus += 0.080

            reasons.append(
                (
                    "bp_target_match",
                    0.080
                )
            )


    # --------------------------------------------------------
    # Treatment initiation
    # --------------------------------------------------------

    elif intent == "treatment_initiation":

        if (
            "initiation"
            in text
            and
            "pharmacological"
            in text
        ):

            bonus += 0.080

            reasons.append(
                (
                    "treatment_initiation_match",
                    0.080
                )
            )


    # --------------------------------------------------------
    # First line HTN
    # --------------------------------------------------------

    elif intent == "first_line_htn":

        if (
            "first-line agents"
            in text
            or
            "initial treatment"
            in text
        ):

            bonus += 0.090

            reasons.append(
                (
                    "first_line_match",
                    0.090
                )
            )


    # --------------------------------------------------------
    # Lipid target
    # --------------------------------------------------------

    elif intent == "lipid_management":

        if (
            profile.prevention_type
            == "secondary"
            and
            "secondary prevention"
            in text
            and
            (
                "ldl"
                in text
                or
                "non-hdl"
                in text
            )
        ):

            bonus += 0.080

            reasons.append(
                (
                    "secondary_lipid_target_match",
                    0.080
                )
            )


    return (
        bonus,
        reasons
    )


# ============================================================
# METADATA-AWARE RERANKING
# ============================================================

def rerank_results(

    results,

    profile: QueryProfile,

):

    reranked = []


    for original_row in results:

        row = dict(
            original_row
        )


        semantic_score = float(
            row.get(
                "similarity",
                0
            )
        )


        score = semantic_score

        reasons = []


        # ====================================================
        # 1. CLINICAL PRIORITY
        # ====================================================

        priority = row.get(
            "clinical_priority"
        )


        if priority == 1:

            score += 0.035

            reasons.append(
                (
                    "clinical_priority_1",
                    0.035
                )
            )


        elif priority == 2:

            score += 0.010

            reasons.append(
                (
                    "clinical_priority_2",
                    0.010
                )
            )


        elif priority == 3:

            score -= 0.020

            reasons.append(
                (
                    "clinical_priority_3",
                    -0.020
                )
            )


        # ====================================================
        # 2. CANONICAL
        # ====================================================

        if row.get(
            "is_canonical"
        ) is True:

            score += 0.040

            reasons.append(
                (
                    "canonical",
                    0.040
                )
            )


        elif row.get(
            "is_canonical"
        ) is False:

            score -= 0.020

            reasons.append(
                (
                    "non_canonical",
                    -0.020
                )
            )


        # ====================================================
        # 3. TOPIC HINTS
        # ====================================================

        row_topic = row.get(
            "topic"
        )


        topic_hints = (
            profile.topic_hints
            or (
                [profile.topic]
                if profile.topic
                else []
            )
        )


        if (
            topic_hints
            and
            row_topic
        ):

            if (
                row_topic
                in topic_hints
            ):

                score += 0.060

                reasons.append(
                    (
                        "topic_match",
                        0.060
                    )
                )


            elif (
                profile.confidence
                >= 0.85
            ):

                score -= 0.025

                reasons.append(
                    (
                        "topic_mismatch",
                        -0.025
                    )
                )


        # ====================================================
        # 4. PREVENTION TYPE
        # ====================================================

        row_prevention = row.get(
            "prevention_type"
        )


        if (
            profile.prevention_type
            and
            row_prevention
        ):

            if (
                profile.prevention_type
                == row_prevention
            ):

                score += 0.050

                reasons.append(
                    (
                        "prevention_match",
                        0.050
                    )
                )


            else:

                score -= 0.030

                reasons.append(
                    (
                        "prevention_mismatch",
                        -0.030
                    )
                )


        # ====================================================
        # 5. CONTENT TYPE
        # ====================================================

        content_type = (
            infer_content_type(
                row
            )
        )


        if (
            profile.content_preference
            == "recommendation"
        ):

            if (
                content_type
                == "recommendation"
            ):

                score += 0.035

                reasons.append(
                    (
                        "recommendation_match",
                        0.035
                    )
                )


            elif (
                content_type
                in [
                    "rationale",
                    "implementation_impact",
                ]
            ):

                score -= 0.015

                reasons.append(
                    (
                        "supporting_content_penalty",
                        -0.015
                    )
                )


        elif (
            profile.content_preference
            == "rationale"
        ):

            if (
                content_type
                in [
                    "rationale",
                    "evidence",
                    "evidence_to_decision",
                ]
            ):

                score += 0.060

                reasons.append(
                    (
                        "rationale_match",
                        0.060
                    )
                )


            elif (
                content_type
                == "recommendation"
            ):

                score += 0.010

                reasons.append(
                    (
                        "related_recommendation",
                        0.010
                    )
                )


        # ====================================================
        # 6. EXACT RECOMMENDATION BONUS
        # ====================================================

        if profile.recommendation_id:

            recommendation_id = str(
                row.get(
                    "recommendation_id"
                )
                or ""
            )


            chunk_id = str(
                row.get(
                    "chunk_id"
                )
                or ""
            )


            if (
                profile.recommendation_id
                == recommendation_id

                or

                profile.recommendation_id
                in chunk_id
            ):

                score += 0.150

                reasons.append(
                    (
                        "exact_recommendation",
                        0.150
                    )
                )


        # ====================================================
        # 7. EXECUTIVE SUMMARY PENALTY
        # ====================================================

        section = str(
            row.get(
                "section"
            )
            or ""
        ).lower()


        if (
            "executive summary"
            in section
        ):

            score -= 0.030

            reasons.append(
                (
                    "executive_summary",
                    -0.030
                )
            )


        # ====================================================
        # 8. SPECIAL INTENT BONUS
        # ====================================================

        (
            intent_bonus,
            intent_reasons
        ) = calculate_intent_bonus(

            row=row,

            profile=profile,

        )


        score += intent_bonus

        reasons.extend(
            intent_reasons
        )


        # ====================================================
        # SAVE
        # ====================================================

        row[
            "semantic_score"
        ] = semantic_score


        row[
            "rerank_score"
        ] = round(
            score,
            6
        )


        row[
            "rerank_reasons"
        ] = reasons


        row[
            "detected_content_type"
        ] = content_type


        reranked.append(
            row
        )


    reranked.sort(

        key=lambda item:
            item["rerank_score"],

        reverse=True

    )


    return reranked


# ============================================================
# CROSS-GUIDELINE BALANCED RETRIEVAL
# ============================================================

def retrieve_candidates(

    query: str,

    profile: QueryProfile,

    candidate_count: int,

):

    query_embedding = encode_query(
        query
    )


    # ========================================================
    # Cross-guideline
    # ========================================================

    if (
        profile.requires_multiple_sources
        or
        len(profile.organizations) > 1
    ):

        organizations = (
            profile.organizations
            or [
                "WHO",
                "NICE",
            ]
        )


        # Fetch enough candidates independently from
        # EACH guideline so one source cannot occupy
        # every candidate slot.
        per_source = max(
            8,
            candidate_count // len(
                organizations
            )
        )


        all_results = []


        for organization in organizations:

            rows = (
                vector_search_by_embedding(

                    query_embedding=
                        query_embedding,

                    limit=
                        per_source,

                    organization=
                        organization,

                )
            )


            all_results.extend(
                rows
            )


        return deduplicate_results(
            all_results
        )


    # ========================================================
    # Normal retrieval
    # ========================================================

    rows = vector_search_by_embedding(

        query_embedding=
            query_embedding,

        limit=
            candidate_count,

        organization=
            profile.organization,

    )


    return deduplicate_results(
        rows
    )


# ============================================================
# SOURCE-BALANCED TOP-K
# ============================================================

def balanced_top_k(

    reranked,

    profile: QueryProfile,

    final_count: int,

):

    if (
        not profile.requires_multiple_sources

        or

        len(profile.organizations) < 2

        or

        final_count < 4
    ):

        return reranked[
            :final_count
        ]


    organizations = (
        profile.organizations
    )


    # Try to reserve at least 2 results
    # from each guideline.
    minimum_per_source = 2


    selected = []

    selected_ids = set()


    best_global_score = (

        reranked[0][
            "rerank_score"
        ]

        if reranked

        else 0
    )


    # Avoid forcing extremely irrelevant
    # documents merely for source balance.
    minimum_acceptable_score = (
        best_global_score
        - 0.30
    )


    for organization in organizations:

        organization_rows = [

            row
            for row in reranked

            if (
                row.get(
                    "organization"
                )
                == organization

                and

                row.get(
                    "rerank_score",
                    0
                )
                >= minimum_acceptable_score
            )

        ]


        for row in organization_rows[
            :minimum_per_source
        ]:

            chunk_id = row.get(
                "chunk_id"
            )


            if (
                chunk_id
                not in selected_ids
            ):

                selected.append(
                    row
                )

                selected_ids.add(
                    chunk_id
                )


    # Fill remaining places by global score
    for row in reranked:

        if len(
            selected
        ) >= final_count:

            break


        chunk_id = row.get(
            "chunk_id"
        )


        if (
            chunk_id
            in selected_ids
        ):

            continue


        selected.append(
            row
        )

        selected_ids.add(
            chunk_id
        )


    # Preserve final ranking order
    selected.sort(

        key=lambda item:
            item[
                "rerank_score"
            ],

        reverse=True

    )


    return selected[
        :final_count
    ]


# ============================================================
# DYNAMIC LIMITS
# ============================================================

def choose_limits(

    profile: QueryProfile,

    candidate_count:
        Optional[int],

    final_count:
        Optional[int],

):

    if candidate_count is None:

        if (
            profile.requires_multiple_sources
        ):

            candidate_count = 24

        elif (
            profile.requires_algorithm
            or
            profile.requires_table
        ):

            candidate_count = 20

        else:

            candidate_count = 15


    if final_count is None:

        if (
            profile.requires_multiple_sources
        ):

            final_count = 8

        elif (
            profile.requires_algorithm
            or
            profile.requires_table
        ):

            final_count = 7

        else:

            final_count = 5


    return (
        candidate_count,
        final_count
    )


# ============================================================
# MAIN RETRIEVER
# ============================================================

def retrieve(

    query: str,

    candidate_count:
        Optional[int] = None,

    final_count:
        Optional[int] = None,

):

    # --------------------------------------------------------
    # STEP 1
    # Query classification
    # --------------------------------------------------------

    profile = classify_query(
        query
    )


    (
        candidate_count,
        final_count
    ) = choose_limits(

        profile=profile,

        candidate_count=
            candidate_count,

        final_count=
            final_count,

    )


    # --------------------------------------------------------
    # STEP 2
    # Exact recommendation route
    # --------------------------------------------------------

    if profile.recommendation_id:

        exact_rows = (
            exact_recommendation_lookup(

                recommendation_id=
                    profile.recommendation_id,

                organization=
                    profile.organization,

            )
        )


        if exact_rows:

            prepared = []


            for row in exact_rows:

                row = dict(
                    row
                )

                row[
                    "similarity"
                ] = 1.0

                row[
                    "semantic_score"
                ] = 1.0

                row[
                    "rerank_score"
                ] = 1.0

                row[
                    "rerank_reasons"
                ] = [

                    (
                        "exact_recommendation_lookup",
                        1.0
                    )

                ]

                row[
                    "detected_content_type"
                ] = infer_content_type(
                    row
                )

                prepared.append(
                    row
                )


            return {

                "query":
                    query,

                "profile":
                    profile.to_dict(),

                "retrieval_mode":
                    "exact_recommendation",

                "candidate_count":
                    len(prepared),

                "results":
                    prepared[
                        :final_count
                    ],

            }


    # --------------------------------------------------------
    # STEP 3
    # Semantic candidate retrieval
    # --------------------------------------------------------

    candidates = retrieve_candidates(

        query=query,

        profile=profile,

        candidate_count=
            candidate_count,

    )


    # --------------------------------------------------------
    # STEP 4
    # Reranking
    # --------------------------------------------------------

    reranked = rerank_results(

        results=
            candidates,

        profile=
            profile,

    )


    # --------------------------------------------------------
    # STEP 5
    # Source-balanced Top-K
    # --------------------------------------------------------

    final_results = (
        balanced_top_k(

            reranked=
                reranked,

            profile=
                profile,

            final_count=
                final_count,

        )
    )


    retrieval_mode = (

        "cross_guideline_balanced"

        if profile.requires_multiple_sources

        else "semantic_reranked"

    )


    return {

        "query":
            query,

        "profile":
            profile.to_dict(),

        "retrieval_mode":
            retrieval_mode,

        "candidate_count":
            len(candidates),

        "results":
            final_results,

    }


# ============================================================
# DISPLAY
# ============================================================

def print_retrieval(
    result
):

    print("\n")
    print(
        "=" * 100
    )

    print("QUERY:")

    print(
        result["query"]
    )


    print("\nRETRIEVAL MODE:")

    print(
        result.get(
            "retrieval_mode"
        )
    )


    print("\nPROFILE:")


    for key, value in (
        result[
            "profile"
        ].items()
    ):

        print(
            f"{key}: {value}"
        )


    print(
        "\nCANDIDATES:",
        result.get(
            "candidate_count"
        )
    )


    print(
        "\nTOP RESULTS:"
    )


    for rank, row in enumerate(

        result[
            "results"
        ],

        start=1,

    ):

        print(
            "\n"
            + "-"
            * 100
        )


        print(
            f"Rank: {rank}"
        )


        print(
            f"Chunk: "
            f"{row.get('chunk_id')}"
        )


        print(
            f"Semantic: "
            f"{row.get('semantic_score', 0):.4f}"
        )


        print(
            f"Final: "
            f"{row.get('rerank_score', 0):.4f}"
        )


        print(
            f"Organization: "
            f"{row.get('organization')}"
        )


        print(
            f"Topic: "
            f"{row.get('topic')}"
        )


        print(
            f"Subtopic: "
            f"{row.get('subtopic')}"
        )


        print(
            f"Content: "
            f"{row.get('detected_content_type')}"
        )


        print(
            f"Priority: "
            f"{row.get('clinical_priority')}"
        )


        print(
            f"Canonical: "
            f"{row.get('is_canonical')}"
        )


        print(
            f"Page: "
            f"{row.get('pdf_page_start')}"
        )


        print(
            "Rerank reasons:"
        )


        for (
            reason,
            bonus
        ) in row.get(
            "rerank_reasons",
            []
        ):

            print(
                f"  {reason}: "
                f"{bonus:+.3f}"
            )


        print(
            "\nTEXT:"
        )


        print(

            row.get(
                "text",
                ""
            )[:1200]

        )


# ============================================================
# REGRESSION TESTS
# ============================================================

if __name__ == "__main__":

    TEST_QUERIES = [

        # Arabic prevention detection
        "ما هو مستوى LDL المستهدف للوقاية الثانوية من أمراض القلب؟",

        # Rationale
        "Why did NICE choose an LDL target of 2.0 mmol/L?",

        # Treatment initiation
        "When should pharmacological treatment for hypertension be started?",

        # Exact ID
        "What does NICE recommendation 1.7.1 say?",

        # Arabic muscle strategies
        "ما هي الإجراءات والاستراتيجيات السريرية التي يجب مناقشتها عندما يبلغ مريض يتناول ستاتين عالي الشدة عن ظهور آلام أو أعراض عضلية غير مبررة وفقاً لنايس؟",

        # Arabic risk underestimation
        "ما هي الحالات أو الفئات التي قد تؤدي إلى تقليل أدوات تقييم المخاطر مثل QRISK من تقدير الخطر القلبي الوعائي الفعلي للمريض وفقاً لنايس؟",

        # Cross-guideline
        "ما هي التوصيات المحددة المتعلقة بالنظام الغذائي ونمط الحياة للوقاية من الأمراض القلبية الوعائية وخفض ضغط الدم في كلا الدليلين؟",

        # Cross-guideline pregnancy
        "What are the explicit recommendations in both guidelines regarding the use of ACE inhibitors, ARBs, and statins during pregnancy?",

    ]


    for query in TEST_QUERIES:

        result = retrieve(
            query
        )

        print_retrieval(
            result
        )