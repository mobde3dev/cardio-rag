import { translations, Language } from "./translations";

export function getTranslation(lang: Language) {
  return translations[lang] || translations.ar;
}

export * from "./translations";
