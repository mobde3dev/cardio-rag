"use client";

import React, { useEffect, useMemo, useRef, useState } from "react";
import { ArrowUp, Sparkles, Loader2 } from "lucide-react";
import { Button } from "@/components/ui/Button";
import { Language, getTranslation } from "@/i18n";
import { SAMPLE_QUESTIONS } from "@/config/sampleQuestions";

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

  /**
   * Dynamic suggestions
   *
   * The search is based on the current language:
   * - Arabic -> questionAr
   * - English -> questionEn
   *
   * We use includes() so the searched text can appear
   * anywhere inside the question.
   */
  const suggestions = useMemo(() => {
    const searchTerm = input.trim().toLowerCase();

    // Don't show suggestions when:
    // - input is empty
    // - the AI is currently processing a request
    if (!searchTerm || isLoading) {
      return [];
    }

    return SAMPLE_QUESTIONS.filter((question) => {
      const questionText =
        language === "ar" ? question.questionAr : question.questionEn;

      return questionText.toLowerCase().includes(searchTerm);
    });
  }, [input, language, isLoading]);

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

  /**
   * Put the selected suggestion into the textarea.
   * It does NOT send the question automatically.
   */
  const handleSuggestionClick = (questionText: string) => {
    setInput(questionText);

    // Focus textarea after selecting a suggestion
    requestAnimationFrame(() => {
      textareaRef.current?.focus();
    });
  };

  const getStepText = () => {
    if (currentStep === "translatingQuery") return t.translatingQuery;
    if (currentStep === "searchingGuidelines") return t.searchingGuidelines;
    if (currentStep === "generatingAnswer") return t.generatingAnswer;

    return t.generatingAnswer;
  };

  return (
    <div className="w-full max-w-4xl mx-auto px-3 sm:px-4 pb-3 sm:pb-4 pt-1 safe-bottom">
      {/* Loading Step Progress Indicator */}
      {isLoading && (
        <div className="flex items-center gap-2 text-xs font-medium text-medical-600 dark:text-medical-400 mb-2 px-3 py-1.5 rounded-xl bg-medical-50/90 dark:bg-medical-950/60 border border-medical-200 dark:border-medical-900/60 animate-fade-in shadow-xs">
          <Loader2 className="h-3.5 w-3.5 animate-spin shrink-0" />
          <span className="truncate">{getStepText()}</span>
        </div>
      )}

      {/* Dynamic Suggestions */}
      {!isLoading && input.trim() && suggestions.length > 0 && (
        <div className="mb-2 animate-fade-in">
          {/* Suggestions Header */}
          <div className="flex items-center gap-1.5 px-2 mb-1.5">
            <Sparkles className="h-3.5 w-3.5 text-medical-600 dark:text-medical-400" />

            <span className="text-[11px] font-semibold text-slate-500 dark:text-slate-400">
              {language === "ar"
                ? "أسئلة مقترحة"
                : "Suggested questions"}
            </span>
          </div>

          {/* Horizontal Suggestions */}
          <div
            className="
              flex gap-2
              overflow-x-auto
              overscroll-x-contain
              pb-1
              px-0.5
              no-scrollbar
              touch-pan-x
              snap-x
            "
          >
            {suggestions.map((question) => {
              const questionText =
                language === "ar"
                  ? question.questionAr
                  : question.questionEn;

              return (
                <button
                  key={question.id}
                  type="button"
                  onClick={() => handleSuggestionClick(questionText)}
                  className="
                    group
                    shrink-0
                    w-[270px]
                    sm:w-[300px]
                    snap-start
                    text-start
                    rounded-xl
                    border
                    border-slate-200/90
                    dark:border-slate-800
                    bg-white/95
                    dark:bg-slate-900/95
                    backdrop-blur-md
                    px-3
                    py-2.5
                    shadow-sm
                    hover:border-medical-300
                    dark:hover:border-medical-800
                    hover:bg-medical-50/70
                    dark:hover:bg-medical-950/30
                    hover:shadow-md
                    transition-all
                    duration-200
                  "
                >
                  <div className="flex items-start gap-2">
                    <div
                      className="
                        mt-0.5
                        flex
                        h-6
                        w-6
                        shrink-0
                        items-center
                        justify-center
                        rounded-lg
                        bg-medical-50
                        dark:bg-medical-950/50
                        text-medical-600
                        dark:text-medical-400
                        group-hover:bg-medical-100
                        dark:group-hover:bg-medical-900/60
                        transition-colors
                      "
                    >
                      <Sparkles className="h-3.5 w-3.5" />
                    </div>

                    <p
                      className="
                        line-clamp-3
                        text-[11px]
                        sm:text-xs
                        font-medium
                        leading-relaxed
                        text-slate-700
                        dark:text-slate-300
                        group-hover:text-medical-800
                        dark:group-hover:text-medical-200
                      "
                    >
                      {questionText}
                    </p>
                  </div>
                </button>
              );
            })}
          </div>
        </div>
      )}

      {/* Input Box */}
      <form
        onSubmit={handleSubmit}
        className="
          relative
          flex
          items-end
          gap-2
          rounded-2xl
          border
          border-slate-200/90
          dark:border-slate-800
          bg-white/95
          dark:bg-slate-900/95
          backdrop-blur-md
          p-1.5
          sm:p-2
          shadow-lg
          shadow-slate-950/5
          focus-within:border-medical-500
          focus-within:ring-2
          focus-within:ring-medical-500/20
          transition-all
        "
      >
        <textarea
          ref={textareaRef}
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder={t.inputPlaceholder}
          rows={1}
          disabled={isLoading}
          className="
            w-full
            resize-none
            bg-transparent
            px-2.5
            sm:px-3
            py-1.5
            text-base
            sm:text-sm
            text-slate-900
            dark:text-slate-100
            placeholder-slate-400
            focus:outline-none
            max-h-36
            min-h-[40px]
            leading-relaxed
          "
        />

        <Button
          type="submit"
          disabled={!input.trim() || isLoading}
          size="icon"
          variant="primary"
          aria-label="Send clinical query"
          className="
            shrink-0
            h-10
            w-10
            sm:h-9
            sm:w-9
            rounded-xl
            flex
            items-center
            justify-center
            min-h-[40px]
            min-w-[40px]
            sm:min-h-[36px]
            sm:min-w-[36px]
          "
        >
          {isLoading ? (
            <Loader2 className="h-4 w-4 animate-spin" />
          ) : (
            <ArrowUp className="h-4.5 w-4.5" />
          )}
        </Button>
      </form>
    </div>
  );
};