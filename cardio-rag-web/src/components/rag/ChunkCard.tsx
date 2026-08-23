import React from "react";
import { RetrievedChunk } from "@/types/chat";
import { Badge } from "@/components/ui/Badge";
import { Language } from "@/i18n";
import { CheckCircle2 } from "lucide-react";

interface ChunkCardProps {
  chunk: RetrievedChunk;
  index: number;
  language: Language;
}

export const ChunkCard: React.FC<ChunkCardProps> = ({
  chunk,
  index,
  language,
}) => {
  return (
    <div className="rounded-2xl border border-slate-200/90 dark:border-slate-800 bg-white dark:bg-slate-900/90 p-4 space-y-3 shadow-xs">
      {/* Header - Enforce LTR for English guideline header */}
      <div dir="ltr" className="space-y-1.5 text-left">
        <div className="flex items-center justify-between gap-2">
          <span className="text-[11px] font-bold text-teal-600 dark:text-teal-400 uppercase tracking-wider">
            {chunk.source} • Reference #{index + 1}
          </span>
          {chunk.recommendationStrength && (
            <Badge variant="medical" size="sm" className="shrink-0">
              {chunk.recommendationStrength}
            </Badge>
          )}
        </div>
        <h4 className="text-xs sm:text-[13.5px] font-bold text-slate-900 dark:text-slate-100">
          {chunk.title}
        </h4>
      </div>

      {/* Section & Page Info (Always English Guidelines metadata) */}
      <div
        dir="ltr"
        className="flex flex-wrap items-center gap-2 text-[11px] font-mono text-slate-600 dark:text-slate-400 bg-slate-50 dark:bg-slate-950/60 px-3 py-1.5 rounded-xl border border-slate-100 dark:border-slate-800 text-left"
      >
        <span>{chunk.section}</span>
        <span className="text-slate-300 dark:text-slate-700">•</span>
        <span className="font-semibold text-slate-700 dark:text-slate-300">{chunk.page}</span>
      </div>

      {/* Content excerpt (Always English Medical Guideline Text) */}
      <div
        dir="ltr"
        className="text-left text-xs sm:text-[13px] text-slate-800 dark:text-slate-200 leading-relaxed bg-slate-50/70 dark:bg-slate-950/40 p-3 rounded-xl border border-slate-200/70 dark:border-slate-800/80 font-normal"
      >
        &ldquo;{chunk.content}&rdquo;
      </div>

      {/* Clean Verified Guideline Badge */}
      <div className="flex items-center justify-between pt-1 text-[11px] text-slate-500 dark:text-slate-400">
        <span className="inline-flex items-center gap-1 text-teal-700 dark:text-teal-400 font-medium">
          <CheckCircle2 className="h-3.5 w-3.5 text-teal-600" />
          <span>{language === "ar" ? "مقتبس وموثق من الدليل الرسمي" : "Verified Official Guideline Excerpt"}</span>
        </span>
      </div>
    </div>
  );
};
