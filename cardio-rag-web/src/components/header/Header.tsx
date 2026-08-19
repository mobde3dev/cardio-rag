"use client";

import React, { useState } from "react";
import { HeartPulse, Settings, Menu } from "lucide-react";
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
import logo from "../../app/assets/logo.png";

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
    <header className="sticky top-0 z-40 flex h-14 sm:h-16 w-full items-center justify-between border-b border-slate-200/80 dark:border-slate-800/80 bg-white/85 dark:bg-slate-900/85 backdrop-blur-md px-3 sm:px-6 safe-top transition-colors">
      {/* Brand & Title */}
      <div className="flex items-center gap-2 sm:gap-3 min-w-0">
        <button
  onClick={onToggleSidebar}
  aria-label="Toggle navigation drawer"
  title="Toggle sidebar"
  className="rounded-xl p-2 text-slate-500 hover:text-slate-700 dark:text-slate-400 dark:hover:text-slate-200 hover:bg-slate-100 dark:hover:bg-slate-800 min-h-[38px] min-w-[38px] flex items-center justify-center shrink-0 transition-colors"
>
  <Menu className="h-5 w-5" />
</button>

        <div className="flex items-center gap-2 sm:gap-2.5 min-w-0">
<img
  src={logo.src}
  alt="CardioRAG Logo"
  className="h-9 w-9 sm:h-10 sm:w-10 object-contain"
/>          <div className="min-w-0">
            <div className="flex items-center gap-1.5 sm:gap-2">
             <h1 className="text-sm sm:text-base font-bold tracking-tight truncate">
  <span className="text-[#078A9A]">Cardio</span>
  <span className="text-[#E31837]">RAG</span>
</h1>
              <Badge variant="medical" size="sm" className="hidden xs:inline-flex text-[10px] sm:text-[11px] py-0 px-1.5">
                NICE & WHO
              </Badge>
            </div>
            <p className="hidden md:block text-[11px] font-medium text-slate-500 dark:text-slate-400 truncate">
              {t.appSubtitle}
            </p>
          </div>
        </div>
      </div>

      {/* Right Controls */}
      <div className="flex items-center gap-1 sm:gap-2 shrink-0">
        {/* User Auth Button */}
        {currentUser ? (
          <div className="flex items-center gap-1 sm:gap-1.5 px-2 sm:px-2.5 py-1 rounded-xl bg-medical-50/60 dark:bg-medical-950/40 border border-medical-200 dark:border-medical-900 text-xs font-semibold text-medical-800 dark:text-medical-200">
            <User className="h-3.5 w-3.5 text-medical-600 dark:text-medical-400 shrink-0" />
            <span className="truncate max-w-[70px] sm:max-w-[100px] hidden sm:inline text-xs">
              {currentUser.fullName}
            </span>
            <button
              onClick={handleLogout}
              title={language === "ar" ? "تسجيل الخروج" : "Sign Out"}
              aria-label="Sign out"
              className="text-slate-400 hover:text-cardio-600 ml-1 rtl:mr-1 p-0.5"
            >
              <LogOut className="h-3 w-3" />
            </button>
          </div>
        ) : (
          <Button
            variant="outline"
            size="sm"
            onClick={() => setIsAuthOpen(true)}
            aria-label={language === "ar" ? "تسجيل الدخول" : "Sign in"}
            className="text-xs font-semibold border-medical-200 dark:border-medical-900 text-medical-700 dark:text-medical-300 px-2 sm:px-3"
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
