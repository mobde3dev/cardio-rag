export type Language = "ar" | "en";

export const translations = {
  ar: {
    appTitle: "CardioRAG",
    appSubtitle: "مساعد سريري ذكي لدعم القرار في أمراض القلب",
    badgeAi: "ذكاء سريري مدعوم بتقنية RAG",
    badgeGrounded: "مدعوم بالأدلة السريرية",
    badgeWhoNice: "إرشادات NICE وWHO",

    // Header & Actions
    newChat: "استفسار سريري جديد",
    searchHistory: "البحث في السجل السريري...",
    settings: "الإعدادات والنماذج",
    guidelines: "الإرشادات المفهرسة",
    rubricEvaluation: "معايير تقييم الهاكاثون",
    rubricScore: "100 نقطة",
    ragInspector: "فاحص RAG",
    themeToggle: "تبديل المظهر",
    langToggle: "English",
    clearHistory: "مسح السجل",
    noHistory: "لا توجد محادثات سابقة",
    deleteSession: "حذف المحادثة",
    renameSession: "إعادة تسمية",

    // Sidebar & Prompt Library
    chatHistory: "سجل المحادثات",
    promptsLibrary: "بنك الأسئلة السريرية (20 سؤالًا)",
    promptCategories: {
      all: "جميع الأسئلة",
      hypertension: "ارتفاع ضغط الدم",
      lipids: "الدهون والستاتينات",
      safety_pregnancy: "سلامة الأدوية أثناء الحمل",
      risk_tools: "أدوات تقييم المخاطر (QRISK)",
      lifestyle: "نمط الحياة والتغذية",
      guideline_comparison: "مقارنة إرشادات WHO وNICE",
    },

    // Chat & Input
    inputPlaceholder:
      "اطرح سؤالًا سريريًا حول ضغط الدم، أو أدوية الستاتين، أو إرشادات NICE وWHO...",
    sendButton: "إرسال الاستفسار",
    stopButton: "إيقاف التوليد",
    translatingQuery: "جارٍ ترجمة الاستفسار لإجراء البحث الدلالي...",
    searchingGuidelines: "جارٍ البحث في إرشادات NICE وWHO...",
    generatingAnswer: "جارٍ توليد إجابة سريرية مستندة إلى الأدلة...",

    // Message & Citations
    assistantName: "CardioRAG AI",
    userName: "الطبيب / المستخدم",
    evidenceLevel: "مستوى الدليل",
    groundedScore: "درجة الاستناد إلى الأدلة",
    citationsCount: "عدد الاستشهادات",
    showChunks: "عرض المقاطع المسترجعة",
    hideChunks: "إخفاء المقاطع",
    compareGuidelines: "مقارنة الإرشادات (WHO وNICE)",
    copyAnswer: "نسخ الإجابة",
    copied: "تم النسخ بنجاح",
    audioReadout: "الاستماع إلى الإجابة",
    translationBreakdown: "تفاصيل مسار ترجمة الاستفسار",
    originalArabicQuery: "الاستفسار الأصلي",
    translatedEnglishQuery: "الاستفسار المترجم للبحث في فضاء المتجهات",
    insufficientEvidenceAlert:
      "تنبيه سريري: الأدلة المسترجعة غير كافية لتقديم توصية حاسمة. يُرجى تجنب الاستنتاجات غير المدعومة بالأدلة.",
    clinicalDisclaimer:
      "ملاحظة للسلامة السريرية: هذا النظام أداة لدعم القرار السريري ومخصص للمتخصصين في الرعاية الصحية، ولا يُغني عن التقييم والحكم السريري الشامل.",

    // RAG Inspector Drawer
    ragInspectorTitle: "فاحص الاسترجاع الدلالي (RAG Inspector)",
    ragInspectorDesc:
      "فحص المقاطع المسترجعة ودرجات التشابه وأقسام الإرشادات قبل توليد الإجابة.",
    retrievedChunksTitle: "المقاطع المسترجعة (Top-k)",
    similarityScore: "درجة التشابه الدلالي",
    chunkSource: "المصدر والمعرّف",
    chunkPage: "الصفحة",
    chunkSection: "القسم السريري",
    metricsBreakdown: "تحليل الأداء وزمن الاستجابة",
    retrievalLatency: "زمن الاسترجاع المتجهي",
    generationLatency: "زمن توليد الإجابة بواسطة LLM",
    totalLatency: "إجمالي زمن الاستجابة",
    tokensUsed: "عدد الـTokens المستخدمة",
    precisionAtK: "دقة الاسترجاع (Precision@k)",
    faithfulness: "درجة الالتزام بالمصادر (Faithfulness)",

    // Guideline Comparison
    guidelineComparisonTitle: "مقارنة الإرشادات الطبية بين WHO وNICE",
    whoRecommendation: "توصيات منظمة الصحة العالمية (WHO 2021)",
    niceRecommendation:
      "توصيات المعهد الوطني للصحة والرعاية (NICE NG136 / NG238)",
    consensusSummary: "نقاط الاتفاق والاختلاف السريرية",

    // Settings Modal
    settingsTitle: "إعدادات Groq وRAG",
    groqApiKeyLabel: "مفتاح Groq API",
    groqApiKeyHelp:
      "يتم تحميله تلقائيًا من متغيرات البيئة في Vercel، ويمكنك تغييره محليًا لأغراض الاختبار.",
    modelSelectionLabel: "نموذج اللغة الأساسي (LLM)",
    translationModelLabel: "نموذج الترجمة والاستخلاص",
    temperatureLabel: "درجة العشوائية في التوليد (Temperature)",
    temperatureHelp:
      "تساعد القيم المنخفضة (0.1 - 0.2) على تقليل الهلوسة والالتزام بشكل أكبر بالإرشادات.",
    topKLabel: "عدد المقاطع المسترجعة (Top-K)",
    topKHelp:
      "عدد المقاطع المسترجعة من قاعدة المتجهات التي يتم تمريرها إلى سياق النموذج.",
    confidenceThresholdLabel: "عتبة الثقة لرفض التخمين",
    confidenceThresholdHelp:
      "يمنع النظام من تقديم إجابة حاسمة عندما تكون درجة التشابه الدلالي أقل من العتبة المحددة.",
    saveSettings: "حفظ الإعدادات",
    resetDefaults: "استعادة الإعدادات الافتراضية",

    // Rubric Modal
    rubricModalTitle: "معايير تقييم الهاكاثون للذكاء الاصطناعي السريري (100 نقطة)",
    rubricModalDesc:
      "تفصيل مدى توافق النظام مع فئات التقييم السريري والتقني السبع.",
    rubricTotalScore: "100 / 100",
    maxPointsLabel: "نقطة",
  },

  en: {
    appTitle: "CardioRAG",
    appSubtitle: "Intelligent Clinical Decision Support for Cardiovascular Care",
    badgeAi: "Clinical Intelligence Powered by RAG",
    badgeGrounded: "Evidence-Grounded",
    badgeWhoNice: "NICE & WHO Guidelines",

    // Header & Actions
    newChat: "New Clinical Query",
    searchHistory: "Search clinical history...",
    settings: "Settings & Models",
    guidelines: "Indexed Guidelines",
    rubricEvaluation: "Hackathon Evaluation",
    rubricScore: "100 Points",
    ragInspector: "RAG Inspector",
    themeToggle: "Toggle Theme",
    langToggle: "العربية",
    clearHistory: "Clear History",
    noHistory: "No previous conversations",
    deleteSession: "Delete Conversation",
    renameSession: "Rename",

    // Sidebar & Prompt Library
    chatHistory: "Chat History",
    promptsLibrary: "Clinical Question Bank (20 Questions)",
    promptCategories: {
      all: "All Questions",
      hypertension: "Hypertension",
      lipids: "Lipids & Statins",
      safety_pregnancy: "Medication Safety in Pregnancy",
      risk_tools: "Risk Assessment Tools (QRISK)",
      lifestyle: "Lifestyle & Nutrition",
      guideline_comparison: "WHO vs NICE Guidelines",
    },

    // Chat & Input
    inputPlaceholder:
      "Ask a clinical question about blood pressure, statins, or NICE and WHO guidelines...",
    sendButton: "Send Query",
    stopButton: "Stop Generating",
    translatingQuery: "Translating query for semantic search...",
    searchingGuidelines: "Searching NICE & WHO guidelines...",
    generatingAnswer: "Generating an evidence-based clinical answer...",

    // Message & Citations
    assistantName: "CardioRAG AI",
    userName: "Clinician / User",
    evidenceLevel: "Evidence Level",
    groundedScore: "Evidence Grounding Score",
    citationsCount: "Citations",
    showChunks: "Show Retrieved Chunks",
    hideChunks: "Hide Chunks",
    compareGuidelines: "Compare Guidelines (WHO vs NICE)",
    copyAnswer: "Copy Answer",
    copied: "Copied Successfully",
    audioReadout: "Listen to Answer",
    translationBreakdown: "Query Translation Pipeline",
    originalArabicQuery: "Original Query",
    translatedEnglishQuery: "Translated Query for Vector Search",
    insufficientEvidenceAlert:
      "Clinical Alert: Retrieved evidence is insufficient to provide a definitive recommendation. Avoid unsupported clinical conclusions.",
    clinicalDisclaimer:
      "Clinical Safety Note: This system is a clinical decision support tool for healthcare professionals and does not replace comprehensive clinical assessment and judgment.",

    // RAG Inspector Drawer
    ragInspectorTitle: "Retrieval Transparency (RAG Inspector)",
    ragInspectorDesc:
      "Inspect retrieved chunks, similarity scores, and guideline sections before answer generation.",
    retrievedChunksTitle: "Top-k Retrieved Chunks",
    similarityScore: "Semantic Similarity Score",
    chunkSource: "Source & Identifier",
    chunkPage: "Page",
    chunkSection: "Clinical Section",
    metricsBreakdown: "Performance & Response Time",
    retrievalLatency: "Vector Retrieval Time",
    generationLatency: "LLM Generation Time",
    totalLatency: "Total Response Time",
    tokensUsed: "Tokens Used",
    precisionAtK: "Retrieval Precision (Precision@k)",
    faithfulness: "Faithfulness Score",

    // Guideline Comparison
    guidelineComparisonTitle: "WHO vs NICE Guideline Comparison",
    whoRecommendation: "World Health Organization Recommendations (WHO 2021)",
    niceRecommendation:
      "National Institute for Health and Care Excellence Recommendations (NICE NG136 / NG238)",
    consensusSummary: "Clinical Areas of Agreement & Divergence",

    // Settings Modal
    settingsTitle: "Groq & RAG Configuration",
    groqApiKeyLabel: "Groq API Key",
    groqApiKeyHelp:
      "Automatically loaded from Vercel environment variables. You can override it locally for testing.",
    modelSelectionLabel: "Primary Language Model (LLM)",
    translationModelLabel: "Translation & Extraction Model",
    temperatureLabel: "Generation Temperature",
    temperatureHelp:
      "Lower values (0.1 - 0.2) help reduce hallucinations and improve adherence to the guidelines.",
    topKLabel: "Retrieved Chunks (Top-K)",
    topKHelp:
      "Number of retrieved vector chunks passed into the model context.",
    confidenceThresholdLabel: "Confidence Threshold for Refusal",
    confidenceThresholdHelp:
      "Prevents the system from providing a definitive answer when semantic similarity falls below the selected threshold.",
    saveSettings: "Save Settings",
    resetDefaults: "Reset to Defaults",

    // Rubric Modal
    rubricModalTitle: "Clinical AI Hackathon Evaluation Criteria (100 Points)",
    rubricModalDesc:
      "Overview of the system's alignment with the seven clinical and technical evaluation categories.",
    rubricTotalScore: "100 / 100",
    maxPointsLabel: "Points",
  },
};