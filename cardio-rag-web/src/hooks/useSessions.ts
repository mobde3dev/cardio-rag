"use client";

import { useState, useEffect, useCallback } from "react";
import { ChatSession, ChatMessage } from "@/types/chat";
import { storageService } from "@/services/storageService";

export function useSessions() {
  const [sessions, setSessions] = useState<ChatSession[]>([]);
  const [activeSessionId, setActiveSessionId] = useState<string>("");
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    const saved = storageService.getSessions();
    if (saved.length > 0) {
      setSessions(saved);
      setActiveSessionId(saved[0].id);
    } else {
      const initialSession: ChatSession = {
        id: "session_" + Date.now(),
        title: "محادثة سريرية جديدة",
        createdAt: Date.now(),
        updatedAt: Date.now(),
        messages: [],
      };
      setSessions([initialSession]);
      setActiveSessionId(initialSession.id);
      storageService.saveSessions([initialSession]);
    }
    setMounted(true);
  }, []);

  const createNewSession = useCallback((title: string = "محادثة سريرية جديدة") => {
    const newSession: ChatSession = {
      id: "session_" + Date.now(),
      title,
      createdAt: Date.now(),
      updatedAt: Date.now(),
      messages: [],
    };
    setSessions((prev) => {
      const updated = [newSession, ...prev];
      storageService.saveSessions(updated);
      return updated;
    });
    setActiveSessionId(newSession.id);
    return newSession;
  }, []);

  const deleteSession = useCallback(
    (id: string) => {
      setSessions((prev) => {
        const filtered = prev.filter((s) => s.id !== id);
        storageService.saveSessions(filtered);
        if (activeSessionId === id && filtered.length > 0) {
          setActiveSessionId(filtered[0].id);
        } else if (filtered.length === 0) {
          const fresh: ChatSession = {
            id: "session_" + Date.now(),
            title: "محادثة سريرية جديدة",
            createdAt: Date.now(),
            updatedAt: Date.now(),
            messages: [],
          };
          storageService.saveSessions([fresh]);
          setActiveSessionId(fresh.id);
          return [fresh];
        }
        return filtered;
      });
    },
    [activeSessionId]
  );

  const updateSessionMessages = useCallback(
    (sessionId: string, messages: ChatMessage[]) => {
      setSessions((prev) => {
        const updated = prev.map((s) => {
          if (s.id === sessionId) {
            const firstUserMsg = messages.find((m) => m.role === "user");
            const newTitle =
              firstUserMsg?.content.slice(0, 38) + (firstUserMsg && firstUserMsg.content.length > 38 ? "..." : "") ||
              s.title;
            return {
              ...s,
              title: s.title === "محادثة سريرية جديدة" && firstUserMsg ? newTitle : s.title,
              messages,
              updatedAt: Date.now(),
            };
          }
          return s;
        });
        storageService.saveSessions(updated);
        return updated;
      });
    },
    []
  );

  const activeSession = sessions.find((s) => s.id === activeSessionId) || sessions[0];

  return {
    sessions,
    activeSession,
    activeSessionId,
    setActiveSessionId,
    createNewSession,
    deleteSession,
    updateSessionMessages,
    mounted,
  };
}
