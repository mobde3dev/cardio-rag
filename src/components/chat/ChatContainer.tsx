"use client";

import React, { useRef, useEffect } from "react";
import { ChatMessage } from "@/types/chat";
import { MessageBubble } from "./MessageBubble";
import { WelcomeHero } from "./WelcomeHero";
import { Language } from "@/i18n";

interface ChatContainerProps {
  messages: ChatMessage[];
  onSelectPrompt: (promptText: string) => void;
  onOpenInspector: (message: ChatMessage) => void;
  language: Language;
  modelName?: string;
}

export const ChatContainer: React.FC<ChatContainerProps> = ({
  messages,
  onSelectPrompt,
  onOpenInspector,
  language,
  modelName,
}) => {
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  return (
    <div className="flex-1 overflow-y-auto px-2.5 sm:px-4 md:px-6 py-3 sm:py-6 space-y-4 sm:space-y-5 overscroll-contain">
      {messages.length === 0 ? (
        <WelcomeHero onSelectPrompt={onSelectPrompt} language={language} />
      ) : (
        messages.map((message) => (
          <MessageBubble
            key={message.id}
            message={message}
            language={language}
            onOpenInspector={onOpenInspector}
            modelName={modelName}
          />
        ))
      )}
      <div ref={bottomRef} className="h-2" />
    </div>
  );
};
