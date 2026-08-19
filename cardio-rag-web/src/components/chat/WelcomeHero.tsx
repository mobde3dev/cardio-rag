"use client";

import React from "react";
import { Sparkles, ArrowRight, ArrowLeft } from "lucide-react";
import { SAMPLE_QUESTIONS } from "@/config/sampleQuestions";
import { Language, getTranslation } from "@/i18n";
import { Badge } from "@/components/ui/Badge";
import { Card } from "@/components/ui/Card";
import cardioRagLogo from "../../app/assets/full-logo-removebg-preview.png";

interface WelcomeHeroProps {
  onSelectPrompt: (promptText: string) => void;
  language: Language;
}

export const WelcomeHero: React.FC<WelcomeHeroProps> = ({
  onSelectPrompt,
  language,
}) => {
  const t = getTranslation(language);
  const isRTL = language === "ar";
  const ArrowIcon = isRTL ? ArrowLeft : ArrowRight;

  const featuredQuestions = [
    SAMPLE_QUESTIONS[0],
    SAMPLE_QUESTIONS[4],
    SAMPLE_QUESTIONS[10],
    SAMPLE_QUESTIONS[13],
  ];

  return (
    <div className="flex flex-col items-center justify-center py-4 sm:py-6 md:py-10 max-w-2xl mx-auto text-center space-y-4 sm:space-y-6 animate-fade-in px-2">

      {/* Logo */}
   <div className="w-full flex justify-center">
  <img
    src={cardioRagLogo.src}
    alt="CardioRAG - Clinical AI Decision Support"
    className="w-[380px] sm:w-[480px] md:w-[560px] lg:w-[620px] h-auto object-contain"
  />
</div>

     <p className="text-xs sm:text-sm text-slate-500 dark:text-slate-400 max-w-lg mx-auto leading-relaxed px-2">
  {language === "ar"
    ? "مساعد ذكي لدعم القرار السريري، يقدّم رؤى موثوقة مبنية على أحدث الإرشادات الطبية."
    : "An intelligent clinical decision support assistant delivering reliable, evidence-based insights from trusted medical guidelines."}
</p>


      {/* Badges */}
      <div className="flex flex-wrap justify-center gap-1.5 sm:gap-2 pt-1">

        <Badge variant="medical" size="sm">
          WHO 2021 (Pharmacology)
        </Badge>

        <Badge variant="cardio" size="sm">
          NICE NG238 (Lipids & Statins)
        </Badge>
      </div>

      {/* Featured Clinical Question Cards */}
      <div className="w-full space-y-2 pt-1 sm:pt-2 text-start">
        <span className="text-xs font-bold text-slate-700 dark:text-slate-300 flex items-center gap-1.5 px-1">
          <Sparkles className="h-3.5 w-3.5 text-medical-600 dark:text-medical-400" />

          <span>
            {language === "ar"
              ? "أسئلة سريرية شائعة للتجربة:"
              : "Suggested Clinical Queries:"}
          </span>
        </span>

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 sm:gap-2.5">
          {featuredQuestions.map((q) => {
            const displayText =
              language === "ar" ? q.questionAr : q.questionEn;

            return (
              <Card
                key={q.id}
                hoverable
                onClick={() => onSelectPrompt(displayText)}
                className="p-3 sm:p-3.5 bg-white/80 dark:bg-slate-900/80 hover:border-medical-500/60 transition-all group min-h-[72px] flex flex-col justify-between"
              >
                <div className="flex items-center justify-between mb-1.5">
                  <span className="text-[10px] font-bold text-medical-600 dark:text-medical-400">
                    {language === "ar"
                      ? q.categoryLabelAr
                      : q.categoryLabelEn}
                  </span>

                  <ArrowIcon className="h-3.5 w-3.5 text-slate-300 group-hover:text-medical-600 transition-transform group-hover:translate-x-0.5 rtl:group-hover:-translate-x-0.5 shrink-0" />
                </div>

                <p className="text-xs text-slate-700 dark:text-slate-300 font-medium leading-relaxed line-clamp-2">
                  {displayText}
                </p>
              </Card>
            );
          })}
        </div>
      </div>
    </div>
  );
};