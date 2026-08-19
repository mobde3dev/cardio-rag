"use client";

import React from "react";
import { Cpu, ChevronDown } from "lucide-react";
import { AVAILABLE_MODELS } from "@/config/models";
import { Language } from "@/i18n";

interface ModelSelectorProps {
  selectedModel: string;
  onChangeModel: (modelId: string) => void;
  language: Language;
  compact?: boolean;
}

export const ModelSelector: React.FC<ModelSelectorProps> = ({
  selectedModel,
  onChangeModel,
  language,
  compact = false,
}) => {
  const current =
    AVAILABLE_MODELS.find((m) => m.id === selectedModel) || AVAILABLE_MODELS[0];

  return (
    <div className="relative inline-flex items-center">
      <div className="flex items-center gap-1.5 px-2.5 sm:px-3 py-1.5 rounded-xl bg-slate-100 dark:bg-slate-800/90 border border-slate-200/90 dark:border-slate-700/80 text-xs font-medium text-slate-800 dark:text-slate-200 hover:border-medical-500/50 transition-colors">
        <Cpu className="h-3.5 w-3.5 text-medical-600 dark:text-medical-400 shrink-0" />
        <div className="relative">
          <select
            value={selectedModel}
            onChange={(e) => onChangeModel(e.target.value)}
            className="bg-transparent focus:outline-none cursor-pointer pe-4 font-semibold text-slate-800 dark:text-slate-100 text-[11px] sm:text-xs appearance-none max-w-[130px] sm:max-w-[180px] truncate"
            aria-label="Select Groq LLM model"
          >
            {AVAILABLE_MODELS.map((model) => (
              <option
                key={model.id}
                value={model.id}
                className="bg-white dark:bg-slate-900 text-slate-800 dark:text-slate-100 py-1"
              >
                {model.name} {model.badge ? `(${model.badge})` : ""}
              </option>
            ))}
          </select>
          <ChevronDown className="h-3 w-3 text-slate-400 absolute end-0 top-1/2 -translate-y-1/2 pointer-events-none" />
        </div>
      </div>
    </div>
  );
};
