import re
from dataclasses import dataclass, asdict, field
from typing import Optional


# ============================================================
# DATA MODEL
# ============================================================

@dataclass
class QueryProfile:

    language: str = "unknown"

    # Single explicit organization
    organization: Optional[str] = None

    # Multiple organizations for comparison questions
    organizations: list[str] = field(default_factory=list)

    # Primary topic kept for backwards compatibility
    topic: Optional[str] = None

    # Some questions genuinely require more than one topic
    topic_hints: list[str] = field(default_factory=list)

    prevention_type: Optional[str] = None

    # recommendation | rationale | None
    content_preference: Optional[str] = None

    recommendation_id: Optional[str] = None

    # More specific routing intent
    intent: Optional[str] = None

    complexity: str = "single"

    requires_multiple_sources: bool = False

    requires_table: bool = False

    requires_algorithm: bool = False

    confidence: float = 0.0

    def to_dict(self):
        return asdict(self)


# ============================================================
# TEXT HELPERS
# ============================================================

def normalize_arabic(text: str) -> str:

    text = text.lower().strip()

    # Remove Arabic diacritics
    text = re.sub(
        r"[\u064B-\u065F\u0670]",
        "",
        text
    )

    replacements = {
        "أ": "ا",
        "إ": "ا",
        "آ": "ا",
        "ى": "ي",
        "ؤ": "و",
        "ئ": "ي",
        "ة": "ه",
        "ـ": "",
    }

    for old, new in replacements.items():
        text = text.replace(old, new)

    text = re.sub(
        r"\s+",
        " ",
        text
    )

    return text.strip()


def contains_any(
    text: str,
    keywords: list[str]
) -> bool:

    return any(
        keyword in text
        for keyword in keywords
    )


def regex_any(
    text: str,
    patterns: list[str]
) -> bool:

    return any(
        re.search(
            pattern,
            text,
            flags=re.IGNORECASE
        )
        for pattern in patterns
    )


def detect_language(query: str) -> str:

    arabic_chars = re.findall(
        r"[\u0600-\u06FF]",
        query
    )

    if len(arabic_chars) >= 2:
        return "ar"

    return "en"


def extract_recommendation_id(
    query: str
) -> Optional[str]:

    patterns = [

        # NICE style
        r"\b1\.\d+\.\d+\b",

        # WHO section/recommendation style
        r"\b3\.\d+\b",

    ]

    for pattern in patterns:

        match = re.search(
            pattern,
            query
        )

        if match:
            return match.group(0)

    return None


def set_topics(
    profile: QueryProfile,
    topics: list[str],
    confidence: float
):

    unique_topics = []

    for topic in topics:

        if topic not in unique_topics:
            unique_topics.append(topic)

    profile.topic_hints = unique_topics

    if unique_topics:
        profile.topic = unique_topics[0]

    profile.confidence = max(
        profile.confidence,
        confidence
    )


# ============================================================
# QUERY CLASSIFIER
# ============================================================

def classify_query(
    query: str
) -> QueryProfile:

    q = query.lower().strip()

    q_ar = normalize_arabic(
        query
    )

    profile = QueryProfile()

    profile.language = detect_language(
        query
    )

    profile.recommendation_id = (
        extract_recommendation_id(
            query
        )
    )


    # ========================================================
    # 1. CROSS-GUIDELINE DETECTION
    # ========================================================

    cross_guideline_patterns_en = [

        r"\bboth guidelines\b",

        r"\bwho\s+(?:and|&)\s+nice\b",

        r"\bnice\s+(?:and|&)\s+who\b",

        r"\bcompare\b.*\bwho\b.*\bnice\b",

        r"\bcompare\b.*\bnice\b.*\bwho\b",

    ]


    cross_guideline_ar = [

        "كلا الدليلين",

        "في الدليلين",

        "بين الدليلين",

        "التوصيات المشتركه في الدليلين",

        "منظمه الصحه العالميه ودليل نايس",

        "منظمه الصحه العالميه ونايس",

        "who و nice",

        "nice و who",

        "قارن بين نهج",

        "قارن بين دليل",

        "كل من دليل",

    ]


    is_cross_guideline = (

        regex_any(
            q,
            cross_guideline_patterns_en
        )

        or

        contains_any(
            q_ar,
            cross_guideline_ar
        )
    )


    if is_cross_guideline:

        profile.organizations = [
            "WHO",
            "NICE"
        ]

        profile.requires_multiple_sources = True

        profile.complexity = (
            "cross_guideline"
        )


    # ========================================================
    # 2. SINGLE ORGANIZATION
    # ========================================================

    if not profile.requires_multiple_sources:

        nice_patterns = [

            r"\bnice\b",

            r"\baccording to nice\b",

        ]

        who_patterns = [

            r"\bwho\b",

            r"\bworld health organization\b",

            r"\baccording to who\b",

        ]


        if (
            regex_any(
                q,
                nice_patterns
            )

            or contains_any(
                q_ar,
                [
                    "نايس",
                    "ارشادات نايس",
                    "دليل نايس",
                ]
            )
        ):

            profile.organization = "NICE"

            profile.organizations = [
                "NICE"
            ]


        elif (
            regex_any(
                q,
                who_patterns
            )

            or contains_any(
                q_ar,
                [
                    "منظمه الصحه العالميه",
                    "دليل منظمه الصحه العالميه",
                ]
            )
        ):

            profile.organization = "WHO"

            profile.organizations = [
                "WHO"
            ]


    # ========================================================
    # 3. CONTENT INTENT
    #
    # IMPORTANT:
    # Do NOT use generic Arabic word "مبرر".
    # It incorrectly matches "غير مبررة".
    # ========================================================

    rationale_patterns_en = [

        r"\bwhy\b",

        r"\brationale\b",

        r"\breason(?:s)?\s+(?:for|behind)\b",

        r"\bwhy did\b",

        r"\bevidence behind\b",

    ]


    rationale_patterns_ar = [

        r"لماذا",

        r"ليه",

        r"ما السبب",

        r"ما هي الاسباب",

        r"ما اسباب",

        r"ما المبرر",

        r"سبب اختيار",

        r"لم اختار",

        r"لماذا اختار",

    ]


    if (
        regex_any(
            q,
            rationale_patterns_en
        )

        or

        regex_any(
            q_ar,
            rationale_patterns_ar
        )
    ):

        profile.content_preference = (
            "rationale"
        )


    else:

        recommendation_patterns_en = [

            r"\brecommend(?:ed|ation)?\b",

            r"\bwhat should\b",

            r"\bwhat strategies\b",

            r"\bwhat clinical strategies\b",

            r"\bwhat actions\b",

            r"\bhow should\b",

            r"\bwhen should\b",

            r"\bwhat are the recommended\b",

            r"\bwhat is the recommended\b",

            r"\btarget\b",

            r"\bfirst[- ]line\b",

        ]


        recommendation_patterns_ar = [

            r"ما هي التوصيات",

            r"ما هي الاجراءات",

            r"ما هي الاستراتيجيات",

            r"ما الاجراءات",

            r"ماذا يجب",

            r"كيف يتم التعامل",

            r"كيف توجه",

            r"متي يجب",

            r"متي ينصح",

            r"الموصي بها",

            r"الموصى بها",

            r"المستهدف",

            r"الهدف",

            r"العلاج الاولي",

            r"الخط الاول",

        ]


        if (
            regex_any(
                q,
                recommendation_patterns_en
            )

            or

            regex_any(
                q_ar,
                recommendation_patterns_ar
            )
        ):

            profile.content_preference = (
                "recommendation"
            )


    # ========================================================
    # 4. PREVENTION TYPE
    # ========================================================

    secondary_terms = [

        "secondary prevention",

        "established cvd",

        "known cvd",

        "existing cardiovascular disease",

    ]


    secondary_ar = [

        "الوقايه الثانويه",

        "للوقايه الثانويه",

        "وقايه ثانويه",

        "الوقايه من الدرجه الثانويه",

    ]


    primary_terms = [

        "primary prevention",

        "without cardiovascular disease",

        "without cvd",

    ]


    primary_ar = [

        "الوقايه الاوليه",

        "للوقايه الاوليه",

        "وقايه اوليه",

    ]


    if (
        contains_any(
            q,
            secondary_terms
        )

        or

        contains_any(
            q_ar,
            secondary_ar
        )
    ):

        profile.prevention_type = (
            "secondary"
        )


    elif (
        contains_any(
            q,
            primary_terms
        )

        or

        contains_any(
            q_ar,
            primary_ar
        )
    ):

        profile.prevention_type = (
            "primary"
        )


    # ========================================================
    # 5. VERY SPECIFIC INTENTS FIRST
    # ========================================================


    # --------------------------------------------------------
    # TRIGLYCERIDE URGENT REFERRAL
    # --------------------------------------------------------

    if (

        contains_any(
            q,
            [
                "triglyceride",
                "triglycerides",
            ]
        )

        and

        contains_any(
            q,
            [
                "urgent",
                "specialist",
                "referral",
                "review",
            ]
        )

    ) or (

        contains_any(
            q_ar,
            [
                "الدهون الثلاثيه",
                "ثلاثي الجليسريد",
                "triglycerides",
            ]
        )

        and

        contains_any(
            q_ar,
            [
                "عاجل",
                "تخصصي",
                "اخصايي",
                "احاله",
                "تقييم",
            ]
        )

    ):

        profile.intent = (
            "urgent_triglyceride_referral"
        )

        set_topics(
            profile,
            [
                "lipid_assessment",
            ],
            0.98
        )

        profile.content_preference = (
            "recommendation"
        )


    # --------------------------------------------------------
    # NONPHYSICIAN MANAGEMENT
    # --------------------------------------------------------

    elif (
        contains_any(
            q,
            [
                "nonphysician",
                "non-physician",
                "pharmacists",
                "pharmacist",
                "nurses",
                "nurse",
            ]
        )

        and

        contains_any(
            q,
            [
                "hypertension",
                "antihypertensive",
                "pharmacological treatment",
            ]
        )

    ) or (

        contains_any(
            q_ar,
            [
                "غير الاطباء",
                "غير الطبيب",
                "الصيادله",
                "الصيادله والممرضين",
                "الممرضين",
            ]
        )

    ):

        profile.intent = (
            "nonphysician_management"
        )

        set_topics(
            profile,
            [
                "nonphysician_management",
            ],
            0.98
        )


    # --------------------------------------------------------
    # STATIN INTENSITY TABLE
    # --------------------------------------------------------

    elif (

        contains_any(
            q,
            [
                "statin",
                "statins",
            ]
        )

        and

        contains_any(
            q,
            [
                "high intensity",
                "high-intensity",
                "medium intensity",
                "low intensity",
                "categorized",
                "categorised",
                "classification",
                "dosage",
                "dosages",
            ]
        )

    ) or (

        contains_any(
            q_ar,
            [
                "الستاتين",
                "statins",
            ]
        )

        and

        contains_any(
            q_ar,
            [
                "تصنيف",
                "الشده",
                "مرتفعه",
                "متوسطه",
                "منخفضه",
                "الجرعه",
                "الجرعات",
            ]
        )

    ):

        profile.intent = (
            "statin_intensity"
        )

        profile.requires_table = True

        profile.complexity = (
            "table"
        )

        set_topics(
            profile,
            [
                "statin_pre_treatment_assessment",
                "lipid_lowering_treatment",
                "statin_optimization",
            ],
            0.95
        )


    # --------------------------------------------------------
    # DO NOT USE CVD RISK TOOL
    # --------------------------------------------------------

    elif (
        regex_any(
            q,
            [
                r"\bdo not use\b.*\brisk\b.*\btool\b",

                r"\bshould not\b.*\brisk\b.*\btool\b",

                r"\bnot be assessed\b.*\brisk\b.*\btool\b",

                r"\balready considered\b.*\bhigh risk\b",
            ]
        )

        or

        contains_any(
            q_ar,
            [
                "لا ينبغي استخدام ادوات تقييم المخاطر",

                "لا ينبغي استخدام اداه تقييم المخاطر",

                "تعتبر بالفعل عاليه الخطوره",

                "عاليه الخطوره بالفعل",
            ]
        )
    ):

        profile.intent = (
            "no_risk_tool"
        )

        set_topics(
            profile,
            [
                "cardiovascular_risk_assessment",
            ],
            0.98
        )


    # --------------------------------------------------------
    # CVD RISK UNDERESTIMATION
    # --------------------------------------------------------

    elif (
        regex_any(
            q,
            [
                r"\bunderestimate\b",

                r"\bunderestimated\b",

                r"\btrue cardiovascular risk\b",

                r"\btrue cvd risk\b",
            ]
        )

        or

        contains_any(
            q_ar,
            [
                "تقليل ادوات تقييم المخاطر",

                "تقلل ادوات تقييم المخاطر",

                "تقلل من تقدير",

                "تقليل تقدير",

                "الخطر الفعلي",

                "الخطر الحقيقي",

                "تقدير الخطر القلبي الوعايي الفعلي",
            ]
        )
    ):

        profile.intent = (
            "risk_underestimation"
        )

        set_topics(
            profile,
            [
                "cardiovascular_risk_assessment",
            ],
            0.98
        )


    # --------------------------------------------------------
    # FOLLOW-UP INTERVAL
    # --------------------------------------------------------

    elif (
        contains_any(
            q,
            [
                "follow-up interval",
                "follow up interval",
                "follow-up intervals",
                "follow up intervals",
                "once blood pressure is controlled",
                "after initiating",
                "after changing antihypertensive",
                "reassessment",
            ]
        )

        or

        contains_any(
            q_ar,
            [
                "الجدول الزمني",
                "اعاده قياس ضغط الدم",
                "متابعه المريض",
                "بعد بدء العلاج",
                "بعد تغيير",
                "عند استقرار الضغط",
                "فترات المتابعه",
            ]
        )
    ):

        profile.intent = (
            "follow_up"
        )

        set_topics(
            profile,
            [
                "follow_up",
            ],
            0.98
        )


    # --------------------------------------------------------
    # BASELINE STATIN ASSESSMENT
    # --------------------------------------------------------

    elif (
        contains_any(
            q,
            [
                "before starting statin",
                "before starting statin therapy",
                "baseline laboratory",
                "baseline blood tests",
                "baseline clinical assessment",
                "before offering a statin",
            ]
        )

        or

        contains_any(
            q_ar,
            [
                "قبل البدء في استخدام الستاتين",
                "قبل البدء بالستاتين",
                "الفحوصات المخبريه والسريريه الاساسيه",
                "الفحوصات الاساسيه",
                "قبل وصف الستاتين",
            ]
        )
    ):

        profile.intent = (
            "baseline_statin_assessment"
        )

        set_topics(
            profile,
            [
                "statin_pre_treatment_assessment",
            ],
            0.98
        )


    # --------------------------------------------------------
    # CK MANAGEMENT
    # --------------------------------------------------------

    elif (
        contains_any(
            q,
            [
                "creatine kinase",
                "ck level",
                "ck levels",
            ]
        )

        or

        contains_any(
            q_ar,
            [
                "الكرياتين كينيز",
                "creatine kinase",
                "مستويات ck",
            ]
        )
    ):

        profile.intent = (
            "ck_management"
        )

        set_topics(
            profile,
            [
                "statin_pre_treatment_assessment",
                "treatment_monitoring",
            ],
            0.98
        )


    # --------------------------------------------------------
    # WHO ALGORITHM 1
    # --------------------------------------------------------

    elif (
        contains_any(
            q,
            [
                "algorithm 1",
                "single-pill combination",
                "single pill combination",
                "sequential steps",
            ]
        )

        or

        contains_any(
            q_ar,
            [
                "algorithm 1",
                "بروتوكول منظمه الصحه العالميه",
                "حبه واحده",
                "علاج مركب في حبه واحده",
                "الخطوات العلاجيه",
            ]
        )
    ):

        profile.intent = (
            "algorithm_1"
        )

        profile.requires_algorithm = True

        profile.complexity = (
            "algorithm"
        )

        set_topics(
            profile,
            [
                "combination_therapy",
                "pharmacological_treatment",
            ],
            0.98
        )


    # --------------------------------------------------------
    # PREGNANCY
    # --------------------------------------------------------

    elif (
        contains_any(
            q,
            [
                "pregnancy",
                "pregnant",
                "conception",
                "breastfeeding",
            ]
        )

        or

        contains_any(
            q_ar,
            [
                "الحمل",
                "الحامل",
                "اثناء الحمل",
                "قبل الحمل",
                "الرضاعه",
            ]
        )
    ):

        profile.intent = (
            "pregnancy"
        )

        set_topics(
            profile,
            [
                "pharmacological_treatment",
                "statin_pre_treatment_assessment",
                "lipid_lowering_treatment",
            ],
            0.95
        )


    # --------------------------------------------------------
    # LAB TESTING + CVD RISK DELAY
    # --------------------------------------------------------

    elif (
        (
            contains_any(
                q,
                [
                    "laboratory testing",
                    "laboratory tests",
                    "risk assessment",
                ]
            )

            and

            contains_any(
                q,
                [
                    "delay",
                    "initiation",
                    "starting treatment",
                ]
            )
        )

        or

        (
            contains_any(
                q_ar,
                [
                    "الفحوصات المخبريه",
                    "تقييم المخاطر",
                ]
            )

            and

            contains_any(
                q_ar,
                [
                    "تاخير",
                    "بدء العلاج",
                ]
            )
        )
    ):

        profile.intent = (
            "lab_and_risk_delay"
        )

        set_topics(
            profile,
            [
                "laboratory_testing",
                "cardiovascular_risk_assessment",
                "treatment_initiation",
            ],
            0.95
        )


    # --------------------------------------------------------
    # STATIN MUSCLE ADVERSE EFFECT STRATEGIES
    # --------------------------------------------------------

    elif (
        (
            contains_any(
                q,
                [
                    "muscle effects",
                    "muscle symptoms",
                    "muscle pain",
                    "adverse muscle",
                    "adverse effects",
                ]
            )

            and

            contains_any(
                q,
                [
                    "statin",
                    "high-intensity statin",
                    "high intensity statin",
                ]
            )
        )

        or

        (
            contains_any(
                q_ar,
                [
                    "اعراض عضليه",
                    "الام عضليه",
                    "الم عضلي",
                    "اثار عضليه",
                    "اعراض عضليه غير مبرره",
                ]
            )

            and

            contains_any(
                q_ar,
                [
                    "ستاتين",
                    "الستاتين",
                    "عالي الشده",
                ]
            )
        )
    ):

        profile.intent = (
            "statin_muscle_adverse_effects"
        )

        profile.content_preference = (
            "recommendation"
        )

        set_topics(
            profile,
            [
                "statin_optimization",
                "treatment_monitoring",
                "statin_pre_treatment_assessment",
            ],
            0.99
        )


    # --------------------------------------------------------
    # TREATMENTS NICE SAYS NOT TO OFFER
    # --------------------------------------------------------

    elif (
        (
            contains_any(
                q,
                [
                    "not offering",
                    "not offer",
                    "do not offer",
                    "not recommended",
                ]
            )

            and

            contains_any(
                q,
                [
                    "lipid",
                    "supplements",
                    "cvd",
                ]
            )
        )

        or

        contains_any(
            q_ar,
            [
                "عدم استخدامها للوقايه",
                "لا توصي باستخدامها",
                "عدم تقديمها",
                "صراحه بعدم استخدامها",
                "المكملات الغذائيه الخافضه للدهون",
            ]
        )
    ):

        profile.intent = (
            "treatments_not_recommended"
        )

        set_topics(
            profile,
            [
                "treatments_not_recommended",
            ],
            0.98
        )


    # --------------------------------------------------------
    # NON-STATIN ALTERNATIVES
    # --------------------------------------------------------

    elif (
        (
            contains_any(
                q,
                [
                    "non-statin",
                    "non statin",
                    "statins are contraindicated",
                    "statins contraindicated",
                    "not tolerated",
                    "statin intolerance",
                ]
            )
        )

        or

        contains_any(
            q_ar,
            [
                "غير الستاتينيه",
                "لا يتحملون الستاتين",
                "موانع لاستخدامه",
                "موانع استخدام الستاتين",
                "عدم تحمل الستاتين",
            ]
        )
    ):

        profile.intent = (
            "statin_intolerance"
        )

        set_topics(
            profile,
            [
                "statin_intolerance",
            ],
            0.98
        )


    # --------------------------------------------------------
    # DIABETES + CKD
    # --------------------------------------------------------

    elif (
        (
            contains_any(
                q,
                [
                    "diabetes",
                    "type 1",
                    "type 2",
                ]
            )

            and

            contains_any(
                q,
                [
                    "ckd",
                    "chronic kidney disease",
                ]
            )
        )

        or

        (
            contains_any(
                q_ar,
                [
                    "السكري",
                    "النوع الاول",
                    "النوع الثاني",
                ]
            )

            and

            contains_any(
                q_ar,
                [
                    "الاعتلال الكلوي المزمن",
                    "مرض الكلي المزمن",
                    "ckd",
                ]
            )
        )
    ):

        profile.intent = (
            "diabetes_ckd"
        )

        set_topics(
            profile,
            [
                "cardiovascular_risk_assessment",
                "treatment_initiation",
                "lipid_lowering_treatment",
            ],
            0.92
        )


    # --------------------------------------------------------
    # LIFESTYLE / DIET
    # --------------------------------------------------------

    elif (
        contains_any(
            q,
            [
                "dietary",
                "diet",
                "lifestyle",
                "physical activity",
                "weight management",
                "blood pressure reduction",
            ]
        )

        or

        contains_any(
            q_ar,
            [
                "النظام الغذائي",
                "نمط الحياه",
                "النشاط البدني",
                "خفض ضغط الدم",
                "انقاص الوزن",
                "الوقايه من الامراض القلبيه",
            ]
        )
    ):

        profile.intent = (
            "lifestyle"
        )

        set_topics(
            profile,
            [
                "lifestyle",
            ],
            0.90
        )


    # --------------------------------------------------------
    # COMBINATION vs LIPID ESCALATION
    # --------------------------------------------------------

    elif (
        (
            contains_any(
                q,
                [
                    "combination therapy",
                    "step-by-step",
                    "step by step",
                    "escalation",
                    "lipid management",
                ]
            )

            and

            profile.requires_multiple_sources
        )

        or

        (
            contains_any(
                q_ar,
                [
                    "العلاج المركب",
                    "التصعيد التدريجي",
                    "تصعيد علاج الدهون",
                ]
            )

            and

            profile.requires_multiple_sources
        )
    ):

        profile.intent = (
            "treatment_strategy_comparison"
        )

        set_topics(
            profile,
            [
                "combination_therapy",
                "lipid_lowering_treatment",
                "statin_optimization",
            ],
            0.95
        )


    # ========================================================
    # 6. GENERAL TOPIC ROUTING
    # ========================================================


    # --------------------------------------------------------
    # BP 130-139 + target = multi-topic
    # --------------------------------------------------------

    elif (
        (
            "130" in q
            and "139" in q
            and contains_any(
                q,
                [
                    "blood pressure",
                    "sbp",
                    "hypertension",
                ]
            )
        )

        or

        (
            "130" in q_ar
            and "139" in q_ar
            and contains_any(
                q_ar,
                [
                    "ضغط",
                    "انقباضي",
                ]
            )
        )
    ):

        profile.intent = (
            "sbp_130_139"
        )

        set_topics(
            profile,
            [
                "treatment_initiation",
                "blood_pressure_target",
            ],
            0.98
        )


    # --------------------------------------------------------
    # COMBINATION THERAPY
    # --------------------------------------------------------

    elif (
        contains_any(
            q,
            [
                "combination therapy",
                "single pill",
                "single-pill",
                "combination medication",
            ]
        )

        or

        contains_any(
            q_ar,
            [
                "العلاج المركب",
                "العلاج المزدوج",
                "قرص واحد",
                "حبه واحده",
            ]
        )
    ):

        profile.intent = (
            "combination_therapy"
        )

        set_topics(
            profile,
            [
                "combination_therapy",
            ],
            0.95
        )


    # --------------------------------------------------------
    # BP TARGET
    # --------------------------------------------------------

    elif (
        contains_any(
            q,
            [
                "blood pressure target",
                "target blood pressure",
                "target systolic",
                "bp target",
            ]
        )

        or

        contains_any(
            q_ar,
            [
                "ضغط الدم المستهدف",
                "هدف ضغط الدم",
                "الضغط المستهدف",
            ]
        )
    ):

        profile.intent = (
            "blood_pressure_target"
        )

        set_topics(
            profile,
            [
                "blood_pressure_target",
            ],
            0.95
        )


    # --------------------------------------------------------
    # TREATMENT INITIATION
    # --------------------------------------------------------

    elif (
        regex_any(
            q,
            [
                r"\bwhen\b.*\b(?:treatment|therapy)\b.*\b(?:start|started|begin|initiated)\w*",

                r"\bwhen\b.*\b(?:start|begin|initiat)\w*.*\b(?:treatment|therapy)\b",

                r"\bwhen should pharmacological treatment\b",

                r"\btreatment threshold\b",

                r"\bblood pressure threshold\b",

                r"\binitiat(?:e|ion|ing)\b.*\btreatment\b",
            ]
        )

        or

        contains_any(
            q_ar,
            [
                "متي نبدا",
                "متي يبدا",
                "متي ينصح ببدء",
                "بدء العلاج",
                "عتبه العلاج",
                "مستوي بدء العلاج",
            ]
        )
    ):

        profile.intent = (
            "treatment_initiation"
        )

        set_topics(
            profile,
            [
                "treatment_initiation",
            ],
            0.97
        )


    # --------------------------------------------------------
    # FIRST-LINE HTN DRUGS
    # --------------------------------------------------------

    elif (
        contains_any(
            q,
            [
                "first-line",
                "first line",
                "antihypertensive drug classes",
                "initial treatment for hypertension",
                "ace inhibitor",
                "acei",
                "arb",
                "ccb",
                "thiazide",
            ]
        )

        or

        contains_any(
            q_ar,
            [
                "ادويه الخط الاول",
                "الفئات الدواييه الثلاث",
                "العلاج الاولي للبالغين",
                "دواء الضغط",
                "ادويه الضغط",
                "مثبطات ace",
            ]
        )
    ):

        profile.intent = (
            "first_line_htn"
        )

        set_topics(
            profile,
            [
                "pharmacological_treatment",
            ],
            0.98
        )


    # --------------------------------------------------------
    # LIPIDS / STATINS
    # --------------------------------------------------------

    elif (
        contains_any(
            q,
            [
                "ldl",
                "hdl",
                "non-hdl",
                "cholesterol",
                "statin",
                "atorvastatin",
                "ezetimibe",
                "lipid",
                "lipids",
                "triglyceride",
            ]
        )

        or

        contains_any(
            q_ar,
            [
                "كوليسترول",
                "الكوليسترول",
                "دهون الدم",
                "الدهون الثلاثيه",
                "ستاتين",
                "اتورفاستاتين",
                "ايزيتيميب",
            ]
        )
    ):

        profile.intent = (
            "lipid_management"
        )

        set_topics(
            profile,
            [
                "lipid_lowering_treatment",
            ],
            0.95
        )


    # --------------------------------------------------------
    # CVD RISK
    # --------------------------------------------------------

    elif (
        contains_any(
            q,
            [
                "qrisk",
                "qrisk3",
                "cardiovascular risk",
                "cvd risk",
                "risk assessment",
                "risk score",
            ]
        )

        or

        contains_any(
            q_ar,
            [
                "مخاطر القلب",
                "خطر القلب",
                "تقييم المخاطر",
                "مخاطر امراض القلب",
                "qrisk",
            ]
        )
    ):

        profile.intent = (
            "cvd_risk"
        )

        set_topics(
            profile,
            [
                "cardiovascular_risk_assessment",
            ],
            0.90
        )


    # ========================================================
    # 7. FALLBACK
    # ========================================================

    if profile.confidence == 0:

        profile.confidence = 0.30


    return profile


# ============================================================
# QUICK DEBUG
# ============================================================

if __name__ == "__main__":

    TESTS = [

        "When should pharmacological treatment for hypertension be started?",

        "Why did NICE choose an LDL target of 2.0 mmol/L?",

        "What does NICE recommendation 1.7.1 say?",

        "ما هو مستوى LDL المستهدف للوقاية الثانوية من أمراض القلب؟",

        "ما هي الإجراءات والاستراتيجيات السريرية التي يجب مناقشتها عندما يبلغ مريض يتناول ستاتين عالي الشدة عن ظهور آلام أو أعراض عضلية غير مبررة وفقاً لنايس؟",

        "ما هي الحالات أو الفئات التي قد تؤدي إلى تقليل أدوات تقييم المخاطر مثل QRISK من تقدير الخطر القلبي الوعائي الفعلي للمريض وفقاً لنايس؟",

        "ما هي التوصيات المحددة المتعلقة بالنظام الغذائي ونمط الحياة للوقاية من الأمراض القلبية الوعائية وخفض ضغط الدم في كلا الدليلين؟",

    ]


    for query in TESTS:

        profile = classify_query(
            query
        )

        print("\n" + "=" * 100)
        print(query)

        print(
            profile.to_dict()
        )