"use client";

import React from "react";
import { ChatMessage } from "@/types/chat";
import { MessageHeader } from "./MessageHeader";
import { MessageContent } from "./MessageContent";
import { ClinicalAlert } from "./ClinicalAlert";
import { Language } from "@/i18n";
import { BookMarked, ExternalLink } from "lucide-react";
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
}) => {
  const isUser = message.role === "user";
  const citations = message.citations || [];

  return (
    <div
      className={clsx(
        "flex w-full animate-fade-in",
        isUser ? "justify-end rtl:justify-start ltr:justify-end" : "justify-start"
      )}
    >
      <div
        className={clsx(
          "transition-all border",
          isUser
            ? "max-w-[92%] sm:max-w-xl rounded-2xl p-3.5 sm:p-4 bg-slate-100 dark:bg-slate-800/90 border-slate-200/90 dark:border-slate-700/80 text-slate-900 dark:text-slate-100 shadow-xs"
            : "w-full rounded-2xl p-4 sm:p-5 md:p-6 bg-white dark:bg-slate-900/95 border-slate-200/90 dark:border-slate-800 text-slate-800 dark:text-slate-100 shadow-md shadow-slate-950/5 ring-1 ring-slate-950/[0.03] dark:ring-white/[0.04]"
        )}
      >
        {/* Assistant Header (Only on Assistant messages) */}
        {!isUser && (
          <MessageHeader
            role={message.role}
            timestamp={message.timestamp}
            content={message.content}
            language={language}
          />
        )}

        {/* Message Content */}
        {isUser ? (
          <p
            dir="auto"
            className="text-[14px] sm:text-[15px] font-medium leading-relaxed text-slate-900 dark:text-slate-100"
          >
            {message.content}
          </p>
        ) : (
          <MessageContent content={message.content} />
        )}

        {/* Insufficient Evidence Warning (Only displayed when evidence is missing) */}
        {!isUser && message.isInsufficientEvidence && (
          <div className="mt-3">
            <ClinicalAlert
              isInsufficientEvidence={true}
              language={language}
            />
          </div>
        )}

        {/* Clean Approved Sources Strip */}
        {!isUser && citations.length > 0 && (
          <div className="mt-4 pt-3 border-t border-slate-100 dark:border-slate-800/80 flex flex-wrap items-center justify-between gap-2.5">
            <div className="flex flex-wrap items-center gap-1.5 sm:gap-2">
              <span className="text-[11px] font-bold text-slate-600 dark:text-slate-400 flex items-center gap-1 shrink-0">
                <BookMarked className="h-3.5 w-3.5 text-teal-600 dark:text-teal-400" />
                <span>{language === "ar" ? "المصادر المعتمدة:" : "Evidence Sources:"}</span>
              </span>

              {citations.map((c) => (
                <button
                  key={c.id}
                  onClick={() => onOpenInspector(message)}
                  title={language === "ar" ? "اضغط لعرض نص التوصية من الدليل" : "Click to view guideline excerpt"}
                  className="inline-flex items-center gap-1 px-2.5 py-1 rounded-lg bg-teal-50 dark:bg-teal-950/50 hover:bg-teal-100 dark:hover:bg-teal-900/60 border border-teal-200/80 dark:border-teal-800/80 text-[11px] text-teal-900 dark:text-teal-200 transition-all font-medium active:scale-[0.98]"
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
                className="inline-flex items-center gap-1 text-[11px] font-semibold text-teal-600 dark:text-teal-400 hover:text-teal-700 dark:hover:text-teal-300 underline underline-offset-2 px-1 py-0.5"
              >
                <span>{language === "ar" ? "عرض الأدلة" : "View Evidence"}</span>
                <ExternalLink className="h-3 w-3" />
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
