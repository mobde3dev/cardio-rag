"use client";

import React, { useState, useRef, useEffect } from "react";
import { Send, Sparkles, Loader2 } from "lucide-react";
import { Button } from "@/components/ui/Button";
import { Language, getTranslation } from "@/i18n";

interface ChatInputProps {
  onSendMessage: (text: string) => void;
  isLoading: boolean;
  currentStep?: string;
  language: Language;
}

export const ChatInput: React.FC<ChatInputProps> = ({
  onSendMessage,
  isLoading,
  currentStep,
  language,
}) => {
  const [input, setInput] = useState("");
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const t = getTranslation(language);

  // Auto-resize textarea
  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = "auto";
      textareaRef.current.style.height = `${Math.min(
        textareaRef.current.scrollHeight,
        140
      )}px`;
    }
  }, [input]);

  const handleSubmit = (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    if (!input.trim() || isLoading) return;
    onSendMessage(input.trim());
    setInput("");
    if (textareaRef.current) {
      textareaRef.current.style.height = "auto";
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  };

  const getStepText = () => {
    if (currentStep === "translatingQuery") return t.translatingQuery;
    if (currentStep === "searchingGuidelines") return t.searchingGuidelines;
    if (currentStep === "generatingAnswer") return t.generatingAnswer;
    return t.generatingAnswer;
  };

  return (
    <div className="w-full max-w-4xl mx-auto px-4 pb-4 pt-1">
      {/* Loading Step Progress Indicator */}
      {isLoading && (
        <div className="flex items-center gap-2 text-xs font-medium text-medical-600 dark:text-medical-400 mb-2 px-3 py-1.5 rounded-xl bg-medical-50/80 dark:bg-medical-950/40 border border-medical-200 dark:border-medical-900/60 animate-fade-in">
          <Loader2 className="h-3.5 w-3.5 animate-spin" />
          <span>{getStepText()}</span>
        </div>
      )}

      {/* Input Box */}
      <form
        onSubmit={handleSubmit}
        className="relative flex items-end gap-2 rounded-2xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 p-2 shadow-lg shadow-slate-950/5 focus-within:border-medical-500 focus-within:ring-2 focus-within:ring-medical-500/20 transition-all"
      >
        <textarea
          ref={textareaRef}
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder={t.inputPlaceholder}
          rows={1}
          disabled={isLoading}
          className="w-full resize-none bg-transparent px-3 py-1.5 text-xs md:text-sm text-slate-900 dark:text-slate-100 placeholder-slate-400 focus:outline-none max-h-36 min-h-[38px] leading-relaxed"
        />

        <Button
          type="submit"
          disabled={!input.trim() || isLoading}
          size="icon"
          variant="primary"
          aria-label="Send clinical query"
          className="shrink-0 h-9 w-9 rounded-xl"
        >
          {isLoading ? (
            <Loader2 className="h-4 w-4 animate-spin" />
          ) : (
            <Send className="h-4 w-4 rtl:rotate-180" />
          )}
        </Button>
      </form>
    </div>
  );
};
