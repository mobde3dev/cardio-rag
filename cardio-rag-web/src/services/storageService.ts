import { ChatSession } from "@/types/chat";
import { AppSettings } from "@/types/settings";
import { Language } from "@/i18n";

const SESSIONS_KEY = "cardio_rag_sessions_v1";
const SETTINGS_KEY = "cardio_rag_settings_v1";
const THEME_KEY = "cardio_rag_theme_v1";
const LANG_KEY = "cardio_rag_lang_v1";

export const DEFAULT_SETTINGS: AppSettings = {
  groqApiKey: "",
  selectedModel: "openai/gpt-oss-120b",
  translationModel: "openai/gpt-oss-20b",
  temperature: 0.15,
  topK: 4,
  confidenceThreshold: 0.70,
  autoTranslateArabic: true,
  streamResponse: true,
  soundEffects: false,
};

export const storageService = {
  getSessions(): ChatSession[] {
    if (typeof window === "undefined") return [];
    try {
      const data = localStorage.getItem(SESSIONS_KEY);
      return data ? JSON.parse(data) : [];
    } catch {
      return [];
    }
  },

  saveSessions(sessions: ChatSession[]): void {
    if (typeof window === "undefined") return;
    try {
      localStorage.setItem(SESSIONS_KEY, JSON.stringify(sessions));
    } catch (e) {
      console.error("Failed to save sessions", e);
    }
  },

  getSettings(): AppSettings {
    if (typeof window === "undefined") return DEFAULT_SETTINGS;
    try {
      const data = localStorage.getItem(SETTINGS_KEY);
      return data ? { ...DEFAULT_SETTINGS, ...JSON.parse(data) } : DEFAULT_SETTINGS;
    } catch {
      return DEFAULT_SETTINGS;
    }
  },

  saveSettings(settings: AppSettings): void {
    if (typeof window === "undefined") return;
    try {
      localStorage.setItem(SETTINGS_KEY, JSON.stringify(settings));
    } catch (e) {
      console.error("Failed to save settings", e);
    }
  },

  getTheme(): "dark" | "light" {
    if (typeof window === "undefined") return "dark";
    const saved = localStorage.getItem(THEME_KEY);
    return saved === "light" ? "light" : "dark";
  },

  saveTheme(theme: "dark" | "light"): void {
    if (typeof window === "undefined") return;
    localStorage.setItem(THEME_KEY, theme);
  },

  getLanguage(): Language {
    if (typeof window === "undefined") return "ar";
    const saved = localStorage.getItem(LANG_KEY);
    return saved === "en" ? "en" : "ar";
  },

  saveLanguage(lang: Language): void {
    if (typeof window === "undefined") return;
    localStorage.setItem(LANG_KEY, lang);
  },
};
