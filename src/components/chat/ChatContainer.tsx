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
    <div className="flex-1 overflow-y-auto px-3 sm:px-4 md:px-6 py-4 sm:py-6 overscroll-contain">
      <div className="w-full max-w-4xl mx-auto space-y-5 sm:space-y-6">
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
    </div>
  );
};
