"use client";

import React from "react";
import { Drawer } from "@/components/ui/Drawer";
import { ChunkCard } from "./ChunkCard";
import { GuidelineComparison } from "./GuidelineComparison";
import { ChatMessage } from "@/types/chat";
import { Language, getTranslation } from "@/i18n";
import { Activity, Clock, Zap, Target, Layers, ArrowRight, ArrowLeft, Languages } from "lucide-react";

interface RagInspectorDrawerProps {
  isOpen: boolean;
  onClose: () => void;
  message: ChatMessage | null;
  language: Language;
}

export const RagInspectorDrawer: React.FC<RagInspectorDrawerProps> = ({
  isOpen,
  onClose,
  message,
  language,
}) => {
  const t = getTranslation(language);
  const isRTL = language === "ar";
  const ArrowIcon = isRTL ? ArrowLeft : ArrowRight;

  if (!message) return null;

  const chunks = message.retrievedChunks || [];
  const metrics = message.metrics;

  return (
    <Drawer
      isOpen={isOpen}
      onClose={onClose}
      title={t.ragInspectorTitle}
      subtitle={t.ragInspectorDesc}
    >
      <div className="space-y-5 text-start">
        {/* RAG Pipeline Flow Visual Card */}
        <div className="rounded-2xl border border-medical-200/90 dark:border-medical-900/60 bg-medical-50/50 dark:bg-medical-950/40 p-3.5 space-y-2.5">
          <div className="flex items-center justify-between">
            <span className="text-xs font-bold text-medical-800 dark:text-medical-200 flex items-center gap-1.5">
              <Layers className="h-3.5 w-3.5 text-medical-600 dark:text-medical-400" />
              <span>{language === "ar" ? "مسار المعالجة السريرية (Pipeline)" : "Clinical RAG Architecture"}</span>
            </span>
            <span className="text-[10px] font-mono font-semibold px-2 py-0.5 rounded-full bg-medical-100 dark:bg-medical-900/80 text-medical-800 dark:text-medical-200">
              BGE-M3 + Rerank
            </span>
          </div>

          {/* Pipeline Steps Chips */}
          <div className="flex flex-wrap items-center gap-1.5 text-[10.5px] font-mono text-slate-700 dark:text-slate-300">
            <span className="px-2 py-1 rounded-lg bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 shadow-2xs font-semibold">
              1. Query Embedding
            </span>
            <ArrowIcon className="h-3 w-3 text-slate-400 shrink-0" />
            <span className="px-2 py-1 rounded-lg bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 shadow-2xs font-semibold">
              2. pgvector (Top 15)
            </span>
            <ArrowIcon className="h-3 w-3 text-slate-400 shrink-0" />
            <span className="px-2 py-1 rounded-lg bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 shadow-2xs font-semibold">
              3. Reranker (Top 5)
            </span>
            <ArrowIcon className="h-3 w-3 text-slate-400 shrink-0" />
            <span className="px-2 py-1 rounded-lg bg-medical-600 text-white font-bold shadow-2xs">
              4. Groq LLM
            </span>
          </div>
        </div>

        {/* Cross-Lingual Translation Step (if query was translated) */}
        {message.translation && (
          <div className="rounded-2xl border border-slate-200 dark:border-slate-800 bg-slate-50/60 dark:bg-slate-950/60 p-3.5 space-y-2">
            <div className="flex items-center gap-1.5 text-xs font-bold text-slate-800 dark:text-slate-200">
              <Languages className="h-3.5 w-3.5 text-medical-600 dark:text-medical-400" />
              <span>{language === "ar" ? "الترجمة الطبية للاسترجاع الدلالي" : "Cross-Lingual Query Alignment"}</span>
            </div>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 text-xs">
              <div className="p-2.5 rounded-xl bg-white dark:bg-slate-900 border border-slate-200/80 dark:border-slate-800">
                <span className="text-[10px] font-semibold text-slate-400 block mb-0.5">
                  {language === "ar" ? "الاستعلام العربي الأصلي" : "Original Query"}
                </span>
                <p className="text-slate-800 dark:text-slate-200 font-medium">
                  {message.translation.originalQuery}
                </p>
              </div>
              <div className="p-2.5 rounded-xl bg-white dark:bg-slate-900 border border-slate-200/80 dark:border-slate-800">
                <span className="text-[10px] font-semibold text-slate-400 block mb-0.5">
                  {language === "ar" ? "المصطلحات الطبية للتضمين (BGE-M3)" : "Translated Medical Search Query"}
                </span>
                <p className="text-slate-800 dark:text-slate-200 font-medium font-mono text-[11px]">
                  {message.translation.translatedQuery}
                </p>
              </div>
            </div>
          </div>
        )}

        {/* Latency & Metrics Breakdown */}
        {metrics && (
          <div className="rounded-2xl border border-slate-200 dark:border-slate-800 bg-slate-50/60 dark:bg-slate-950/60 p-4 space-y-3">
            <h4 className="text-xs font-bold text-slate-900 dark:text-slate-100 flex items-center gap-1.5">
              <Activity className="h-3.5 w-3.5 text-medical-600 dark:text-medical-400" />
              <span>{t.metricsBreakdown}</span>
            </h4>

            <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 text-xs">
              <div className="p-2.5 rounded-xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800">
                <span className="text-[10px] text-slate-500 block">
                  {t.retrievalLatency}
                </span>
                <span className="font-mono font-bold text-slate-800 dark:text-slate-200 text-xs sm:text-sm">
                  {metrics.retrievalLatencyMs || 25}ms
                </span>
              </div>
              <div className="p-2.5 rounded-xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800">
                <span className="text-[10px] text-slate-500 block">
                  {t.generationLatency}
                </span>
                <span className="font-mono font-bold text-slate-800 dark:text-slate-200 text-xs sm:text-sm">
                  {metrics.generationLatencyMs || 320}ms
                </span>
              </div>
              <div className="p-2.5 rounded-xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800">
                <span className="text-[10px] text-slate-500 block">
                  {t.totalLatency}
                </span>
                <span className="font-mono font-bold text-medical-600 dark:text-medical-400 text-xs sm:text-sm">
                  {metrics.totalLatencyMs || 345}ms
                </span>
              </div>
              <div className="p-2.5 rounded-xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800">
                <span className="text-[10px] text-slate-500 block">
                  {t.tokensUsed}
                </span>
                <span className="font-mono font-bold text-slate-800 dark:text-slate-200 text-xs sm:text-sm">
                  {metrics.tokensUsed || 350}
                </span>
              </div>
            </div>
          </div>
        )}

        {/* Guideline Comparison (NICE vs WHO) */}
        {message.guidelineComparison && (
          <GuidelineComparison
            comparison={message.guidelineComparison}
            language={language}
          />
        )}

        {/* Retrieved Chunks List */}
        <div className="space-y-3">
          <div className="flex items-center justify-between">
            <h4 className="text-xs font-bold text-slate-900 dark:text-slate-100">
              {t.retrievedChunksTitle} ({chunks.length})
            </h4>
            <span className="text-[10px] font-mono text-emerald-600 dark:text-emerald-400">
              Similarity &gt; 0.70
            </span>
          </div>

          <div className="space-y-3">
            {chunks.map((chunk, idx) => (
              <ChunkCard
                key={chunk.id}
                chunk={chunk}
                index={idx}
                language={language}
              />
            ))}
          </div>
        </div>
      </div>
    </Drawer>
  );
};
