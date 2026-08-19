"use client";

import React from "react";
import { Activity, Clock, Zap, Target } from "lucide-react";
import { RagMetrics } from "@/types/chat";
import { Language, getTranslation } from "@/i18n";

interface MessageMetricsProps {
  metrics?: RagMetrics;
  confidenceScore?: number;
  language: Language;
}

export const MessageMetrics: React.FC<MessageMetricsProps> = ({
  metrics,
  confidenceScore,
  language,
}) => {
  const t = getTranslation(language);
  if (!metrics) return null;

  return (
    <div className="mt-2.5 flex flex-wrap items-center gap-2 text-[10px] font-mono text-slate-500 dark:text-slate-400">
      {/* Grounded / Confidence Score */}
      {confidenceScore !== undefined && (
        <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-md bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-300">
          <Target className="h-3 w-3 text-emerald-500" />
          <span>
            {t.groundedScore}: {Math.round(confidenceScore * 100)}%
          </span>
        </span>
      )}

      {/* Precision@k */}
      {metrics.precisionAtK !== undefined && (
        <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-md bg-slate-100 dark:bg-slate-800">
          <Activity className="h-3 w-3 text-medical-500" />
          <span>P@k: {metrics.precisionAtK}</span>
        </span>
      )}

      {/* Latency */}
      {metrics.totalLatencyMs !== undefined && (
        <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-md bg-slate-100 dark:bg-slate-800">
          <Clock className="h-3 w-3 text-amber-500" />
          <span>{metrics.totalLatencyMs}ms</span>
        </span>
      )}

      {/* Tokens */}
      {metrics.tokensUsed !== undefined && (
        <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-md bg-slate-100 dark:bg-slate-800">
          <Zap className="h-3 w-3 text-indigo-500" />
          <span>{metrics.tokensUsed} tokens</span>
        </span>
      )}
    </div>
  );
};
