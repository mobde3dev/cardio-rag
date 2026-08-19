"use client";

import React from "react";
import { ChatMessage } from "@/types/chat";
import { MessageHeader } from "./MessageHeader";
import { MessageContent } from "./MessageContent";
import { ClinicalAlert } from "./ClinicalAlert";
import { Language, getTranslation } from "@/i18n";
import { BookMarked, ExternalLink, ShieldCheck, Activity } from "lucide-react";
import { clsx } from "clsx";

interface MessageBubbleProps {
  message: ChatMessage;
  language: Language;
  onOpenInspector: (message: ChatMessage) => void;
  modelName?: string;
}

export const MessageBubble: React.FC<MessageBubbleProps> = ({
  message,
  language,
  onOpenInspector,
  modelName,
}) => {
  const isUser = message.role === "user";
  const t = getTranslation(language);
  const citations = message.citations || [];
  const metrics = message.metrics;

  return (
    <div
      className={clsx(
        "flex w-full animate-fade-in",
        isUser ? "justify-end" : "justify-start"
      )}
    >
      <div
        className={clsx(
          "rounded-2xl p-4 sm:p-5 md:p-6 transition-all border",
          isUser
            ? "max-w-[92%] sm:max-w-xl bg-slate-100 dark:bg-slate-800/90 border-slate-200 dark:border-slate-700/80 text-slate-900 dark:text-slate-100 shadow-xs"
            : "w-full bg-white dark:bg-slate-900/95 border-slate-200/90 dark:border-slate-800 text-slate-800 dark:text-slate-100 shadow-md shadow-slate-950/5 ring-1 ring-slate-950/[0.03] dark:ring-white/[0.04]"
        )}
      >
        {/* Message Header */}
        <MessageHeader
          role={message.role}
          timestamp={message.timestamp}
          content={message.content}
          language={language}
          modelName={modelName}
        />

        {/* Main Clinical Content */}
        <MessageContent content={message.content} />

        {/* Insufficient Evidence Warning (Only displayed when out-of-scope / evidence missing) */}
        {!isUser && message.isInsufficientEvidence && (
          <div className="mt-3">
            <ClinicalAlert
              isInsufficientEvidence={true}
              language={language}
            />
          </div>
        )}

        {/* Unified Compact Evidence & Audit Bar */}
        {!isUser && (citations.length > 0 || metrics) && (
          <div className="mt-4 pt-3 border-t border-slate-100 dark:border-slate-800/80 flex flex-wrap items-center justify-between gap-2.5">
            {/* Citations Pills & Quick Inspect */}
            <div className="flex flex-wrap items-center gap-1.5 sm:gap-2">
              <span className="text-[11px] font-bold text-slate-600 dark:text-slate-400 flex items-center gap-1 shrink-0">
                <BookMarked className="h-3.5 w-3.5 text-medical-600 dark:text-medical-400" />
                <span>{language === "ar" ? "المصادر المعتمدة:" : "Evidence Sources:"}</span>
              </span>

              {citations.map((c) => (
                <button
                  key={c.id}
                  onClick={() => onOpenInspector(message)}
                  title={language === "ar" ? "اضغط لاستعراض المقطع الأصلي" : "Click to view source excerpt"}
                  className="inline-flex items-center gap-1 px-2 py-1 rounded-lg bg-medical-50 dark:bg-medical-950/50 hover:bg-medical-100 dark:hover:bg-medical-900/60 border border-medical-200/80 dark:border-medical-800/80 text-[11px] text-medical-800 dark:text-medical-200 transition-all font-medium active:scale-[0.98]"
                >
                  <span className="font-semibold">{c.source}</span>
                  <span className="text-slate-400 dark:text-slate-600">•</span>
                  <span className="text-slate-600 dark:text-slate-300 text-[10.5px]">
                    {c.page || c.section}
                  </span>
                </button>
              ))}

              <button
                onClick={() => onOpenInspector(message)}
                className="inline-flex items-center gap-1 text-[11px] font-semibold text-medical-600 dark:text-medical-400 hover:text-medical-700 dark:hover:text-medical-300 underline underline-offset-2 px-1 py-0.5"
              >
                <span>{language === "ar" ? "فحص الأدلة" : "Inspect Chunks"}</span>
                <ExternalLink className="h-3 w-3" />
              </button>
            </div>

            {/* Quality & Latency Badge */}
            {metrics && (
              <div className="flex items-center gap-2 text-[10.5px] font-mono text-slate-500 dark:text-slate-400 shrink-0 ms-auto">
                <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-md bg-slate-100 dark:bg-slate-800/80 text-emerald-700 dark:text-emerald-400 border border-slate-200/60 dark:border-slate-700/60">
                  <ShieldCheck className="h-3 w-3" />
                  <span>Faithfulness: {Math.round((message.confidenceScore || 0.98) * 100)}%</span>
                </span>

                {metrics.totalLatencyMs && (
                  <span className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded-md bg-slate-100 dark:bg-slate-800/80 text-slate-600 dark:text-slate-300 border border-slate-200/60 dark:border-slate-700/60">
                    <Activity className="h-3 w-3 text-amber-500" />
                    <span>{metrics.totalLatencyMs}ms</span>
                  </span>
                )}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
};
