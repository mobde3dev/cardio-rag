import React from "react";
import { GitCompare } from "lucide-react";
import { Language, getTranslation } from "@/i18n";

interface GuidelineComparisonProps {
  comparison?: {
    whoStance: string;
    niceStance: string;
    consensus: string;
  };
  language: Language;
}

export const GuidelineComparison: React.FC<GuidelineComparisonProps> = ({
  comparison,
  language,
}) => {
  const t = getTranslation(language);
  if (!comparison) return null;

  return (
    <div className="rounded-2xl border border-medical-200 dark:border-medical-900 bg-medical-50/40 dark:bg-medical-950/20 p-4 space-y-3">
      <div className="flex items-center gap-2 text-xs font-bold text-medical-800 dark:text-medical-200">
        <GitCompare className="h-4 w-4 text-medical-600 dark:text-medical-400" />
        <span>{t.guidelineComparisonTitle}</span>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-xs">
        {/* WHO Stance */}
        <div className="rounded-xl bg-white dark:bg-slate-900 p-3 border border-slate-200 dark:border-slate-800 space-y-1">
          <span className="font-bold text-[11px] text-slate-900 dark:text-slate-100 flex items-center gap-1.5">
            <span className="h-2 w-2 rounded-full bg-blue-500" />
            {t.whoRecommendation}
          </span>
          <p className="text-slate-600 dark:text-slate-400 leading-relaxed text-[11px]">
            {comparison.whoStance}
          </p>
        </div>

        {/* NICE Stance */}
        <div className="rounded-xl bg-white dark:bg-slate-900 p-3 border border-slate-200 dark:border-slate-800 space-y-1">
          <span className="font-bold text-[11px] text-slate-900 dark:text-slate-100 flex items-center gap-1.5">
            <span className="h-2 w-2 rounded-full bg-medical-500" />
            {t.niceRecommendation}
          </span>
          <p className="text-slate-600 dark:text-slate-400 leading-relaxed text-[11px]">
            {comparison.niceStance}
          </p>
        </div>
      </div>

      {/* Consensus */}
      <div className="rounded-xl bg-emerald-50/60 dark:bg-emerald-950/30 p-2.5 border border-emerald-200/80 dark:border-emerald-900/60 text-[11px] text-emerald-900 dark:text-emerald-200">
        <span className="font-bold">{t.consensusSummary}: </span>
        <span>{comparison.consensus}</span>
      </div>
    </div>
  );
};
