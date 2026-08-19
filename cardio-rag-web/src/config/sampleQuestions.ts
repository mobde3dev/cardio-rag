export interface SampleQuestion {
  id: string;

  category:
    | "hypertension"
    | "lipids"
    | "safety_pregnancy"
    | "risk_tools"
    | "lifestyle"
    | "guideline_comparison"
    | "heart_failure";

  categoryLabelAr: string;
  categoryLabelEn: string;

  questionAr: string;
  questionEn: string;

  primaryGuideline:
    | "NICE NG136"
    | "WHO 2021"
    | "NICE NG238"
    | "Both";
}

export const SAMPLE_QUESTIONS: SampleQuestion[] = [
  {
    id: "q1",
    category: "hypertension",
    categoryLabelAr: "علاج ضغط الدم الأولي",
    categoryLabelEn: "Initial Hypertension Therapy",
    questionAr:
      "ما هي الفئات الدوائية الثلاث الموصى بها كعلاج أولي للبالغين المصابين بارتفاع ضغط الدم؟",
    questionEn:
      "What are the three drug classes recommended as first-line therapy for adults with hypertension?",
    primaryGuideline: "Both",
  },

  {
    id: "q2",
    category: "lipids",
    categoryLabelAr: "أهداف الكوليسترول",
    categoryLabelEn: "Cholesterol Targets",
    questionAr:
      "ما هو هدف مستوى الكوليسترول الموصى به للوقاية الثانوية من الأمراض القلبية الوعائية وفقاً لإرشادات نايس (NICE)؟",
    questionEn:
      "What is the recommended cholesterol target for secondary prevention of cardiovascular disease according to NICE guidelines?",
    primaryGuideline: "NICE NG238",
  },

  {
    id: "q3",
    category: "lipids",
    categoryLabelAr: "الدهون الثلاثية الحرجة",
    categoryLabelEn: "Critical Triglycerides",
    questionAr:
      "متى يجب ترتيب تقييم تخصصي عاجل بناءً على مستوى الدهون الثلاثية (Triglycerides) وفقاً لإرشادات نايس؟",
    questionEn:
      "When should urgent specialist assessment be arranged based on triglyceride levels according to NICE guidelines?",
    primaryGuideline: "NICE NG238",
  },

  {
    id: "q4",
    category: "hypertension",
    categoryLabelAr: "تمكين غير الأطباء (WHO)",
    categoryLabelEn: "Task-Shifting (WHO)",
    questionAr:
      "ما هي الشروط الأربعة التي وضعتها منظمة الصحة العالمية لتمكين غير الأطباء (كالصيادلة والممرضين) من تقديم العلاج الدوائي لارتفاع ضغط الدم؟",
    questionEn:
      "What are the four conditions set by the WHO to enable non-physicians (such as pharmacists and nurses) to deliver pharmacological treatment for hypertension?",
    primaryGuideline: "WHO 2021",
  },

  {
    id: "q5",
    category: "lipids",
    categoryLabelAr: "تصنيف شدة الستاتين",
    categoryLabelEn: "Statin Intensity",
    questionAr:
      "كيف يتم تصنيف أدوية الستاتين (Statins) من حيث الشدة إلى فئات مرتفعة ومتوسطة ومنخفضة بناءً على الجرعة ونوع الدواء وفقاً لنايس؟",
    questionEn:
      "How are statins classified by intensity into high, medium, and low categories based on dose and drug type according to NICE?",
    primaryGuideline: "NICE NG238",
  },

  {
    id: "q6",
    category: "risk_tools",
    categoryLabelAr: "موانع أدوات المخاطر",
    categoryLabelEn: "Risk Assessment Exclusions",
    questionAr:
      "ما هي الفئات السريرية التي لا ينبغي استخدام أدوات تقييم المخاطر (مثل QRISK) معها لأنها تُعتبر بالفعل عالية الخطورة للإصابة بالأمراض القلبية الوعائية؟",
    questionEn:
      "Which clinical categories should not have cardiovascular risk assessment tools (such as QRISK) applied because they are already considered at high risk of CVD?",
    primaryGuideline: "NICE NG238",
  },

  {
    id: "q7",
    category: "hypertension",
    categoryLabelAr: "جدول متابعة الضغط",
    categoryLabelEn: "BP Follow-up Timeline",
    questionAr:
      "ما هو الجدول الزمني الموصى به لإعادة قياس ضغط الدم ومتابعة المريض بعد بدء العلاج أو تغييره، وعند استقرار الضغط؟",
    questionEn:
      "What is the recommended timeline for re-measuring blood pressure and patient follow-up after starting or modifying therapy, and once BP is controlled?",
    primaryGuideline: "Both",
  },

  {
    id: "q8",
    category: "lipids",
    categoryLabelAr: "فحوصات ما قبل الستاتين",
    categoryLabelEn: "Pre-Statin Baseline Tests",
    questionAr:
      "ما هي الفحوصات المخبرية والسريرية الأساسية التي يجب إجراؤها قبل البدء في استخدام الستاتين (Statins)؟",
    questionEn:
      "What are the essential baseline laboratory and clinical tests required prior to starting statin therapy?",
    primaryGuideline: "NICE NG238",
  },

  {
    id: "q9",
    category: "lipids",
    categoryLabelAr: "إنزيم الكرياتين كينيز (CK)",
    categoryLabelEn: "Creatine Kinase (CK) Protocol",
    questionAr:
      "كيف توجه إرشادات نايس التعامل مع مستويات إنزيم الكرياتين كينيز (Creatine Kinase) قبل وأثناء العلاج بالستاتين؟",
    questionEn:
      "How do NICE guidelines advise managing creatine kinase (CK) levels before and during statin therapy?",
    primaryGuideline: "NICE NG238",
  },

  {
    id: "q10",
    category: "hypertension",
    categoryLabelAr: "بروتوكول حبة واحدة (WHO)",
    categoryLabelEn: "Single-Pill Algorithm (WHO)",
    questionAr:
      "ما هي الخطوات العلاجية الموصى بها في بروتوكول منظمة الصحة العالمية (Algorithm 1) للبدء بعلاج مركب في حبة واحدة وتصعيده عند عدم الوصول للهدف؟",
    questionEn:
      "What are the treatment steps recommended in the WHO protocol (Algorithm 1) for initiating single-pill combination therapy and stepped escalation when targets are not met?",
    primaryGuideline: "WHO 2021",
  },

  {
    id: "q11",
    category: "safety_pregnancy",
    categoryLabelAr: "سلامة الحمل والأدوية",
    categoryLabelEn: "Pregnancy Safety (ACEi/ARB/Statins)",
    questionAr:
      "ما هي التوصيات الصريحة في الدليلين الطبيين بشأن استخدام الأدوية التالية أثناء الحمل: مثبطات الإنزيم المحول للأنجيوتنسين (ACEi)، حاصرات مستقبلات الأنجيوتنسين (ARBs)، وأدوية الستاتين؟",
    questionEn:
      "What are the explicit recommendations in both guidelines regarding the use of ACE inhibitors (ACEi), ARBs, and statins during pregnancy?",
    primaryGuideline: "Both",
  },

  {
    id: "q12",
    category: "hypertension",
    categoryLabelAr: "ضغط 130-139 ملم زئبق",
    categoryLabelEn: "Systolic 130-139 mmHg Triggers",
    questionAr:
      "متى يُنصح ببدء علاج خفض ضغط الدم عند مستويات الضغط الانقباضي بين 130 و139 ملم زئبق، وما هي الأهداف المحددة لهذه الفئات؟",
    questionEn:
      "When is blood pressure lowering therapy recommended for systolic levels between 130 and 139 mmHg, and what are the specific targets for these patient groups?",
    primaryGuideline: "Both",
  },

  {
    id: "q13",
    category: "guideline_comparison",
    categoryLabelAr: "تأخير العلاج بالفحوصات",
    categoryLabelEn: "Lab Delay & Initiation",
    questionAr:
      "ما هي التوصيات المشتركة في الدليلين حول إجراء الفحوصات المخبرية وتقييم المخاطر القلبية الوعائية ومدى ارتباطها بتأخير بدء العلاج الدوائي؟",
    questionEn:
      "What are the common recommendations across both guidelines regarding laboratory testing and CVD risk assessment without delaying pharmacotherapy initiation?",
    primaryGuideline: "Both",
  },

  {
    id: "q14",
    category: "guideline_comparison",
    categoryLabelAr: "مقارنة العلاج المركب (WHO vs NICE)",
    categoryLabelEn: "Combination Therapy (WHO vs NICE)",
    questionAr:
      "قارن بين نهج كل من الدليلين (WHO و NICE) في تفضيل العلاج المركب (Combination therapy) أو العلاج متعدد الأدوية عند بدء العلاج الخافض للضغط مقارنة بتصعيد علاج الدهون.",
    questionEn:
      "Compare the approaches of WHO and NICE guidelines regarding preference for initial combination therapy in hypertension versus lipid treatment escalation.",
    primaryGuideline: "Both",
  },

  {
    id: "q15",
    category: "lipids",
    categoryLabelAr: "مكملات غير موصى بها (NICE)",
    categoryLabelEn: "Non-Recommended Supplements",
    questionAr:
      "ما هي العلاجات والمكملات الغذائية الخافضة للدهون التي توصي إرشادات نايس صراحة بعدم استخدامها للوقاية من الأمراض القلبية الوعائية؟",
    questionEn:
      "Which lipid-lowering treatments and dietary supplements do NICE guidelines explicitly recommend AGAINST using for CVD prevention?",
    primaryGuideline: "NICE NG238",
  },

  {
    id: "q16",
    category: "lipids",
    categoryLabelAr: "بدائل الستاتين",
    categoryLabelEn: "Non-Statin Alternatives",
    questionAr:
      "ما هي الخيارات العلاجية غير الستاتينية الموصى بها في إرشادات نايس للمرضى الذين لا يتحملون الستاتين أو لديهم موانع لاستخدامه؟",
    questionEn:
      "What are the non-statin therapeutic options recommended by NICE guidelines for patients who are statin-intolerant or have contraindications?",
    primaryGuideline: "NICE NG238",
  },

  {
    id: "q17",
    category: "guideline_comparison",
    categoryLabelAr: "مرضى السكري والاعتلال الكلوي",
    categoryLabelEn: "Diabetes & CKD Management",
    questionAr:
      "كيف يتعامل كل من دليل منظمة الصحة العالمية ودليل نايس مع مرضى السكري (النوع الأول والثاني) والاعتلال الكلوي المزمن من حيث مستويات الخطورة وبدء العلاج؟",
    questionEn:
      "How do WHO and NICE guidelines handle patients with diabetes (Type 1 & 2) and chronic kidney disease (CKD) regarding risk stratification and treatment initiation?",
    primaryGuideline: "Both",
  },

  {
    id: "q18",
    category: "lifestyle",
    categoryLabelAr: "توصيات نمط الحياة والغذاء",
    categoryLabelEn: "Diet & Lifestyle Recommendations",
    questionAr:
      "ما هي التوصيات المحددة المتعلقة بالنظام الغذائي ونمط الحياة للوقاية من الأمراض القلبية الوعائية وارتفاع ضغط الدم في كلا الدليلين؟",
    questionEn:
      "What are the specific dietary and lifestyle recommendations for CVD and hypertension prevention in both guidelines?",
    primaryGuideline: "Both",
  },

  {
    id: "q19",
    category: "lipids",
    categoryLabelAr: "آلام العضلات مع الستاتين",
    categoryLabelEn: "Statin Muscle Symptoms Protocol",
    questionAr:
      "ما هي الإجراءات السريرية التي يجب اتخاذها عندما يبلغ مريض يتناول ستاتين عالي الشدة عن ظهور آلام أو أعراض عضلية غير مبررة؟",
    questionEn:
      "What clinical actions should be taken when a patient on high-intensity statin reports unexplained muscle pain or symptoms?",
    primaryGuideline: "NICE NG238",
  },

  {
    id: "q20",
    category: "risk_tools",
    categoryLabelAr: "عوامل تقليل دقة QRISK",
    categoryLabelEn: "QRISK Underestimation Factors",
    questionAr:
      "ما هي الحالات أو العوامل التي قد تؤدي إلى تقليل أدوات تقييم المخاطر (مثل QRISK) من تقدير الخطر القلبي الوعائي الفعلي للمريض وفقاً لنايس؟",
    questionEn:
      "What conditions or factors may lead risk assessment tools (like QRISK) to underestimate actual cardiovascular risk according to NICE?",
    primaryGuideline: "NICE NG238",
  },

  /*
   * Heart Failure Suggestions
   *
   * These are suggestion prompts for the Chat UI.
   * The actual medical answer should still be generated
   * from the project's RAG sources.
   */

  {
    id: "q21",
    category: "heart_failure",
    categoryLabelAr: "علاج فشل القلب",
    categoryLabelEn: "Heart Failure Treatment",
    questionAr:
      "ما هي الخطوط العلاجية الموصى بها للمرضى المصابين بفشل القلب؟",
    questionEn:
      "What treatment pathways are recommended for patients with heart failure?",
    primaryGuideline: "Both",
  },

  {
    id: "q22",
    category: "heart_failure",
    categoryLabelAr: "تشخيص فشل القلب",
    categoryLabelEn: "Heart Failure Diagnosis",
    questionAr:
      "متى يتم تشخيص فشل القلب وما هي الفحوصات الأساسية المطلوبة لتقييم المريض؟",
    questionEn:
      "How is heart failure diagnosed and what initial investigations are recommended for patient assessment?",
    primaryGuideline: "Both",
  },

  {
    id: "q23",
    category: "heart_failure",
    categoryLabelAr: "أدوية فشل القلب",
    categoryLabelEn: "Heart Failure Medications",
    questionAr:
      "ما هي الأدوية المستخدمة في علاج فشل القلب، وكيف يتم اختيار العلاج الدوائي المناسب حسب حالة المريض؟",
    questionEn:
      "Which medications are used to treat heart failure, and how is pharmacological treatment selected according to the patient's condition?",
    primaryGuideline: "Both",
  },

  {
    id: "q24",
    category: "heart_failure",
    categoryLabelAr: "متابعة فشل القلب",
    categoryLabelEn: "Heart Failure Follow-up",
    questionAr:
      "ما هي أهم مؤشرات المتابعة التي يجب تقييمها لدى المريض المصاب بفشل القلب بعد بدء العلاج؟",
    questionEn:
      "What are the key follow-up parameters that should be assessed in a patient with heart failure after starting treatment?",
    primaryGuideline: "Both",
  },

  {
    id: "q25",
    category: "heart_failure",
    categoryLabelAr: "تفاقم فشل القلب",
    categoryLabelEn: "Worsening Heart Failure",
    questionAr:
      "متى يحتاج مريض فشل القلب إلى تقييم عاجل أو دخول المستشفى بسبب تدهور حالته؟",
    questionEn:
      "When does a patient with heart failure require urgent assessment or hospital admission because of worsening symptoms?",
    primaryGuideline: "Both",
  },
];