"use client";

import React, { useState } from "react";
import { Header } from "@/components/header/Header";
import { ChatSidebar } from "@/components/sidebar/ChatSidebar";
import { ChatContainer } from "@/components/chat/ChatContainer";
import { ChatInput } from "@/components/chat/ChatInput";
import { RagInspectorDrawer } from "@/components/rag/RagInspectorDrawer";
import { RubricModal } from "@/components/rag/RubricModal";
import { useLanguage } from "@/hooks/useLanguage";
import { useTheme } from "@/hooks/useTheme";
import { useSessions } from "@/hooks/useSessions";
import { useChat } from "@/hooks/useChat";
import { storageService } from "@/services/storageService";
import { AppSettings } from "@/types/settings";

export default function Home() {
  const { language, isRTL, toggleLanguage, t, mounted: langMounted } = useLanguage();
  const { theme, isDark, toggleTheme, mounted: themeMounted } = useTheme();
  const [settings, setSettings] = useState<AppSettings>(() => storageService.getSettings());
  const [isSidebarOpen, setIsSidebarOpen] = useState(false);
  const [isRubricOpen, setIsRubricOpen] = useState(false);

  const {
    sessions,
    activeSession,
    activeSessionId,
    setActiveSessionId,
    createNewSession,
    deleteSession,
    updateSessionMessages,
    mounted: sessionsMounted,
  } = useSessions();

  const {
    isLoading,
    currentStep,
    sendMessage,
    selectedInspectChunkMessage,
    setSelectedInspectChunkMessage,
  } = useChat({
    activeSessionMessages: activeSession?.messages || [],
    onUpdateMessages: (messages) => updateSessionMessages(activeSessionId, messages),
    settings,
    userLanguage: language,
  });

  const handleSelectPrompt = (promptText: string) => {
    sendMessage(promptText);
  };

  if (!langMounted || !themeMounted || !sessionsMounted) {
    return (
      <div className="flex h-dvh w-full items-center justify-center bg-slate-950 text-slate-400">
        <div className="h-6 w-6 animate-spin rounded-full border-2 border-medical-500 border-t-transparent" />
      </div>
    );
  }

  return (
    <div className="flex h-dvh w-full overflow-hidden bg-slate-50 dark:bg-slate-950 font-sans">
      {/* Sidebar */}
      <ChatSidebar
        isOpen={isSidebarOpen}
        onClose={() => setIsSidebarOpen(false)}
        sessions={sessions}
        activeSessionId={activeSessionId}
        onSelectSession={setActiveSessionId}
        onDeleteSession={deleteSession}
        onNewSession={() => createNewSession(language === "ar" ? "محادثة سريرية جديدة" : "New Clinical Query")}
        onSelectPrompt={handleSelectPrompt}
        language={language}
      />

      {/* Main Chat Workspace */}
      <div className="flex flex-1 flex-col h-full overflow-hidden">
        {/* Top Navigation Header */}
        <Header
          language={language}
          onToggleLanguage={toggleLanguage}
          isDark={isDark}
          onToggleTheme={toggleTheme}
          selectedModel={settings.selectedModel}
          onChangeModel={(modelId) => {
            const updated = { ...settings, selectedModel: modelId };
            setSettings(updated);
            storageService.saveSettings(updated);
          }}
          settings={settings}
          onSaveSettings={setSettings}
          onOpenRubric={() => setIsRubricOpen(true)}
          onToggleSidebar={() => setIsSidebarOpen(!isSidebarOpen)}
        />

        {/* Message Thread Scroll Area */}
        <ChatContainer
          messages={activeSession?.messages || []}
          onSelectPrompt={handleSelectPrompt}
          onOpenInspector={(msg) => setSelectedInspectChunkMessage(msg)}
          language={language}
          modelName={settings.selectedModel}
        />

        {/* Bottom Input Area */}
        <ChatInput
          onSendMessage={sendMessage}
          isLoading={isLoading}
          currentStep={currentStep}
          language={language}
        />
      </div>

      {/* RAG Inspector Drawer (Transparency & Metrics) */}
      <RagInspectorDrawer
        isOpen={!!selectedInspectChunkMessage}
        onClose={() => setSelectedInspectChunkMessage(null)}
        message={selectedInspectChunkMessage}
        language={language}
      />

      {/* Rubric Evaluation Modal (100 Pts Breakdown) */}
      <RubricModal
        isOpen={isRubricOpen}
        onClose={() => setIsRubricOpen(false)}
        language={language}
      />
    </div>
  );
}
