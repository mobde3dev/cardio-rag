import React from "react";
import { AlertTriangle, ShieldAlert } from "lucide-react";
import { Language, getTranslation } from "@/i18n";

interface ClinicalAlertProps {
  isInsufficientEvidence?: boolean;
  language: Language;
}

export const ClinicalAlert: React.FC<ClinicalAlertProps> = ({
  isInsufficientEvidence,
  language,
}) => {
  const t = getTranslation(language);

  if (isInsufficientEvidence) {
    return (
      <div className="my-2.5 flex items-start gap-2.5 rounded-xl border border-amber-300 dark:border-amber-900/80 bg-amber-50/80 dark:bg-amber-950/40 p-3 text-xs text-amber-900 dark:text-amber-200">
        <AlertTriangle className="h-4 w-4 text-amber-600 dark:text-amber-400 shrink-0 mt-0.5" />
        <p className="leading-relaxed">{t.insufficientEvidenceAlert}</p>
      </div>
    );
  }

  return (
    <div className="mt-3 flex items-start gap-2 rounded-xl border border-slate-200/60 dark:border-slate-800/60 bg-slate-50/50 dark:bg-slate-950/40 px-3 py-2 text-[11px] text-slate-500 dark:text-slate-400">
      <ShieldAlert className="h-3.5 w-3.5 text-medical-600 dark:text-medical-400 shrink-0 mt-0.5" />
      <p className="leading-normal">{t.clinicalDisclaimer}</p>
    </div>
  );
};
