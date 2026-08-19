"use client";

import React, { useState } from "react";
import { Sparkles, BookOpen } from "lucide-react";
import { SAMPLE_QUESTIONS, SampleQuestion } from "@/config/sampleQuestions";
import { Language, getTranslation } from "@/i18n";
import { Badge } from "@/components/ui/Badge";

interface PromptLibraryProps {
  onSelectPrompt: (promptText: string) => void;
  language: Language;
}

export const PromptLibrary: React.FC<PromptLibraryProps> = ({
  onSelectPrompt,
  language,
}) => {
  const [activeCategory, setActiveCategory] = useState<string>("all");
  const t = getTranslation(language);

  const categories = [
    { id: "all", label: t.promptCategories.all },
    { id: "hypertension", label: t.promptCategories.hypertension },
    { id: "lipids", label: t.promptCategories.lipids },
    { id: "safety_pregnancy", label: t.promptCategories.safety_pregnancy },
    { id: "risk_tools", label: t.promptCategories.risk_tools },
    { id: "guideline_comparison", label: t.promptCategories.guideline_comparison },
  ];

  const filteredQuestions =
    activeCategory === "all"
      ? SAMPLE_QUESTIONS
      : SAMPLE_QUESTIONS.filter((q) => q.category === activeCategory);

  return (
    <div className="flex flex-col space-y-2.5">
      {/* Category Pills */}
      <div className="flex gap-1.5 overflow-x-auto pb-1.5 no-scrollbar -mx-1 px-1 touch-pan-x">
        {categories.map((cat) => (
          <button
            key={cat.id}
            onClick={() => setActiveCategory(cat.id)}
            className={`whitespace-nowrap px-2.5 py-1 text-[11px] font-medium rounded-lg transition-colors min-h-[32px] flex items-center shrink-0 ${
              activeCategory === cat.id
                ? "bg-medical-600 text-white shadow-xs"
                : "bg-slate-100 dark:bg-slate-800/80 text-slate-600 dark:text-slate-400 hover:bg-slate-200 dark:hover:bg-slate-700"
            }`}
          >
            {cat.label}
          </button>
        ))}
      </div>

      {/* Questions Scrollable List */}
      <div className="space-y-1.5 overflow-y-auto max-h-64 pr-1">
        {filteredQuestions.map((q) => {
          const displayText = language === "ar" ? q.questionAr : q.questionEn;
          return (
            <button
              key={q.id}
              onClick={() => onSelectPrompt(displayText)}
              className="w-full text-start p-2.5 rounded-xl border border-slate-200/80 dark:border-slate-800 bg-white/60 dark:bg-slate-900/60 hover:bg-medical-50/60 dark:hover:bg-medical-950/30 hover:border-medical-300 dark:hover:border-medical-800 transition-all text-xs text-slate-700 dark:text-slate-300 group"
            >
              <div className="flex items-center justify-between mb-1">
                <span className="text-[10px] font-semibold text-medical-600 dark:text-medical-400">
                  {language === "ar" ? q.categoryLabelAr : q.categoryLabelEn}
                </span>
                <span className="text-[10px] font-mono text-slate-400">
                  {q.primaryGuideline}
                </span>
              </div>
              <p className="line-clamp-2 leading-relaxed text-[11px] group-hover:text-medical-800 dark:group-hover:text-medical-200">
                {displayText}
              </p>
            </button>
          );
        })}
      </div>
    </div>
  );
};
