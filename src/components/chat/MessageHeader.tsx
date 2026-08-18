"use client";

import React, { useState } from "react";
import { Copy, Check, Volume2, Bot, User } from "lucide-react";
import { Role } from "@/types/chat";
import { Language, getTranslation } from "@/i18n";
import { Badge } from "@/components/ui/Badge";

interface MessageHeaderProps {
  role: Role;
  timestamp: number;
  content: string;
  language: Language;
  modelName?: string;
}

export const MessageHeader: React.FC<MessageHeaderProps> = ({
  role,
  timestamp,
  content,
  language,
  modelName,
}) => {
  const [copied, setCopied] = useState(false);
  const t = getTranslation(language);

  const handleCopy = () => {
    navigator.clipboard.writeText(content);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const handleAudio = () => {
    if ("speechSynthesis" in window) {
      window.speechSynthesis.cancel();
      const utterance = new SpeechSynthesisUtterance(content);
      utterance.lang = language === "ar" ? "ar-SA" : "en-US";
      window.speechSynthesis.speak(utterance);
    }
  };

  const formattedTime = new Date(timestamp).toLocaleTimeString([], {
    hour: "2-digit",
    minute: "2-digit",
  });

  return (
    <div className="flex items-center justify-between pb-2 mb-2 border-b border-slate-100 dark:border-slate-800/80">
      <div className="flex items-center gap-2">
        <div
          className={`flex h-6 w-6 items-center justify-center rounded-lg ${
            role === "assistant"
              ? "bg-medical-600 text-white"
              : "bg-slate-700 text-white"
          }`}
        >
          {role === "assistant" ? (
            <Bot className="h-3.5 w-3.5" />
          ) : (
            <User className="h-3.5 w-3.5" />
          )}
        </div>
        <span className="text-xs font-bold text-slate-800 dark:text-slate-200">
          {role === "assistant" ? t.assistantName : t.userName}
        </span>
        {modelName && role === "assistant" && (
          <Badge variant="medical" size="sm" className="hidden sm:inline-flex">
            {modelName.split("/")[1] || modelName}
          </Badge>
        )}
        <span className="text-[10px] text-slate-400 font-mono">
          {formattedTime}
        </span>
      </div>

      {role === "assistant" && (
        <div className="flex items-center gap-1">
          <button
            onClick={handleAudio}
            title={t.audioReadout}
            aria-label="Listen to answer"
            className="p-1 rounded-md text-slate-400 hover:text-medical-600 dark:hover:text-medical-400 hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors"
          >
            <Volume2 className="h-3.5 w-3.5" />
          </button>
          <button
            onClick={handleCopy}
            title={t.copyAnswer}
            aria-label="Copy answer text"
            className="p-1 rounded-md text-slate-400 hover:text-medical-600 dark:hover:text-medical-400 hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors"
          >
            {copied ? (
              <Check className="h-3.5 w-3.5 text-emerald-500" />
            ) : (
              <Copy className="h-3.5 w-3.5" />
            )}
          </button>
        </div>
      )}
    </div>
  );
};
