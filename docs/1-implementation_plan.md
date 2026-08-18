# CardioRAG — Clinical AI Chatbot Web Interface

CardioRAG is an evidence-based Clinical Cardiology AI Decision Support Web Application. It provides a modular, highly accessible, responsive chat interface tailored for clinical cardiology guidelines (NICE NG136, WHO 2021, NICE CG181/NG238). It features Groq LLM integration, cross-lingual translation pipeline (Arabic ⇄ English), transparent RAG evidence inspection, bilingual RTL/LTR support, light/dark themes, and chat history.

## User Review Required

> [!IMPORTANT]
> **Key Architecture Decisions:**
> 1. **Framework**: Next.js 14 (App Router) + Tailwind CSS + Lucide Icons for optimal Vercel deployment with serverless API routes (`/api/chat`, `/api/translate`).
> 2. **Clean Component Architecture**: Strict separation of concerns with small, maintainable components (20–80 lines per file).
> 3. **RAG Transparency & Hackathon Rubric**: Full inspection drawer showing retrieved chunks, cosine similarity scores, guideline citation pages, and evaluation metrics (Precision@k, Faithfulness, Latency).
> 4. **Pre-Loaded Clinical Bank**: All 20 clinical questions provided in the user prompt are included as interactive starter chips categorized by topic (Hypertension, Statins, Pregnancy, Risk Tools, Lifestyle, Guidelines Comparison).

---

## Proposed Changes

```
cardio-rag-web/
├── package.json
├── tsconfig.json
├── tailwind.config.ts
├── postcss.config.js
├── next.config.mjs
├── .env.example
├── src/
│   ├── app/
│   │   ├── api/
│   │   │   ├── chat/route.ts              # Groq API route with clinical system prompt
│   │   │   └── translate/route.ts         # Translation route (AR -> EN for embeddings)
│   │   ├── layout.tsx                     # Root layout with fonts & theme provider
│   │   ├── page.tsx                       # Main dashboard & chat orchestrator
│   │   └── globals.css                    # Design system tokens (Medical Teal/Slate)
│   ├── types/
│   │   ├── chat.ts                        # Message, ChatSession, Attachment types
│   │   ├── rag.ts                         # Chunk, Citation, EvaluationMetrics types
│   │   └── settings.ts                    # Settings, ModelConfig types
│   ├── config/
│   │   ├── guidelines.ts                  # NICE & WHO metadata & section mappings
│   │   ├── sampleQuestions.ts             # 20 Clinical cardiology questions in AR/EN
│   │   ├── models.ts                      # Groq supported models & specs
│   │   └── rubricCriteria.ts              # Hackathon 100-point rubric breakdown
│   ├── i18n/
│   │   ├── translations.ts                # Bilingual dictionary (AR / EN)
│   │   └── index.ts                       # Localization helper
│   ├── services/
│   │   ├── groqService.ts                 # Groq API client with error handling
│   │   ├── translationService.ts          # Arabic -> English query translator
│   │   ├── ragMockService.ts              # RAG chunk simulation with similarity scores
│   │   └── storageService.ts              # LocalStorage persistence for sessions & settings
│   ├── hooks/
│   │   ├── useChat.ts                     # Core chat orchestrator hook
│   │   ├── useTheme.ts                    # Theme hook (Light / Dark)
│   │   ├── useLanguage.ts                 # Language hook (AR RTL / EN LTR)
│   │   └── useSessions.ts                 # Session manager hook
│   ├── components/
│   │   ├── ui/
│   │   │   ├── Button.tsx                 # Accessible button with states
│   │   │   ├── Badge.tsx                  # Guideline & status badge
│   │   │   ├── Card.tsx                   # Surface card container
│   │   │   ├── Modal.tsx                  # Reusable accessible modal
│   │   │   ├── Drawer.tsx                 # Sliding side drawer for RAG inspection
│   │   │   └── Tooltip.tsx                # Contextual tooltip
│   │   ├── header/
│   │   │   ├── Header.tsx                 # Top navigation bar
│   │   │   ├── ModelSelector.tsx          # Dropdown to choose Groq model
│   │   │   ├── LanguageToggle.tsx         # AR / EN switcher
│   │   │   ├── ThemeToggle.tsx            # Light / Dark switcher
│   │   │   └── SettingsModal.tsx          # API Key, Top-K & Temperature settings
│   │   ├── sidebar/
│   │   │   ├── ChatSidebar.tsx            # Responsive sidebar wrapper
│   │   │   ├── SessionList.tsx            # History list with search & delete
│   │   │   ├── SessionItem.tsx            # Single session item with active state
│   │   │   ├── PromptLibrary.tsx          # 20 Pre-loaded clinical questions
│   │   │   └── GuidelineStatus.tsx        # NICE / WHO indexed source indicator
│   │   ├── chat/
│   │   │   ├── ChatContainer.tsx          # Message scroll area with auto-scroll
│   │   │   ├── MessageBubble.tsx          # Individual message container
│   │   │   ├── MessageHeader.tsx          # Avatar, sender, copy, audio action
│   │   │   ├── MessageContent.tsx         # Markdown text & table renderer
│   │   │   ├── MessageCitations.tsx       # Guideline citation pill badges
│   │   │   ├── MessageMetrics.tsx         # Faithfulness, Precision@k, Latency
│   │   │   ├── MessageTranslation.tsx     # Cross-lingual translation pill
│   │   │   ├── ChatInput.tsx              # Auto-growing input box with submit
│   │   │   ├── ClinicalAlert.tsx          # Safety warning & confidence meter
│   │   │   └── WelcomeHero.tsx            # Initial landing state with Quick Prompts
│   │   └── rag/
│   │       ├── RagInspectorDrawer.tsx     # Transparency drawer for retrieved chunks
│   │       ├── ChunkCard.tsx              # Chunk card with similarity score & text
│   │       ├── ScoreMeter.tsx             # Colored similarity progress bar
│   │       ├── GuidelineComparison.tsx    # Side-by-side WHO vs NICE comparison
│   │       └── RubricModal.tsx            # Hackathon rubric evaluation viewer
```

---

## Verification Plan

### Automated & Build Verification
1. `npm install` all dependencies cleanly.
2. `npm run build` to verify Next.js TypeScript and bundling without errors.
3. Test API route `/api/chat` and `/api/translate` locally.

### Manual Verification
1. **Interactive Chat**: Ask both Arabic and English cardiology queries and verify streaming/response.
2. **Translation Pipeline**: Verify Arabic query is translated to English for RAG vector search, then answered in Arabic.
3. **Pre-loaded Questions**: Click on any of the 20 sample cardiology questions to verify instant populate and query execution.
4. **Theme & Localization**: Toggle between Dark/Light modes and Arabic (RTL) / English (LTR).
5. **RAG Inspection**: Click on citation pills and RAG Inspector to view retrieved chunks, similarity scores, and guideline sections.
6. **Chat History**: Create multiple sessions, rename, switch between them, and delete.
7. **Mobile Responsiveness**: Test on mobile (375px), tablet (768px), and desktop (1280px+).
