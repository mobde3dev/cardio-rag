"use client";

import React from "react";
import { Database, CheckCircle2 } from "lucide-react";
import { INDEXED_GUIDELINES } from "@/config/guidelines";
import { Language, getTranslation } from "@/i18n";
import { Badge } from "@/components/ui/Badge";

interface GuidelineStatusProps {
  language: Language;
}

export const GuidelineStatus: React.FC<GuidelineStatusProps> = ({ language }) => {
  const t = getTranslation(language);

  return (
    <div className="rounded-2xl border border-slate-200/80 dark:border-slate-800 bg-slate-50/50 dark:bg-slate-900/40 p-3 space-y-2">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-1.5 text-xs font-semibold text-slate-800 dark:text-slate-200">
          <Database className="h-3.5 w-3.5 text-medical-600 dark:text-medical-400" />
          <span>{t.guidelines}</span>
        </div>
        <span className="flex h-2 w-2 relative">
          <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
          <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-500"></span>
        </span>
      </div>

      <div className="space-y-1.5">
        {INDEXED_GUIDELINES.map((g) => (
          <div
            key={g.id}
            className="flex items-center justify-between text-[11px] text-slate-600 dark:text-slate-400"
          >
            <span className="font-semibold text-slate-800 dark:text-slate-200 truncate">
              {g.name}
            </span>
            <span className="font-mono text-[10px] text-emerald-600 dark:text-emerald-400">
              {g.totalChunksCount} chunks
            </span>
          </div>
        ))}
      </div>
    </div>
  );
};
