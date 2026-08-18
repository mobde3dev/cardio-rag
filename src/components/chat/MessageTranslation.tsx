"use client";

import React, { useState } from "react";
import { Globe, ChevronDown, ChevronUp } from "lucide-react";
import { TranslationMeta } from "@/types/chat";
import { Language, getTranslation } from "@/i18n";

interface MessageTranslationProps {
  translation: TranslationMeta;
  language: Language;
}

export const MessageTranslation: React.FC<MessageTranslationProps> = ({
  translation,
  language,
}) => {
  const [expanded, setExpanded] = useState(false);
  const t = getTranslation(language);

  if (!translation || translation.detectedLang !== "ar") return null;

  return (
    <div className="mb-2.5 rounded-xl border border-medical-200/60 dark:border-medical-900/60 bg-medical-50/40 dark:bg-medical-950/20 px-3 py-1.5 text-xs">
      <button
        onClick={() => setExpanded(!expanded)}
        className="flex w-full items-center justify-between text-[11px] font-semibold text-medical-800 dark:text-medical-300"
      >
        <span className="flex items-center gap-1.5">
          <Globe className="h-3.5 w-3.5 text-medical-600 dark:text-medical-400" />
          <span>{t.translationBreakdown}</span>
          <span className="font-mono text-[10px] text-slate-400">
            ({translation.latencyMs}ms)
          </span>
        </span>
        {expanded ? (
          <ChevronUp className="h-3.5 w-3.5" />
        ) : (
          <ChevronDown className="h-3.5 w-3.5" />
        )}
      </button>

      {expanded && (
        <div className="mt-2 space-y-1.5 pt-1.5 border-t border-medical-200/40 dark:border-medical-900/40 text-[11px]">
          <div>
            <span className="font-bold text-slate-500">{t.originalArabicQuery}:</span>
            <p className="text-slate-800 dark:text-slate-200 mt-0.5">
              {translation.originalQuery}
            </p>
          </div>
          <div>
            <span className="font-bold text-medical-700 dark:text-medical-400">
              {t.translatedEnglishQuery}:
            </span>
            <p className="text-slate-800 dark:text-slate-200 font-mono text-[10px] mt-0.5 bg-white/70 dark:bg-slate-900/70 p-1.5 rounded-lg border border-slate-200 dark:border-slate-800">
              {translation.translatedQuery}
            </p>
          </div>
        </div>
      )}
    </div>
  );
};
