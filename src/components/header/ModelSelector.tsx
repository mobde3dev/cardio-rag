"use client";

import React from "react";
import { Cpu, ChevronDown } from "lucide-react";
import { AVAILABLE_MODELS } from "@/config/models";
import { Language } from "@/i18n";

interface ModelSelectorProps {
  selectedModel: string;
  onChangeModel: (modelId: string) => void;
  language: Language;
}

export const ModelSelector: React.FC<ModelSelectorProps> = ({
  selectedModel,
  onChangeModel,
  language,
}) => {
  const current =
    AVAILABLE_MODELS.find((m) => m.id === selectedModel) || AVAILABLE_MODELS[0];

  return (
    <div className="relative inline-block">
      <div className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-slate-100 dark:bg-slate-800/80 border border-slate-200 dark:border-slate-700/80 text-xs font-medium text-slate-800 dark:text-slate-200">
        <Cpu className="h-3.5 w-3.5 text-medical-600 dark:text-medical-400 shrink-0" />
        <select
          value={selectedModel}
          onChange={(e) => onChangeModel(e.target.value)}
          className="bg-transparent focus:outline-none cursor-pointer pr-4 font-semibold text-slate-800 dark:text-slate-100"
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
      </div>
    </div>
  );
};
