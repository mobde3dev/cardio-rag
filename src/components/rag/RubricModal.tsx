"use client";

import React from "react";
import { Award, CheckCircle2 } from "lucide-react";
import { Modal } from "@/components/ui/Modal";
import { Badge } from "@/components/ui/Badge";
import { HACKATHON_RUBRIC } from "@/config/rubricCriteria";
import { Language, getTranslation } from "@/i18n";

interface RubricModalProps {
  isOpen: boolean;
  onClose: () => void;
  language: Language;
}

export const RubricModal: React.FC<RubricModalProps> = ({
  isOpen,
  onClose,
  language,
}) => {
  const t = getTranslation(language);

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title={t.rubricModalTitle}
      description={t.rubricModalDesc}
      maxWidth="2xl"
    >
      <div className="space-y-4">
        {/* Total Score Banner */}
        <div className="flex items-center justify-between rounded-2xl bg-gradient-to-r from-medical-600 to-medical-800 p-4 text-white shadow-md">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-white/20">
              <Award className="h-6 w-6 text-amber-300" />
            </div>
            <div>
              <h4 className="text-sm font-bold">
                {language === "ar"
                  ? "معايير التقييم للهاكاثون السريري"
                  : "Clinical Hackathon Evaluation Score"}
              </h4>
              <p className="text-xs text-white/80">
                {language === "ar"
                  ? "تغطية شاملة لكافة محاور التقييم السبعة"
                  : "Comprehensive 7-pillar clinical RAG evaluation"}
              </p>
            </div>
          </div>
          <div className="text-right rtl:text-left">
            <span className="text-2xl font-black font-mono">100</span>
            <span className="text-xs text-white/80 block">
              {t.maxPointsLabel}
            </span>
          </div>
        </div>

        {/* Pillars List */}
        <div className="space-y-3">
          {HACKATHON_RUBRIC.map((item) => (
            <div
              key={item.id}
              className="rounded-2xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 p-4 space-y-2"
            >
              <div className="flex items-center justify-between">
                <h5 className="text-xs font-bold text-slate-900 dark:text-slate-100">
                  {language === "ar" ? item.titleAr : item.title}
                </h5>
                <Badge variant="medical" size="sm">
                  {item.maxPoints} {t.maxPointsLabel}
                </Badge>
              </div>

              <p className="text-xs text-slate-600 dark:text-slate-400 leading-relaxed">
                {language === "ar" ? item.descriptionAr : item.description}
              </p>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-1.5 pt-1">
                {(language === "ar" ? item.checksAr : item.checks).map(
                  (check, cIdx) => (
                    <div
                      key={cIdx}
                      className="flex items-start gap-1.5 text-[11px] text-slate-700 dark:text-slate-300"
                    >
                      <CheckCircle2 className="h-3.5 w-3.5 text-emerald-500 shrink-0 mt-0.5" />
                      <span>{check}</span>
                    </div>
                  )
                )}
              </div>
            </div>
          ))}
        </div>
      </div>
    </Modal>
  );
};
