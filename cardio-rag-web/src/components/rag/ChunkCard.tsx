import React from "react";
import { RetrievedChunk } from "@/types/chat";
import { ScoreMeter } from "./ScoreMeter";
import { Badge } from "@/components/ui/Badge";
import { Language } from "@/i18n";

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
    <div className="rounded-2xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900/90 p-3.5 space-y-2.5 shadow-xs">
      {/* Header */}
      <div className="flex items-start justify-between gap-2">
        <div>
          <span className="text-[10px] font-bold text-medical-600 dark:text-medical-400 uppercase tracking-wider">
            {chunk.source} • Chunk #{index + 1}
          </span>
          <h4 className="text-xs font-bold text-slate-900 dark:text-slate-100 mt-0.5">
            {chunk.title}
          </h4>
        </div>
        {chunk.recommendationStrength && (
          <Badge variant="medical" size="sm">
            {chunk.recommendationStrength}
          </Badge>
        )}
      </div>

      {/* Section & Page Info */}
      <div className="flex flex-wrap items-center gap-2 text-[10px] font-mono text-slate-500 dark:text-slate-400 bg-slate-50 dark:bg-slate-950/60 p-2 rounded-xl">
        <span>{chunk.section}</span>
        <span className="text-slate-300 dark:text-slate-700">•</span>
        <span>{chunk.page}</span>
      </div>

      {/* Content excerpt */}
      <p className="text-xs text-slate-700 dark:text-slate-300 leading-relaxed bg-slate-50/50 dark:bg-slate-950/40 p-2.5 rounded-xl border border-slate-100 dark:border-slate-800/80">
        &ldquo;{chunk.content}&rdquo;
      </p>

      {/* Similarity Score Meter */}
      <ScoreMeter
        score={chunk.similarityScore}
        label={language === "ar" ? "نسبة التطابق الدلالي (Cosine Similarity)" : "Cosine Similarity"}
      />
    </div>
  );
};
