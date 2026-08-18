"use client";

import React, { useState } from "react";
import { HeartPulse, Settings, Award, Menu, ShieldCheck } from "lucide-react";
import { LanguageToggle } from "./LanguageToggle";
import { ThemeToggle } from "./ThemeToggle";
import { ModelSelector } from "./ModelSelector";
import { SettingsModal } from "./SettingsModal";
import { AuthModal } from "@/components/auth/AuthModal";
import { Button } from "@/components/ui/Button";
import { Badge } from "@/components/ui/Badge";
import { Language, getTranslation } from "@/i18n";
import { AppSettings } from "@/types/settings";
import { User, LogOut } from "lucide-react";
import { supabaseService, UserProfile } from "@/services/supabaseService";

interface HeaderProps {
  language: Language;
  onToggleLanguage: () => void;
  isDark: boolean;
  onToggleTheme: () => void;
  selectedModel: string;
  onChangeModel: (modelId: string) => void;
  settings: AppSettings;
  onSaveSettings: (settings: AppSettings) => void;
  onOpenRubric: () => void;
  onToggleSidebar: () => void;
}

export const Header: React.FC<HeaderProps> = ({
  language,
  onToggleLanguage,
  isDark,
  onToggleTheme,
  selectedModel,
  onChangeModel,
  settings,
  onSaveSettings,
  onOpenRubric,
  onToggleSidebar,
}) => {
  const [isSettingsOpen, setIsSettingsOpen] = useState(false);
  const [isAuthOpen, setIsAuthOpen] = useState(false);
  const [currentUser, setCurrentUser] = useState<UserProfile | null>(() =>
    supabaseService.getCurrentUser()
  );
  const t = getTranslation(language);

  const handleLogout = () => {
    supabaseService.logout();
    setCurrentUser(null);
  };

  return (
    <header className="sticky top-0 z-40 flex h-16 w-full items-center justify-between border-b border-slate-200/80 dark:border-slate-800/80 bg-white/80 dark:bg-slate-900/80 backdrop-blur-md px-4 sm:px-6">
      {/* Brand & Title */}
      <div className="flex items-center gap-3">
        <button
          onClick={onToggleSidebar}
          aria-label="Toggle navigation drawer"
          className="rounded-xl p-2 text-slate-500 hover:text-slate-700 dark:text-slate-400 dark:hover:text-slate-200 hover:bg-slate-100 dark:hover:bg-slate-800 lg:hidden"
        >
          <Menu className="h-5 w-5" />
        </button>

        <div className="flex items-center gap-2.5">
          <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-gradient-to-tr from-cardio-600 to-medical-500 text-white shadow-sm">
            <HeartPulse className="h-5 w-5 animate-pulse-slow" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-base font-bold tracking-tight text-slate-900 dark:text-slate-100">
                Cardio<span className="text-medical-600 dark:text-medical-400">RAG</span>
              </h1>
              <Badge variant="medical" size="sm">
                NICE & WHO
              </Badge>
            </div>
            <p className="hidden sm:block text-[11px] font-medium text-slate-500 dark:text-slate-400">
              {t.appSubtitle}
            </p>
          </div>
        </div>
      </div>

      {/* Center / Model Selection (Desktop) */}
      <div className="hidden md:flex items-center gap-2">
        <ModelSelector
          selectedModel={selectedModel}
          onChangeModel={onChangeModel}
          language={language}
        />
      </div>

      {/* Right Controls */}
      <div className="flex items-center gap-1.5 sm:gap-2">
        {/* Rubric Button */}
        <Button
          variant="outline"
          size="sm"
          onClick={onOpenRubric}
          className="hidden sm:inline-flex border-amber-200 dark:border-amber-900/60 bg-amber-50/50 dark:bg-amber-950/20 text-amber-800 dark:text-amber-300 font-semibold"
        >
          <Award className="h-3.5 w-3.5 text-amber-600 dark:text-amber-400" />
          <span>{t.rubricScore}</span>
        </Button>

        {/* User Auth Button */}
        {currentUser ? (
          <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-xl bg-medical-50/60 dark:bg-medical-950/40 border border-medical-200 dark:border-medical-900 text-xs font-semibold text-medical-800 dark:text-medical-200">
            <User className="h-3.5 w-3.5 text-medical-600 dark:text-medical-400" />
            <span className="truncate max-w-[80px] hidden sm:inline">
              {currentUser.fullName}
            </span>
            <button
              onClick={handleLogout}
              title={language === "ar" ? "تسجيل الخروج" : "Sign Out"}
              className="text-slate-400 hover:text-cardio-600 ml-1 rtl:mr-1"
            >
              <LogOut className="h-3 w-3" />
            </button>
          </div>
        ) : (
          <Button
            variant="outline"
            size="sm"
            onClick={() => setIsAuthOpen(true)}
            className="text-xs font-semibold border-medical-200 dark:border-medical-900 text-medical-700 dark:text-medical-300"
          >
            <User className="h-3.5 w-3.5" />
            <span className="hidden sm:inline">
              {language === "ar" ? "دخول" : "Sign In"}
            </span>
          </Button>
        )}

        <LanguageToggle
          currentLanguage={language}
          onToggle={onToggleLanguage}
        />

        <ThemeToggle isDark={isDark} onToggle={onToggleTheme} />

        <Button
          variant="outline"
          size="icon"
          onClick={() => setIsSettingsOpen(true)}
          aria-label="Settings"
          className="border-slate-200 dark:border-slate-800 text-slate-600 dark:text-slate-300"
        >
          <Settings className="h-4 w-4" />
        </Button>
      </div>

      {/* Settings Modal */}
      <SettingsModal
        isOpen={isSettingsOpen}
        onClose={() => setIsSettingsOpen(false)}
        settings={settings}
        onSaveSettings={onSaveSettings}
        language={language}
      />

      {/* Auth Modal */}
      <AuthModal
        isOpen={isAuthOpen}
        onClose={() => setIsAuthOpen(false)}
        onSuccess={(user) => setCurrentUser(user)}
        language={language}
      />
    </header>
  );
};
