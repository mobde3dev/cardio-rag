"use client";

import React from "react";
import { Drawer } from "@/components/ui/Drawer";
import { ChunkCard } from "./ChunkCard";
import { GuidelineComparison } from "./GuidelineComparison";
import { ChatMessage } from "@/types/chat";
import { Language, getTranslation } from "@/i18n";
import { BookOpen, ShieldCheck } from "lucide-react";

interface RagInspectorDrawerProps {
  isOpen: boolean;
  onClose: () => void;
  message: ChatMessage | null;
  language: Language;
}

export const RagInspectorDrawer: React.FC<RagInspectorDrawerProps> = ({
  isOpen,
  onClose,
  message,
  language,
}) => {
  const t = getTranslation(language);

  if (!message) return null;

  const chunks = message.retrievedChunks || [];

  return (
    <Drawer
      isOpen={isOpen}
      onClose={onClose}
      side={language === "ar" ? "right" : "left"}
      title={language === "ar" ? "المصادر والأدلة الطبية المعتمدة" : "Medical Evidence & Guidelines"}
      subtitle={
        language === "ar"
          ? "استعراض نصوص التوصيات المقتبسة مباشرة من إرشادات WHO 2021 و NICE NG238"
          : "Direct excerpts from WHO 2021 & NICE NG238 clinical guidelines"
      }
    >
      <div className="space-y-4 text-start">
        {/* Quality & Trust Banner */}
        <div className="rounded-xl border border-teal-200/90 dark:border-teal-900/60 bg-teal-50/50 dark:bg-teal-950/30 p-3 flex items-center justify-between">
          <div className="flex items-center gap-2 text-xs font-semibold text-teal-900 dark:text-teal-200">
            <ShieldCheck className="h-4 w-4 text-teal-600 dark:text-teal-400 shrink-0" />
            <span>
              {language === "ar"
                ? "إجابة موثقة بالكامل بناءً على الإرشادات الطبية المعتمدة"
                : "Evidence-grounded response from official guidelines"}
            </span>
          </div>
          <span className="text-[11px] font-mono font-bold px-2 py-0.5 rounded-md bg-teal-100 dark:bg-teal-900/60 text-teal-800 dark:text-teal-300">
            WHO & NICE
          </span>
        </div>

        {/* Guideline Comparison (WHO 2021 vs NICE NG238) */}
        {message.guidelineComparison && (
          <GuidelineComparison
            comparison={message.guidelineComparison}
            language={language}
          />
        )}

        {/* Retrieved Evidence Chunks List */}
        <div className="space-y-3 pt-1">
          <div className="flex items-center justify-between px-0.5">
            <h4 className="text-xs font-bold text-slate-900 dark:text-slate-100 flex items-center gap-1.5">
              <BookOpen className="h-3.5 w-3.5 text-teal-600 dark:text-teal-400" />
              <span>
                {language === "ar" ? "نصوص التوصيات المقتبسة" : "Guideline Excerpts"} ({chunks.length})
              </span>
            </h4>
          </div>

          <div className="space-y-3">
            {chunks.map((chunk, idx) => (
              <ChunkCard
                key={chunk.id}
                chunk={chunk}
                index={idx}
                language={language}
              />
            ))}
          </div>
        </div>
      </div>
    </Drawer>
  );
};
