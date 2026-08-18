"use client";

import React from "react";
import { Languages } from "lucide-react";
import { Language } from "@/i18n";
import { Button } from "@/components/ui/Button";

interface LanguageToggleProps {
  currentLanguage: Language;
  onToggle: () => void;
}

export const LanguageToggle: React.FC<LanguageToggleProps> = ({
  currentLanguage,
  onToggle,
}) => {
  return (
    <Button
      variant="outline"
      size="sm"
      onClick={onToggle}
      aria-label="Toggle language"
      className="font-semibold text-xs border-slate-200 dark:border-slate-800"
    >
      <Languages className="h-4 w-4 text-medical-600 dark:text-medical-400" />
      <span>{currentLanguage === "ar" ? "English" : "العربية"}</span>
    </Button>
  );
};
