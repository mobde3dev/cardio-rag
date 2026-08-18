"use client";

import React from "react";
import { X, ShieldCheck } from "lucide-react";
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

  return (
    <>
      {/* Mobile Backdrop */}
      {isOpen && (
        <div
          className="fixed inset-0 z-40 bg-slate-950/60 backdrop-blur-xs lg:hidden"
          onClick={onClose}
        />
      )}

      {/* Sidebar Container */}
      <aside
        className={clsx(
          "fixed top-0 bottom-0 z-40 w-80 flex-col justify-between border-r border-slate-200/80 dark:border-slate-800/80 bg-white/90 dark:bg-slate-925/95 backdrop-blur-lg p-4 transition-transform duration-300 lg:static lg:flex lg:translate-x-0",
          isOpen ? "translate-x-0 flex" : "-translate-x-full lg:translate-x-0"
        )}
      >
        {/* Top Header */}
        <div className="space-y-4">
          <div className="flex items-center justify-between lg:hidden pb-2 border-b border-slate-100 dark:border-slate-800">
            <span className="text-sm font-bold text-slate-900 dark:text-slate-100">
              {t.appTitle}
            </span>
            <button
              onClick={onClose}
              className="rounded-lg p-1.5 text-slate-400 hover:text-slate-600 dark:hover:text-slate-200"
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
        <div className="pt-4 border-t border-slate-100 dark:border-slate-800">
          <GuidelineStatus language={language} />
        </div>
      </aside>
    </>
  );
};
