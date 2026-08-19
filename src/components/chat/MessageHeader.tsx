"use client";

import React, { useState } from "react";
import { Copy, Check, Volume2, HeartPulse, User } from "lucide-react";
import { Role } from "@/types/chat";
import { Language, getTranslation } from "@/i18n";

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
    <div className="flex items-center justify-between pb-2.5 mb-2.5 border-b border-slate-100 dark:border-slate-800/80">
      <div className="flex items-center gap-2 min-w-0">
        <div
          className={`flex h-7 w-7 items-center justify-center rounded-xl shrink-0 shadow-xs ${
            role === "assistant"
              ? "bg-gradient-to-tr from-teal-600 to-teal-500 text-white"
              : "bg-slate-700 text-white"
          }`}
        >
          {role === "assistant" ? (
            <HeartPulse className="h-4 w-4" />
          ) : (
            <User className="h-4 w-4" />
          )}
        </div>
        <span className="text-xs sm:text-[13.5px] font-bold text-slate-800 dark:text-slate-100 truncate">
          {role === "assistant" ? t.assistantName : t.userName}
        </span>
        <span className="text-[10px] text-slate-400 font-mono shrink-0">
          {formattedTime}
        </span>
      </div>

      {role === "assistant" && (
        <div className="flex items-center gap-0.5 sm:gap-1 shrink-0">
          <button
            onClick={handleAudio}
            title={t.audioReadout}
            aria-label="Listen to answer"
            className="p-1.5 rounded-lg text-slate-400 hover:text-teal-600 dark:hover:text-teal-400 hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors min-h-[32px] min-w-[32px] flex items-center justify-center"
          >
            <Volume2 className="h-4 w-4" />
          </button>
          <button
            onClick={handleCopy}
            title={t.copyAnswer}
            aria-label="Copy answer text"
            className="p-1.5 rounded-lg text-slate-400 hover:text-teal-600 dark:hover:text-teal-400 hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors min-h-[32px] min-w-[32px] flex items-center justify-center"
          >
            {copied ? (
              <Check className="h-4 w-4 text-emerald-500" />
            ) : (
              <Copy className="h-4 w-4" />
            )}
          </button>
        </div>
      )}
    </div>
  );
};
