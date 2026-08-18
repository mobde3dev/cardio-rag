"use client";

import React from "react";
import { Drawer } from "@/components/ui/Drawer";
import { ChunkCard } from "./ChunkCard";
import { GuidelineComparison } from "./GuidelineComparison";
import { ChatMessage } from "@/types/chat";
import { Language, getTranslation } from "@/i18n";
import { Activity, Clock, Zap, Target } from "lucide-react";

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
      <div className="space-y-6">
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

        {/* Guideline Comparison */}
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
              Threshold &gt; 0.70
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
