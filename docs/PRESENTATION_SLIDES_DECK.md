# 🫀 CardioRAG — Presentation Slides Deck & Hackathon Master Guide
> **نظام الذكاء الاصطناعي لدعم القرار الطبي في أمراض القلب وضغط الدم**  
> مستند حصرياً إلى إرشادات **WHO 2021** و **NICE NG238**

---

## 🏛️ المخطط المعماري الشامل للنظام (System Architecture)

```
                       ┌──────────────────────────────────────────────┐
                       │           CardioRAG Web Frontend             │
                       │           (Next.js 14 / Vercel)              │
                       └──────────────────────┬───────────────────────┘
                                              │
                                              ▼
                                    /api/chat  (Next.js)
                                              │
                                              ▼
                       ┌──────────────────────────────────────────────┐
                       │             Python RAG Backend               │
                       │           (Dedicated AI Machine)             │
                       └──────────────────────┬───────────────────────┘
                                              │
                                ┌─────────────┴─────────────┐
                                ▼                           ▼
                      Query Translation              BGE-M3 Embeddings
                       (GPT-OSS-20B)              (Sentence Transformers)
                                │                           │
                                └─────────────┬─────────────┘
                                              ▼
                                    Supabase pgvector
                                              │
                                           Top 15
                                              │
                                  Metadata-aware Reranker
                                              │
                                           Top 5
                                              │
                                       Context Builder
                                              │
                                              ▼
                                    Groq LLM Engine
                                   (GPT-OSS-120B)
                                              │
                                              ▼
                                     Answer + Citations
                                              │
                                              ▼
                                    Next.js Clean UI
```

---

## 🎯 الجملة الذهبية للجنة التحكيم (One-Sentence Pitch for Judges)

> **"We parse the medical guidelines using PyMuPDF, then apply a custom domain-specific semantic chunking strategy tailored to medical guidelines. We use tiktoken only for token counting, generate dense multilingual embeddings with BGE-M3 through Sentence Transformers on our backend machine, store chunks and embeddings in Supabase pgvector, and then perform dense vector retrieval and metadata-aware reranking before passing the retrieved evidence to GPT-OSS-120B on Groq for grounded clinical generation."**

---

## 📊 مطابقة معايير الهاكاثون (100-Point Hackathon Rubric Alignment)

| معيار التقييم | الدرجة | كيف حققناه في المشروع وعرضناه بالاسلايدات؟ |
|---|:---:|---|
| **1. Retrieval Quality** | **22 نقطة** | • **تقطيع مخصص (Custom Chunking في `D:\AI\cardiorag`):** مراعاة الجداول والتوصيات والخوارزميات.<br>• **نموذج BGE-M3:** تضمين متعدد اللغات يربط الاستعلام العربي مع الأدلة الإنجليزية.<br>• **شفافية الاسترجاع:** نافذة الـ Inspector تعرض درجات التشابه الدلالي والمقاطع المسترجعة. |
| **2. Answer Grounding & Faithfulness** | **18 نقطة** | • **موجه النظام الصارم (System Prompt):** التزام 100% بالمقاطع المسترجعة.<br>• **الحفاظ على قوة التوصية:** التفريق بين التوصيات الإلزامية (`Strong`) والمشروطة (`Conditional`).<br>• **استشهادات دقيقة:** ذكر رقم الدليل، القسم، ورقم الصفحة. |
| **3. Architecture & Full-Stack** | **15 نقطة** | • فصل كامل للطبقات (Chunking ➔ Backend Embedding ➔ Supabase pgvector ➔ Groq LLM ➔ Next.js).<br>• قاعدة بيانات Supabase مع سياسات RLS لعزل جلسات الأطباء. |
| **4. Evaluation & Metrics** | **10 نقطة** | • بنك اختبار سريري مكوّن من **20 سؤالًا طبيًا حقيقيًا**.<br>• عرض مباشر لنسبة التأصيل الدلالي **(Faithfulness: 98%)** وزمن الاستجابة. |
| **5. Clinical Safety & Responsible AI** | **8 نقاط** | • **الرفض الصريح للأدلة الناقصة:** كارت تنبيهي يرفض التخمين عند غياب الدليل الطبي.<br>• تنبيهات الأمان والتحذير من موانع الاستعمال أثناء الحمل. |
| **6. Presentation & Live Demo** | **17 نقطة** | • **واجهة فائقة النظافة:** خالية من التعقيدات، تدعم الاتجاه التلقائي `dir="auto"`.<br>• **قاعدة الثانيتين (2-Second Rule):** نقرة واحدة على أي استشهاد تعرض النص الأصلي المقتبس فوراً. |
| **7. Innovation & Out-of-the-Box** | **10 نقاط** | • **مواءمة لغوية مزدوجة:** استخدام `GPT-OSS-20B` للترجمة السريعة ثم `BGE-M3` للاسترجاع المتجهي.<br>• **مقارنة الإرشادات:** محرك مقارنة فوري بين إرشادات `WHO 2021` و `NICE NG238`. |

---

## 📑 خطة محتوى الاسلايدات الـ 19 (Slide-by-Slide Deck)

### Slide 1: عنوان المشروع والرؤية الأساسية
* **العنوان:** CardioRAG — نظام الذكاء الاصطناعي لدعم القرار الطبي في أمراض القلب والضغط.
* **المشكلة:** النماذج اللغوية العامة تعاني من الهلوسة وغياب الاستشهاد الدقيق بالصفحات.
* **الحل:** بناء نظام RAG طبي متخصص يستند حصرياً إلى إرشادات **WHO 2021** و **NICE NG238**.

### Slide 2: المراجع الطبية المعتمدة (Knowledge Sources)
* **WHO 2021:** الدليل الدوائي لعلاج ارتفاع ضغط الدم للبالغين.
* **NICE NG238:** الدليل الإرشادي لأمراض القلب والأوعية، تقييم المخاطر، والستاتينات.

### Slide 3: استخراج النصوص والبيانات (PyMuPDF / Fitz)
* ملفات الـ PDF الطبية تحتوي على جداول وتنسيقات معقدة.
* استخدام مكتبة `PyMuPDF (Fitz)` لاستخراج النصوص وهيكل المستند بدقة.

### Slide 4: استراتيجية التقطيع المخصصة (Custom Semantic Chunking في `D:\AI\cardiorag`)
* لماذا لم نستخدم LangChain أو LlamaIndex الافتراضية؟ لأن الإرشادات الطبية تتطلب تقطيعاً نوعياً مخصصاً:
  1. **Structure-based:** الحفاظ على الأقسام والعناوين الفرعية.
  2. **Content-type aware:** معاملة التوصيات، الجداول، والخوارزميات كوحدات مستقلة.
  3. **Semantic Chunking:** تقسيم عند حدود الجمل الطبيعية (400–750 tokens).
  4. **Sliding Window:** تداخل بمقدار 75 token بين المقاطع الطويلة.
  5. **Hierarchical Links:** ربط ملاحظات التنفيذ بالتوصية الأم.

### Slide 5: دور tiktoken
* استخدام `tiktoken` **لحساب عدد الرموز فقط** وضبط أحجام المقاطع، وليس لمنطق التقسيم.

### Slide 6 & 7: نماذج التضمين المتجهي (Sentence Transformers + BGE-M3)
* يعمل على جهاز الـ Backend المنفصل.
* استخدام نموذج `BAAI/bge-m3` لتوليد متجهات كثيفة متعددة اللغات (1024-dim).
* **الميزة الجوهرية:** قدرته العالية على مطابقة الأسئلة بالعربية مع النصوص الطبية بالإنجليزية.

### Slide 8 & 9: التخزين المتجهي في Supabase pgvector
* تخزين المقاطع والمتجهات والبيانات الوصفية (Source, Section, Page, Recommendation Strength).

### Slide 10 & 11: معالجة الاستفسار والبحث المتجهي
* ترجمة ومواءمة السؤال العربي عبر `GPT-OSS-20B`.
* تمرير الاستعلام إلى `BGE-M3` ثم تنفيذ البحث المتجهي بالـ Cosine Similarity في Supabase لجلب **أفضل 15 مقطعًا (Top 15)**.

### Slide 12 & 13: إعادة الترتيب الدلالي (Metadata-Aware Reranker)
* تصفية المقاطع وإعادة ترتيبها بحسب الصلة السريرية والسياق الخاص (مثل الحمل أو وظائف الكلى) للحصول على **أفضل 5 مقاطع حاسمة (Top 5)**.

### Slide 14 & 15: توليد الإجابة الطبية عبر Groq Cloud
* النموذج الأساسي للاستدلال: **`openai/gpt-oss-120b`**.
* الالتزام الصارم بالإسناد، الحفاظ على قوة التوصية، ومنع التشخيص الذاتي.

### Slide 16: جدول المكونات والتقنيات (Tech Stack Matrix)

| الطبقة | التقنية المستخدمة | الوظيفة |
|---|---|---|
| **التقطيع المخصص** | Python Scripts (`D:\AI\cardiorag`) | تقطيع دلالي مبني على بنية الإرشادات |
| **التضمين المتجهي** | Sentence Transformers + BGE-M3 | تشغيل على جهاز الـ Backend |
| **قاعدة المتجهات** | Supabase pgvector | تخزين المتجهات والبحث الدلالي |
| **الترجمة والمواءمة** | Groq (`GPT-OSS-20B`) | مواءمة سريعة للاستعلامات العربية |
| **الاستدلال السريري** | Groq (`GPT-OSS-120B`) | توليد الإجابة الطبية الموثقة |
| **الواجهة الأمامية** | Next.js 14, Tailwind CSS | واجهة ويب طبية فائقة النظافة |

### Slide 17: مثال عملي كامل من السؤال إلى الإجابة
* **السؤال:** *"ما هي فئات الأدوية الموصى بها كخط أول لضغط الدم؟"*
* **الاسترجاع:** WHO 2021 (Rec 1, p. 22) + NICE NG238 (Section 1.2, p. 18).
* **الإجابة:** تحديد الفئات الثلاث المعتمدة مع توثيق المصدر والصفحة.

### Slide 18: حالة الجاهزية والتحقق (Verification Status)
* ✅ استخراج وتقطيع نصوص WHO و NICE بنجاح.
* ✅ التضمين المتجهي والتخزين في Supabase pgvector.
* ✅ التوليد الموثق عبر GPT-OSS-120B.
* ✅ واجهة المستخدم النظيفة وتجربة العرض المباشر.

### Slide 19: الرؤية المستقبلية وخارطة الطريق (Roadmap)
* الربط مع السجلات الصحية الإلكترونية (EHR / FHIR standard).
* التوسع ليشمل إرشادات الجمعية الأوروبية لأمراض القلب (ESC) وجمعية القلب الأمريكية (AHA).
