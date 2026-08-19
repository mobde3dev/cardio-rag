"use client";

import React, { useState } from "react";
import { Search, Plus } from "lucide-react";
import { ChatSession } from "@/types/chat";
import { SessionItem } from "./SessionItem";
import { Button } from "@/components/ui/Button";
import { Language, getTranslation } from "@/i18n";

interface SessionListProps {
  sessions: ChatSession[];
  activeSessionId: string;
  onSelectSession: (id: string) => void;
  onDeleteSession: (id: string) => void;
  onNewSession: () => void;
  language: Language;
}

export const SessionList: React.FC<SessionListProps> = ({
  sessions,
  activeSessionId,
  onSelectSession,
  onDeleteSession,
  onNewSession,
  language,
}) => {
  const [searchTerm, setSearchTerm] = useState("");
  const t = getTranslation(language);

  const filteredSessions = sessions.filter((s) =>
    s.title.toLowerCase().includes(searchTerm.toLowerCase())
  );

  return (
    <div className="flex flex-col space-y-3">
      {/* New Session Button */}
      <Button
        variant="primary"
        size="md"
        onClick={onNewSession}
        className="w-full justify-center shadow-sm text-xs font-semibold"
      >
        <Plus className="h-4 w-4" />
        <span>{t.newChat}</span>
      </Button>

      {/* Search Sessions */}
      <div className="relative">
        <Search className="absolute left-3 top-2.5 h-3.5 w-3.5 text-slate-400 rtl:right-3 rtl:left-auto" />
        <input
          type="text"
          value={searchTerm}
          onChange={(e) => setSearchTerm(e.target.value)}
          placeholder={t.searchHistory}
          className="w-full rounded-xl border border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-950/60 py-1.5 pl-8 pr-3 rtl:pr-8 rtl:pl-3 text-xs text-slate-900 dark:text-slate-100 placeholder-slate-400 focus:border-medical-500 focus:outline-none"
        />
      </div>

      {/* List */}
      <div className="space-y-1 overflow-y-auto max-h-56 pr-1">
        {filteredSessions.length > 0 ? (
          filteredSessions.map((session) => (
            <SessionItem
              key={session.id}
              session={session}
              isActive={session.id === activeSessionId}
              onSelect={onSelectSession}
              onDelete={onDeleteSession}
            />
          ))
        ) : (
          <p className="text-center py-4 text-xs text-slate-400">
            {t.noHistory}
          </p>
        )}
      </div>
    </div>
  );
};
