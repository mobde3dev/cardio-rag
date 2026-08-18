"use client";

import React, { useEffect, useState } from "react";
import { X, HeartPulse, ChevronDown, BookOpen } from "lucide-react";
import { SessionList } from "./SessionList";
import { PromptLibrary } from "./PromptLibrary";
import { GuidelineStatus } from "./GuidelineStatus";
import { ChatSession } from "@/types/chat";
import { Language, getTranslation } from "@/i18n";
import { clsx } from "clsx";
import { Badge } from "@/components/ui/Badge";
import logo from "../../app/assets/logo.png";


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

  // Clinical Question Bank dropdown state
  const [isPromptLibraryOpen, setIsPromptLibraryOpen] = useState(false);

  // Close sidebar on ESC key
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape" && isOpen) {
        onClose();
      }
    };

    window.addEventListener("keydown", handleKeyDown);

    return () => {
      window.removeEventListener("keydown", handleKeyDown);
    };
  }, [isOpen, onClose]);

  return (
    <>
      {/* Sidebar Backdrop */}
      {isOpen && (
        <div
          className="fixed inset-0 z-40 bg-slate-950/30 backdrop-blur-[2px] animate-fade-in"
          onClick={onClose}
          aria-hidden="true"
        />
      )}

      {/* Sidebar Container */}
      <aside
        className={clsx(
          // Base layout
          "fixed inset-y-0 start-0 z-50",
          "w-[84vw] max-w-[320px] sm:w-80 lg:w-72 xl:w-80",
          "shrink-0 flex-col justify-between",

          // Background & border
          "border-e border-slate-200/80 dark:border-slate-800/80",
          "bg-white/95 dark:bg-slate-925/95",
          "backdrop-blur-xl",

          // Spacing
          "p-3.5 sm:p-4",

          // Animation
          "transition-transform duration-300 ease-in-out",

          // Height & scrolling
          "h-dvh overflow-y-auto overscroll-contain safe-bottom",

          // Shadow
          "shadow-2xl",

          // Open / Close state
          isOpen
            ? "translate-x-0 flex"
            : "-translate-x-full rtl:translate-x-full flex"
        )}
      >
        {/* Top Header & Content */}
        <div className="space-y-3 sm:space-y-4">
          {/* Sidebar Header */}
          <div className="flex items-center justify-between pb-2.5 border-b border-slate-100 dark:border-slate-800">
     <div className="flex items-center gap-3">
    <img
      src={logo.src}
      alt="CardioRAG Logo"
      className="h-9 w-9 sm:h-10 sm:w-10 object-contain"
    />

  <span className="text-lg sm:text-xl font-bold">
    <span className="text-[#078A9A]">Cardio</span>
    <span className="text-[#E31837]">RAG</span>
  </span>
</div>

            {/* Close Button */}
            <button
              onClick={onClose}
              aria-label="Close sidebar"
              className="rounded-xl p-2 text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 hover:bg-slate-100 dark:hover:bg-slate-800 min-h-[38px] min-w-[38px] flex items-center justify-center transition-colors"
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

          {/* Clinical Question Bank */}
          <div className="pt-2 border-t border-slate-100 dark:border-slate-800">
            {/* Dropdown Header */}
            <button
              type="button"
              onClick={() =>
                setIsPromptLibraryOpen((prev) => !prev)
              }
              aria-expanded={isPromptLibraryOpen}
              className={clsx(
                "w-full flex items-center justify-between gap-3",
                "rounded-xl px-3 py-2.5",
                "text-sm font-semibold",
                "text-slate-700 dark:text-slate-200",
                "hover:bg-slate-50 dark:hover:bg-slate-800/60",
                "transition-colors duration-200"
              )}
            >
              {/* Left Side */}
              <div className="flex items-center gap-7 min-w-0">
                <BookOpen className="h-4 w-4 shrink-0 text-medical-600 dark:text-medical-400" />

                <span className="truncate">
                  {language === "ar"
                    ? "بنك الأسئلة السريرية"
                    : "Clinical Question Bank"}
                </span>

                <Badge
                  variant="medical"
                  size="sm"
                  className="shrink-0 text-[10px]"
                >
                  20 Qs
                </Badge>
              </div>

              {/* Chevron */}
              <ChevronDown
                className={clsx(
                  "h-4 w-4 shrink-0 text-slate-400",
                  "transition-transform duration-200",
                  isPromptLibraryOpen && "rotate-180"
                )}
              />
            </button>

            {/* Dropdown Content */}
            {isPromptLibraryOpen && (
              <div className="mt-2 animate-fade-in">
                <PromptLibrary
                  onSelectPrompt={(text) => {
                    onSelectPrompt(text);
                    onClose();
                  }}
                  language={language}
                />
              </div>
            )}
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