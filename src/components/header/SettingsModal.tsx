"use client";

import React, { useState } from "react";
import { Modal } from "@/components/ui/Modal";
import { Button } from "@/components/ui/Button";
import { AppSettings } from "@/types/settings";
import { AVAILABLE_MODELS } from "@/config/models";
import { Language, getTranslation } from "@/i18n";
import { DEFAULT_SETTINGS, storageService } from "@/services/storageService";
import { Key, Sliders, ShieldCheck } from "lucide-react";

interface SettingsModalProps {
  isOpen: boolean;
  onClose: () => void;
  settings: AppSettings;
  onSaveSettings: (settings: AppSettings) => void;
  language: Language;
}

export const SettingsModal: React.FC<SettingsModalProps> = ({
  isOpen,
  onClose,
  settings,
  onSaveSettings,
  language,
}) => {
  const [formData, setFormData] = useState<AppSettings>(settings);
  const t = getTranslation(language);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    onSaveSettings(formData);
    storageService.saveSettings(formData);
    onClose();
  };

  const handleReset = () => {
    setFormData(DEFAULT_SETTINGS);
  };

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title={t.settingsTitle}
      maxWidth="md"
    >
      <form onSubmit={handleSubmit} className="space-y-4">
        {/* Groq API Key */}
        <div className="space-y-1.5">
          <label className="flex items-center gap-1.5 text-xs font-semibold text-slate-700 dark:text-slate-300">
            <Key className="h-3.5 w-3.5 text-medical-600 dark:text-medical-400" />
            {t.groqApiKeyLabel}
          </label>
          <input
            type="password"
            value={formData.groqApiKey}
            onChange={(e) =>
              setFormData({ ...formData, groqApiKey: e.target.value })
            }
            placeholder="gsk_..."
            className="w-full rounded-xl border border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-950 px-3 py-2 text-base sm:text-sm text-slate-900 dark:text-slate-100 focus:border-medical-500 focus:outline-none focus:ring-1 focus:ring-medical-500"
          />
          <p className="text-[11px] text-slate-500 dark:text-slate-400">
            {t.groqApiKeyHelp}
          </p>
        </div>

        {/* Primary Model */}
        <div className="space-y-1.5">
          <label className="text-xs font-semibold text-slate-700 dark:text-slate-300">
            {t.modelSelectionLabel}
          </label>
          <select
            value={formData.selectedModel}
            onChange={(e) =>
              setFormData({ ...formData, selectedModel: e.target.value })
            }
            className="w-full rounded-xl border border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-950 px-3 py-2 text-base sm:text-sm text-slate-900 dark:text-slate-100 focus:border-medical-500 focus:outline-none"
          >
            {AVAILABLE_MODELS.map((m) => (
              <option key={m.id} value={m.id}>
                {m.name}
              </option>
            ))}
          </select>
        </div>

        {/* Translation Model */}
        <div className="space-y-1.5">
          <label className="text-xs font-semibold text-slate-700 dark:text-slate-300">
            {t.translationModelLabel}
          </label>
          <select
            value={formData.translationModel}
            onChange={(e) =>
              setFormData({ ...formData, translationModel: e.target.value })
            }
            className="w-full rounded-xl border border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-950 px-3 py-2 text-base sm:text-sm text-slate-900 dark:text-slate-100 focus:border-medical-500 focus:outline-none"
          >
            <option value="openai/gpt-oss-20b">GPT-OSS 20B (Ultra Fast)</option>
            <option value="qwen/qwen3.6-27b">Qwen 3.6 27B (Bilingual Pro)</option>
            <option value="allam-2-7b">Allam 2 7B (Arabic Native)</option>
          </select>
        </div>

        {/* Temperature Slider */}
        <div className="space-y-1.5 pt-1">
          <div className="flex justify-between text-xs font-semibold text-slate-700 dark:text-slate-300">
            <span>{t.temperatureLabel}</span>
            <span className="font-mono text-medical-600 dark:text-medical-400">
              {formData.temperature}
            </span>
          </div>
          <input
            type="range"
            min="0"
            max="0.8"
            step="0.05"
            value={formData.temperature}
            onChange={(e) =>
              setFormData({
                ...formData,
                temperature: parseFloat(e.target.value),
              })
            }
            className="w-full accent-medical-600 h-2 cursor-pointer"
          />
          <p className="text-[11px] text-slate-500 dark:text-slate-400">
            {t.temperatureHelp}
          </p>
        </div>

        {/* Top-K Chunks Slider */}
        <div className="space-y-1.5">
          <div className="flex justify-between text-xs font-semibold text-slate-700 dark:text-slate-300">
            <span>{t.topKLabel}</span>
            <span className="font-mono text-medical-600 dark:text-medical-400">
              {formData.topK}
            </span>
          </div>
          <input
            type="range"
            min="2"
            max="8"
            step="1"
            value={formData.topK}
            onChange={(e) =>
              setFormData({ ...formData, topK: parseInt(e.target.value, 10) })
            }
            className="w-full accent-medical-600 h-2 cursor-pointer"
          />
        </div>

        {/* Buttons */}
        <div className="flex flex-wrap items-center justify-between gap-2 pt-4 border-t border-slate-100 dark:border-slate-800">
          <Button
            type="button"
            variant="ghost"
            size="sm"
            onClick={handleReset}
          >
            {t.resetDefaults}
          </Button>
          <div className="flex gap-2">
            <Button
              type="button"
              variant="outline"
              size="sm"
              onClick={onClose}
            >
              {language === "ar" ? "إلغاء" : "Cancel"}
            </Button>
            <Button type="submit" variant="primary" size="sm">
              {t.saveSettings}
            </Button>
          </div>
        </div>
      </form>
    </Modal>
  );
};
