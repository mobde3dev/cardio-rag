"use client";

import React, { useEffect } from "react";
import { X, HeartPulse } from "lucide-react";
import { SessionList } from "./SessionList";
import { PromptLibrary } from "./PromptLibrary";
import { GuidelineStatus } from "./GuidelineStatus";
import { ChatSession } from "@/types/chat";
import { Language, getTranslation } from "@/i18n";
import { clsx } from "clsx";

interface ChatSidebarProps {
  isOpen: boolean;
  onClose: () => void;
  sessions: ChatSession[];
  activeSessionId: string;
  onSelectSession: (id: string) => void;
  onDeleteSession: (id: string) => void;
  onNewSession: () => void;
  onSelectPrompt: (promptText: string) => void;
  language: Language;
}

export const ChatSidebar: React.FC<ChatSidebarProps> = ({
  isOpen,
  onClose,
  sessions,
  activeSessionId,
  onSelectSession,
  onDeleteSession,
  onNewSession,
  onSelectPrompt,
  language,
}) => {
  const t = getTranslation(language);

  // Close sidebar on ESC key
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape" && isOpen) onClose();
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [isOpen, onClose]);

  return (
    <>
      {/* Mobile Backdrop */}
      {isOpen && (
        <div
          className="fixed inset-0 z-40 bg-slate-950/65 backdrop-blur-xs lg:hidden animate-fade-in"
          onClick={onClose}
          aria-hidden="true"
        />
      )}

      {/* Sidebar Container */}
      <aside
        className={clsx(
          "inset-y-0 start-0 z-40 w-[84vw] max-w-[320px] sm:w-80 lg:w-72 xl:w-80 shrink-0 flex-col justify-between border-e border-slate-200/80 dark:border-slate-800/80 bg-white/95 dark:bg-slate-925/95 backdrop-blur-xl p-3.5 sm:p-4 transition-transform duration-300 ease-in-out h-dvh overflow-y-auto overscroll-contain safe-bottom",
          "lg:static lg:flex lg:translate-x-0 lg:shadow-none",
          isOpen
            ? "fixed translate-x-0 flex shadow-2xl"
            : "fixed max-lg:-translate-x-full max-lg:rtl:translate-x-full hidden lg:flex"
        )}
        style={{ transform: undefined }}
      >
        {/* Top Header & Content */}
        <div className="space-y-3 sm:space-y-4">
          <div className="flex items-center justify-between lg:hidden pb-2.5 border-b border-slate-100 dark:border-slate-800">
            <div className="flex items-center gap-2">
              <div className="flex h-7 w-7 items-center justify-center rounded-lg bg-gradient-to-tr from-cardio-600 to-medical-500 text-white shadow-xs">
                <HeartPulse className="h-4 w-4" />
              </div>
              <span className="text-sm font-bold text-slate-900 dark:text-slate-100">
                {t.appTitle}
              </span>
            </div>
            <button
              onClick={onClose}
              aria-label="Close sidebar"
              className="rounded-xl p-2 text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 hover:bg-slate-100 dark:hover:bg-slate-800 min-h-[38px] min-w-[38px] flex items-center justify-center"
            >
              <X className="h-5 w-5" />
            </button>
          </div>

          {/* Session List */}
          <SessionList
            sessions={sessions}
            activeSessionId={activeSessionId}
            onSelectSession={(id) => {
              onSelectSession(id);
              onClose();
            }}
            onDeleteSession={onDeleteSession}
            onNewSession={onNewSession}
            language={language}
          />

          {/* Prompt Library */}
          <div className="pt-2 border-t border-slate-100 dark:border-slate-800">
            <PromptLibrary
              onSelectPrompt={(text) => {
                onSelectPrompt(text);
                onClose();
              }}
              language={language}
            />
          </div>
        </div>

        {/* Bottom Guideline Status */}
        <div className="pt-3 sm:pt-4 border-t border-slate-100 dark:border-slate-800 mt-4">
          <GuidelineStatus language={language} />
        </div>
      </aside>
    </>
  );
};
