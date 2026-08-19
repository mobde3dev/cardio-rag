"use client";

import React from "react";
import { ChatMessage } from "@/types/chat";
import { MessageHeader } from "./MessageHeader";
import { MessageContent } from "./MessageContent";
import { MessageCitations } from "./MessageCitations";
import { MessageTranslation } from "./MessageTranslation";
import { MessageMetrics } from "./MessageMetrics";
import { ClinicalAlert } from "./ClinicalAlert";
import { Language } from "@/i18n";
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

  return (
    <div
      className={clsx(
        "flex w-full animate-fade-in",
        isUser ? "justify-end" : "justify-start"
      )}
    >
      <div
        className={clsx(
          "w-full rounded-2xl p-3 sm:p-4 md:p-5 transition-all shadow-xs border",
          isUser
            ? "max-w-[92%] sm:max-w-lg md:max-w-xl bg-slate-100 dark:bg-slate-800/90 border-slate-200 dark:border-slate-700/80 text-slate-900 dark:text-slate-100"
            : "max-w-[98%] sm:max-w-2xl md:max-w-3xl bg-white dark:bg-slate-900/95 border-slate-200/90 dark:border-slate-800 text-slate-800 dark:text-slate-100 shadow-md shadow-slate-950/5"
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

        {/* Translation Pipeline Details (if Arabic query was translated for RAG) */}
        {message.translation && (
          <MessageTranslation
            translation={message.translation}
            language={language}
          />
        )}

        {/* Main Clinical Content */}
        <MessageContent content={message.content} />

        {/* Citations & Evidence Pill Badges */}
        {message.citations && message.citations.length > 0 && (
          <MessageCitations
            citations={message.citations}
            onOpenInspector={() => onOpenInspector(message)}
            language={language}
          />
        )}

        {/* Metrics Badge Strip (Faithfulness, P@k, Latency) */}
        {!isUser && (
          <MessageMetrics
            metrics={message.metrics}
            confidenceScore={message.confidenceScore}
            language={language}
          />
        )}

        {/* Clinical Safety & Disclaimer Notice */}
        {!isUser && (
          <ClinicalAlert
            isInsufficientEvidence={message.isInsufficientEvidence}
            language={language}
          />
        )}
      </div>
    </div>
  );
};
