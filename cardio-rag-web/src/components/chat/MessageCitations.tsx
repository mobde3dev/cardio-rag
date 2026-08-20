"use client";

import React from "react";
import { BookMarked, ExternalLink } from "lucide-react";
import { MessageCitation } from "@/types/chat";
import { Badge } from "@/components/ui/Badge";
import { Language, getTranslation } from "@/i18n";

interface MessageCitationsProps {
  citations: MessageCitation[];
  onOpenInspector: () => void;
  language: Language;
}

export const MessageCitations: React.FC<MessageCitationsProps> = ({
  citations,
  onOpenInspector,
  language,
}) => {
  const t = getTranslation(language);
  if (!citations || citations.length === 0) return null;

  return (
    <div className="mt-3 pt-2.5 border-t border-slate-100 dark:border-slate-800/80">
      <div className="flex items-center justify-between mb-2">
        <span className="text-[11px] font-bold text-slate-700 dark:text-slate-300 flex items-center gap-1.5">
          <BookMarked className="h-3.5 w-3.5 text-medical-600 dark:text-medical-400" />
          <span>
            {t.citationsCount} ({citations.length})
          </span>
        </span>

        <button
          onClick={onOpenInspector}
          className="text-[11px] font-semibold text-medical-600 dark:text-medical-400 hover:underline flex items-center gap-1"
        >
          <span>{t.showChunks}</span>
          <ExternalLink className="h-3 w-3" />
        </button>
      </div>

      {citations.length > 0 && (
        <div className="flex flex-wrap gap-1.5 sm:gap-2">
          {citations.map((c) => (
            <button
              key={c.id}
              onClick={onOpenInspector}
              className="inline-flex items-center gap-1.5 px-2.5 py-1.5 rounded-xl bg-medical-50/80 dark:bg-medical-950/40 hover:bg-medical-100 dark:hover:bg-medical-900/60 border border-medical-200/80 dark:border-medical-800/80 text-[11px] text-medical-800 dark:text-medical-200 transition-all min-h-[32px] active:scale-[0.98]"
            >
              <span className="font-bold shrink-0">{c.source}</span>
              <span className="text-slate-300 dark:text-slate-700">•</span>
              <span className="truncate max-w-[150px] sm:max-w-[200px] text-slate-600 dark:text-slate-300 font-mono text-[10px]">
                {c.page || c.section}
              </span>
            </button>
          ))}
        </div>
      )}
    </div>
  );
};
