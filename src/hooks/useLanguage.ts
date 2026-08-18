"use client";

import { useState, useEffect, useCallback } from "react";
import { Language, getTranslation, translations } from "@/i18n";
import { storageService } from "@/services/storageService";

export function useLanguage() {
  const [language, setLanguageState] = useState<Language>("ar");
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    const saved = storageService.getLanguage();
    setLanguageState(saved);
    document.documentElement.dir = saved === "ar" ? "rtl" : "ltr";
    document.documentElement.lang = saved;
    setMounted(true);
  }, []);

  const setLanguage = useCallback((newLang: Language) => {
    setLanguageState(newLang);
    storageService.saveLanguage(newLang);
    document.documentElement.dir = newLang === "ar" ? "rtl" : "ltr";
    document.documentElement.lang = newLang;
  }, []);

  const toggleLanguage = useCallback(() => {
    setLanguage(language === "ar" ? "en" : "ar");
  }, [language, setLanguage]);

  const t = getTranslation(language);
  const isRTL = language === "ar";

  return {
    language,
    isRTL,
    setLanguage,
    toggleLanguage,
    t,
    mounted,
  };
}
