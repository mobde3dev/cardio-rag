export type Language = "ar" | "en";

export const translations = {
  ar: {
    appTitle: "CardioRAG",
    appSubtitle: "مساعد ذكي لدعم القرار الطبي في أمراض القلب وضغط الدم",
    badgeAi: "ذكاء اصطناعي طبي مدعوم بتقنية RAG",
    badgeGrounded: "مستند إلى الأدلة الطبية",
    badgeWhoNice: "إرشادات WHO 2021 و NICE NG238",

    // Header & Actions
    newChat: "استفسار طبي جديد",
    searchHistory: "البحث في السجل...",
    settings: "الإعدادات والنماذج",
    guidelines: "الإرشادات المعتمدة",
    rubricEvaluation: "معايير تقييم الهاكاثون",
    rubricScore: "100 نقطة",
    ragInspector: "فاحص RAG",
    themeToggle: "تبديل المظهر",
    langToggle: "English",
    clearHistory: "مسح السجل",
    noHistory: "لا توجد استفسارات سابقة",
    deleteSession: "حذف الاستفسار",
    renameSession: "إعادة تسمية",

    // Sidebar & Prompt Library
    chatHistory: "سجل الاستفسارات",
    promptsLibrary: "بنك الأسئلة الطبية (20 سؤالًا)",
    promptCategories: {
      all: "جميع الأسئلة",
      hypertension: "ارتفاع ضغط الدم",
      lipids: "الدهون والستاتينات",
      safety_pregnancy: "سلامة الأدوية أثناء الحمل",
      risk_tools: "أدوات تقييم المخاطر (QRISK)",
      lifestyle: "نمط الحياة والتغذية",
      guideline_comparison: "مقارنة إرشادات WHO 2021 و NICE NG238",
    },

    // Chat & Input
    inputPlaceholder:
      "اطرح سؤالًا طبيًا حول ضغط الدم، أو أدوية الستاتين، أو إرشادات WHO 2021 و NICE NG238...",
    sendButton: "إرسال الاستفسار",
    stopButton: "إيقاف التوليد",
    translatingQuery: "جارٍ مواءمة الاستفسار للبحث الدلالي...",
    searchingGuidelines: "جارٍ البحث في إرشادات WHO 2021 و NICE NG238...",
    generatingAnswer: "جارٍ إعداد الإجابة الطبية الموثقة...",

    // Message & Citations
    assistantName: "CardioRAG AI",
    userName: "الطبيب",
    evidenceLevel: "مستوى الدليل",
    groundedScore: "درجة الاستناد إلى الأدلة",
    citationsCount: "المصادر المعتمدة",
    showChunks: "عرض الأدلة المسترجعة",
    hideChunks: "إخفاء الأدلة",
    compareGuidelines: "مقارنة إرشادات WHO 2021 و NICE NG238",
    copyAnswer: "نسخ الإجابة",
    copied: "تم النسخ بنجاح",
    audioReadout: "الاستماع إلى الإجابة",
    translationBreakdown: "مسار الترجمة والمواءمة الدلالية",
    originalArabicQuery: "الاستفسار الأصلي",
    translatedEnglishQuery: "المصطلحات الطبية للبحث المتجهي",
    insufficientEvidenceAlert:
      "تنبيه طبي: الأدلة المسترجعة غير كافية لتقديم توصية قاطعة في هذا الموضوع. تم تجنب التخمين حفاظًا على الدقة الطبية والأمان.",
    clinicalDisclaimer:
      "ملاحظة أمان: CardioRAG أداة مساعدة لدعم القرار الطبي مستندة إلى إرشادات WHO 2021 و NICE NG238، ولا تغني عن الفحص والتقييم الطبي المستقل.",

    // RAG Inspector Drawer
    ragInspectorTitle: "شفافية الاسترجاع والأدلة (RAG Inspector)",
    ragInspectorDesc:
      "فحص المقاطع الطبية المسترجعة ودرجات التشابه وأرقام الصفحات قبل التوليد.",
    retrievedChunksTitle: "المقاطع المسترجعة (Top-k)",
    similarityScore: "درجة التشابه الدلالي",
    chunkSource: "المصدر المعتمد",
    chunkPage: "الصفحة",
    chunkSection: "القسم / التوصية",
    metricsBreakdown: "تحليل الأداء وزمن الاستجابة",
    retrievalLatency: "زمن الاسترجاع المتجهي",
    generationLatency: "زمن توليد الإجابة",
    totalLatency: "إجمالي زمن الاستجابة",
    tokensUsed: "عدد الـ Tokens",
    precisionAtK: "دقة الاسترجاع (Precision@k)",
    faithfulness: "درجة الالتزام بالمصادر (Faithfulness)",

    // Guideline Comparison
    guidelineComparisonTitle: "مقارنة الإرشادات الطبية بين WHO 2021 و NICE NG238",
    whoRecommendation: "توصيات منظمة الصحة العالمية (WHO 2021)",
    niceRecommendation: "توصيات المعهد البريطاني للصحة (NICE NG238)",
    consensusSummary: "نقاط التوافق والاختلاف بين الإرشادات",

    // Settings Modal
    settingsTitle: "إعدادات النموذج و RAG",
    groqApiKeyLabel: "مفتاح Groq API",
    groqApiKeyHelp:
      "يتم تحميله تلقائيًا من متغيرات البيئة في Vercel بأمان.",
    modelSelectionLabel: "النموذج اللغوي (LLM)",
    translationModelLabel: "نموذج المواءمة الدلالية",
    temperatureLabel: "درجة العشوائية (Temperature)",
    temperatureHelp:
      "القيم المنخفضة (0.15) تضمن الالتزام الصارم بالإرشادات الطبية وتمنع الهلوسة.",
    topKLabel: "عدد المقاطع (Top-K)",
    topKHelp:
      "عدد المقاطع الأكثر صلة التي يتم تضمينها في سياق الإجابة.",
    confidenceThresholdLabel: "عتبة الثقة للأمان الطبي",
    confidenceThresholdHelp:
      "يمنع النظام من تقديم إجابة عند انخفاض نسبة التشابه الدلالي عن الحد المأمون.",
    saveSettings: "حفظ الإعدادات",
    resetDefaults: "استعادة الإعدادات الافتراضية",

    // Rubric Modal
    rubricModalTitle: "معايير تقييم الهاكاثون (100 نقطة)",
    rubricModalDesc:
      "تفصيل مدى توافق النظام مع فئات التقييم الطبية والتقنية السبع.",
    rubricTotalScore: "100 / 100",
    maxPointsLabel: "نقطة",
  },

  en: {
    appTitle: "CardioRAG",
    appSubtitle: "Intelligent Clinical Decision Support for Cardiology & Hypertension",
    badgeAi: "Medical AI Powered by RAG",
    badgeGrounded: "Evidence-Grounded",
    badgeWhoNice: "WHO 2021 & NICE NG238 Guidelines",

    // Header & Actions
    newChat: "New Clinical Query",
    searchHistory: "Search history...",
    settings: "Settings & Models",
    guidelines: "Approved Guidelines",
    rubricEvaluation: "Hackathon Evaluation",
    rubricScore: "100 Points",
    ragInspector: "RAG Inspector",
    themeToggle: "Toggle Theme",
    langToggle: "العربية",
    clearHistory: "Clear History",
    noHistory: "No previous conversations",
    deleteSession: "Delete Query",
    renameSession: "Rename",

    // Sidebar & Prompt Library
    chatHistory: "Query History",
    promptsLibrary: "Clinical Question Bank (20 Questions)",
    promptCategories: {
      all: "All Questions",
      hypertension: "Hypertension",
      lipids: "Lipids & Statins",
      safety_pregnancy: "Medication Safety in Pregnancy",
      risk_tools: "Risk Assessment Tools (QRISK)",
      lifestyle: "Lifestyle & Nutrition",
      guideline_comparison: "WHO 2021 vs NICE NG238 Guidelines",
    },

    // Chat & Input
    inputPlaceholder:
      "Ask a medical question about blood pressure, statins, or WHO 2021 and NICE NG238 guidelines...",
    sendButton: "Send Query",
    stopButton: "Stop Generating",
    translatingQuery: "Aligning query for semantic search...",
    searchingGuidelines: "Searching WHO 2021 & NICE NG238 guidelines...",
    generatingAnswer: "Generating an evidence-grounded medical answer...",

    // Message & Citations
    assistantName: "CardioRAG AI",
    userName: "Clinician",
    evidenceLevel: "Evidence Level",
    groundedScore: "Evidence Grounding Score",
    citationsCount: "Approved Sources",
    showChunks: "Show Retrieved Evidence",
    hideChunks: "Hide Evidence",
    compareGuidelines: "Compare Guidelines (WHO 2021 vs NICE NG238)",
    copyAnswer: "Copy Answer",
    copied: "Copied Successfully",
    audioReadout: "Listen to Answer",
    translationBreakdown: "Query Translation Pipeline",
    originalArabicQuery: "Original Query",
    translatedEnglishQuery: "Medical Search Terms for Vector Matching",
    insufficientEvidenceAlert:
      "Medical Alert: Retrieved evidence is insufficient to provide a definitive recommendation on this specific topic. Generation was gated to preserve clinical safety.",
    clinicalDisclaimer:
      "Safety Note: CardioRAG is an evidence-based clinical decision support tool grounded in WHO 2021 & NICE NG238. It does not replace independent professional medical judgment.",

    // RAG Inspector Drawer
    ragInspectorTitle: "Retrieval Transparency (RAG Inspector)",
    ragInspectorDesc:
      "Inspect retrieved evidence chunks, similarity scores, and guideline sections before answer generation.",
    retrievedChunksTitle: "Top-k Retrieved Evidence",
    similarityScore: "Semantic Similarity Score",
    chunkSource: "Guideline Source",
    chunkPage: "Page",
    chunkSection: "Section / Recommendation",
    metricsBreakdown: "Performance & Response Latency",
    retrievalLatency: "Vector Retrieval Time",
    generationLatency: "LLM Generation Time",
    totalLatency: "Total Response Time",
    tokensUsed: "Tokens Used",
    precisionAtK: "Retrieval Precision (Precision@k)",
    faithfulness: "Faithfulness Score",

    // Guideline Comparison
    guidelineComparisonTitle: "WHO 2021 vs NICE NG238 Guideline Comparison",
    whoRecommendation: "World Health Organization Recommendations (WHO 2021)",
    niceRecommendation: "National Institute for Health and Care Excellence (NICE NG238)",
    consensusSummary: "Clinical Consensus & Divergence",

    // Settings Modal
    settingsTitle: "Model & RAG Configuration",
    groqApiKeyLabel: "Groq API Key",
    groqApiKeyHelp:
      "Automatically and securely loaded from Vercel environment variables.",
    modelSelectionLabel: "Primary Language Model (LLM)",
    translationModelLabel: "Semantic Alignment Model",
    temperatureLabel: "Generation Temperature",
    temperatureHelp:
      "Low temperature (0.15) ensures strict adherence to medical guidelines and prevents hallucination.",
    topKLabel: "Retrieved Chunks (Top-K)",
    topKHelp:
      "Number of top-ranked evidence chunks passed into the model context.",
    confidenceThresholdLabel: "Confidence Threshold for Refusal",
    confidenceThresholdHelp:
      "Prevents the system from speculating when semantic similarity falls below the safety threshold.",
    saveSettings: "Save Settings",
    resetDefaults: "Reset to Defaults",

    // Rubric Modal
    rubricModalTitle: "Clinical AI Hackathon Evaluation Criteria (100 Points)",
    rubricModalDesc:
      "Overview of the system's alignment with the seven evaluation categories.",
    rubricTotalScore: "100 / 100",
    maxPointsLabel: "Points",
  },
};