"use client";

import React from "react";
import { MessageSquare, Trash2 } from "lucide-react";
import { ChatSession } from "@/types/chat";
import { clsx } from "clsx";

interface SessionItemProps {
  session: ChatSession;
  isActive: boolean;
  onSelect: (id: string) => void;
  onDelete: (id: string) => void;
}

export const SessionItem: React.FC<SessionItemProps> = ({
  session,
  isActive,
  onSelect,
  onDelete,
}) => {
  return (
    <div
      onClick={() => onSelect(session.id)}
      role="button"
      tabIndex={0}
      className={clsx(
        "group relative flex items-center justify-between rounded-xl px-3 py-2.5 text-xs font-medium transition-all duration-150 cursor-pointer select-none",
        isActive
          ? "bg-medical-50 dark:bg-medical-950/50 text-medical-800 dark:text-medical-200 border border-medical-200 dark:border-medical-800/80 shadow-xs"
          : "text-slate-600 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-800/60 hover:text-slate-900 dark:hover:text-slate-200"
      )}
    >
      <div className="flex items-center gap-2.5 overflow-hidden">
        <MessageSquare
          className={clsx(
            "h-4 w-4 shrink-0",
            isActive
              ? "text-medical-600 dark:text-medical-400"
              : "text-slate-400 group-hover:text-slate-600"
          )}
        />
        <span className="truncate">{session.title}</span>
      </div>

      <button
        onClick={(e) => {
          e.stopPropagation();
          onDelete(session.id);
        }}
        aria-label="Delete session"
        className="opacity-0 group-hover:opacity-100 rounded-lg p-1 text-slate-400 hover:text-cardio-600 hover:bg-cardio-50 dark:hover:bg-cardio-950/40 transition-all"
      >
        <Trash2 className="h-3.5 w-3.5" />
      </button>
    </div>
  );
};
