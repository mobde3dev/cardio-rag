# 🩺 دليل المطور للتكامل والتعديل — CardioRAG Developer Guide

هذا الدليل مخصص لتوضيح هيكلية المشروع المعمارية، مع **روابط مباشرة قابلة للنقر (Clickable Links)** لكل ملف، وشرح تفصيلي لما يمكنك تعديله أو ربطه بالـ Backend ونماذج الـ Embedding والـ Vector Database.

---

## 🗂️ خريطة ملفات المشروع وأماكن التعديل السريع

### 1. الـ System Prompts ومسارات الذكاء الاصطناعي (Prompts & AI Endpoints)

| الملف | الرابط القابل للنقر | ما الذي تعدله هنا؟ |
|---|---|---|
| **Clinical System Prompt** | [groqService.ts](file:///d:/AI/cardio-rag-web/src/services/groqService.ts) | تعديل نص السيستيم برومبت الرئيسي للنموذج السريري، وتحديد شروط التأصيل الإرشادي (Grounding Rules) وتنسيق الاستشهادات (Citations). |
| **Serverless Chat Route** | [route.ts (chat)](file:///d:/AI/cardio-rag-web/src/app/api/chat/route.ts) | الـ Endpoint المسؤول عن تمرير الطلبات إلى Groq API عبر السيرفر بأمان دون كشف المفتاح في الـ Client. |
| **Translation Pipeline Route** | [route.ts (translate)](file:///d:/AI/cardio-rag-web/src/app/api/translate/route.ts) | البرومبت الخاص بترجمة استفسار المستخدم العربي إلى مصطلحات طبية إنجليزية متوافقة مع فضاء الـ Embeddings. |
| **Translation Client Service** | [translationService.ts](file:///d:/AI/cardio-rag-web/src/services/translationService.ts) | منطق اكتشاف اللغة العربية وتشغيل خط المعالجة المزدوج (Cross-lingual Pipeline). |

---

### 2. محرك الـ RAG والمقاطع المسترجعة والربط مع الفيكتور داتابيز (Vector DB & Chunks)

| الملف | الرابط القابل للنقر | ما الذي تعدله هنا؟ |
|---|---|---|
| **RAG Evidence Engine** | [ragMockService.ts](file:///d:/AI/cardio-rag-web/src/services/ragMockService.ts) | **هنا المكان الأساسي لربط الـ Vector DB الحقيقي الخاص بك!** يمكنك استبدال دالة `retrieveClinicalEvidence` لتقوم بعمل `fetch` إلى الـ Backend / Pinecone / Qdrant / Supabase pgvector وإرجاع المقاطع الحقيقية مع درجات الـ Cosine Similarity. |
| **Indexed Guidelines Config** | [guidelines.ts](file:///d:/AI/cardio-rag-web/src/config/guidelines.ts) | إضافة أو تعديل بيانات الأدلة المفهرسة (مثل NICE NG136, WHO 2021, NICE NG238, ESC, AHA)، وأرقام المقاطع وتواريخ التحديث. |

---

### 3. بنك الأسئلة السريرية الـ 20 (Sample Questions Bank)

| الملف | الرابط القابل للنقر | ما الذي تعدله هنا؟ |
|---|---|---|
| **Clinical 20 Questions** | [sampleQuestions.ts](file:///d:/AI/cardio-rag-web/src/config/sampleQuestions.ts) | قائمة الـ 20 سؤالاً سريرياً مع الترجمة والتصنيفات (ضغط الدم، الستاتين، الحمل، أدوات المخاطر QRISK، ومقارنة الأدلة). يمكنك إضافة أي أسئلة سريرية إضافية هنا. |

---

### 4. نماذج Groq وإعدادات الـ LLM (Model Configurations)

| الملف | الرابط القابل للنقر | ما الذي تعدله هنا؟ |
|---|---|---|
| **Available Models** | [models.ts](file:///d:/AI/cardio-rag-web/src/config/models.ts) | قائمة النماذج المتاحة في القائمة المنسدلة (`openai/gpt-oss-120b`, `openai/gpt-oss-20b`, `qwen/qwen3.6-27b`, `allam-2-7b`, `llama-3.3-70b-versatile`). |
| **App Settings Types** | [settings.ts](file:///d:/AI/cardio-rag-web/src/types/settings.ts) | تعريف أنواع الـ State للإعدادات (Temperature, Top-K, Confidence Threshold). |

---

### 5. قاعدة بيانات Supabase و RLS (Database & Isolated Chat History)

| الملف | الرابط القابل للنقر | ما الذي تعدله هنا؟ |
|---|---|---|
| **Supabase SQL Migration** | [supabase_schema.sql](file:///d:/AI/cardio-rag-web/supabase_schema.sql) | كود SQL كامل جاهز للتشغيل في Supabase SQL Editor: ينشئ جداول `profiles`, `chat_sessions`, `chat_messages` مع سياسات **Row Level Security (RLS)** الصارمة لكل مستخدم. |
| **Supabase Client Service** | [supabaseService.ts](file:///d:/AI/cardio-rag-web/src/services/supabaseService.ts) | إدارة تسجيل الدخول السريع للطبيب، وعزل سجل المحادثات لكل مستخدم (يدعم وضع Guest للـ MVP). |
| **Auth Modal Component** | [AuthModal.tsx](file:///d:/AI/cardio-rag-web/src/components/auth/AuthModal.tsx) | نافذة تسجيل الدخول السريع في الواجهة الأمامية. |

---

### 6. معايير تقييم الهاكاثون (Hackathon 100-Points Evaluation Rubric)

| الملف | الرابط القابل للنقر | ما الذي تعدله هنا؟ |
|---|---|---|
| **Rubric Criteria Data** | [rubricCriteria.ts](file:///d:/AI/cardio-rag-web/src/config/rubricCriteria.ts) | تفاصيل المعايير السبعة لتقييم الهاكاثون (Retrieval Quality 22, Faithfulness 18, Architecture 15, Metrics 10, Safety 8, Presentation 17, Innovation 10). |
| **Rubric Modal View** | [RubricModal.tsx](file:///d:/AI/cardio-rag-web/src/components/rag/RubricModal.tsx) | نافذة عرض تقييم الـ 100 نقطة التفاعلية في الواجهة. |

---

### 7. لوحة فحص الـ RAG والشفافية (RAG Inspector & Metrics Drawer)

| الملف | الرابط القابل للنقر | ما الذي تعدله هنا؟ |
|---|---|---|
| **RAG Inspector Drawer** | [RagInspectorDrawer.tsx](file:///d:/AI/cardio-rag-web/src/components/rag/RagInspectorDrawer.tsx) | السايدبار الجانبي الذي يظهر عند الضغط على "عرض المقاطع المسترجعة"، ويعرض درجات التطابق وأزمنة المعالجة (Latency). |
| **Chunk Card View** | [ChunkCard.tsx](file:///d:/AI/cardio-rag-web/src/components/rag/ChunkCard.tsx) | بطاقة المقطع المسترجع المنفردة، مع شريط نسبة الـ Cosine Similarity ورقم الصفحة. |
| **WHO vs NICE Comparison** | [GuidelineComparison.tsx](file:///d:/AI/cardio-rag-web/src/components/rag/GuidelineComparison.tsx) | بطاقة المقارنة التفريقية السريرية بين إرشادات منظمة الصحة العالمية والدليل البريطاني. |

---

### 8. الترجمة والنصوص والتعريب (i18n & Localization)

| الملف | الرابط القابل للنقر | ما الذي تعدله هنا؟ |
|---|---|---|
| **Bilingual Dictionary** | [translations.ts](file:///d:/AI/cardio-rag-web/src/i18n/translations.ts) | كافة النصوص والمصطلحات الطبية باللغتين العربية والإنجليزية. |
| **Language Hook** | [useLanguage.ts](file:///d:/AI/cardio-rag-web/src/hooks/useLanguage.ts) | إدارة اتجاه الصفحة (RTL للعربية / LTR للإنجليزية) وحفظ التفضيلات. |

---

### 9. التصميم والألوان والسمات (Theme & CSS Design System)

| الملف | الرابط القابل للنقر | ما الذي تعدله هنا؟ |
|---|---|---|
| **Tailwind Config** | [tailwind.config.ts](file:///d:/AI/cardio-rag-web/tailwind.config.ts) | لوحة الألوان السريرية (`medical` Teal و `cardio` Crimson) والخطوط والتحريكات. |
| **Global Styles** | [globals.css](file:///d:/AI/cardio-rag-web/src/app/globals.css) | استيراد خطوط Google (`IBM Plex Sans Arabic`, `Plus Jakarta Sans`) وتنسيقات شريط التمرير. |

---

## 🚀 كيفية النشر على Vercel وضبط الـ Environment Variables

### تشغيل محرك الاسترجاع المحلي

شغّل واجهة FastAPI من مجلد `cardio-rag-backend`:

```bash
uvicorn src.api:app --reload --port 8000
```

ثم اضبط `RAG_BACKEND_URL=http://127.0.0.1:8000` في بيئة تشغيل الويب. واجهة Next.js تمرر طلبات `/api/retrieve` إلى مسار FastAPI `/retrieve`، بينما تبقى مفاتيح Groq على الخادم.

1. ارفع المشروع إلى GitHub (باتباع الكوميتات النظيفة).
2. ادخل إلى لوحة تحكم [Vercel](https://vercel.com) واضغط **Import Project**.
3. في شاشة **Environment Variables** أضف المفاتيح التالية:
   - `GROQ_API_KEY`: مفتاح Groq الخاص بك (مثال: `gsk_...`).
   - `DEFAULT_GROQ_MODEL`: النموذج الافتراضي (افتراضياً: `openai/gpt-oss-120b`).
   - `DEFAULT_TRANSLATION_MODEL`: نموذج الترجمة (افتراضياً: `openai/gpt-oss-20b`).
   - `RAG_BACKEND_URL`: عنوان خدمة FastAPI للاسترجاع (مثال محلي: `http://127.0.0.1:8000`).

### نشر مجاني مقترح

1. ارفع مجلد `cardio-rag-backend` إلى مستودع GitHub، ثم أنشئ خدمة **Render Web Service** باستخدام `render.yaml`.
2. أضف متغيرات `SUPABASE_URL`, `SUPABASE_KEY`, `CLOUDFLARE_ACCOUNT_ID`, و`CLOUDFLARE_API_TOKEN` في Render.
3. ارفع مجلد `cardio-rag-web` إلى Vercel كـ Next.js project.
4. في Vercel أضف `RAG_BACKEND_URL` بقيمة رابط Render، مثل `https://cardio-rag-api.onrender.com`، بالإضافة إلى `GROQ_API_KEY`.
5. بعد معرفة رابط Vercel، اضبط `FRONTEND_URL` في Render عليه. خدمة Render المجانية قد تدخل وضع السكون، لذلك قد يتأخر أول طلب بعد فترة من عدم الاستخدام.
   - `NEXT_PUBLIC_SUPABASE_URL`: (اختياري) رابط مشروع Supabase الخاص بك.
   - `NEXT_PUBLIC_SUPABASE_ANON_KEY`: (اختياري) المفتاح العام لـ Supabase.
4. اضغط **Deploy** وسيعمل الموقع فوراً بكامل إمكانياته السريرية!
