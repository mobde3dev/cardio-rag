"use client";

import React, { useState } from "react";
import { User, Mail, Lock, Sparkles, LogIn, UserCheck } from "lucide-react";
import { Modal } from "@/components/ui/Modal";
import { Button } from "@/components/ui/Button";
import { supabaseService, UserProfile } from "@/services/supabaseService";
import { Language, getTranslation } from "@/i18n";

interface AuthModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSuccess: (user: UserProfile) => void;
  language: Language;
}

export const AuthModal: React.FC<AuthModalProps> = ({
  isOpen,
  onClose,
  onSuccess,
  language,
}) => {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const t = getTranslation(language);

  const handleEmailLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!email) return;
    setIsLoading(true);
    try {
      const user = await supabaseService.loginWithEmail(email, password);
      onSuccess(user);
      onClose();
    } finally {
      setIsLoading(false);
    }
  };

  const handleGuestLogin = async () => {
    setIsLoading(true);
    try {
      const user = await supabaseService.loginAsGuest();
      onSuccess(user);
      onClose();
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title={language === "ar" ? "تسجيل الدخول السريري" : "Clinician Sign In"}
      description={
        language === "ar"
          ? "سجل دخولك لحفظ سجل المحادثات السريرية الخاص بك فقط عبر Supabase RLS."
          : "Sign in to isolate and sync your clinical chat history via Supabase RLS."
      }
      maxWidth="sm"
    >
      <div className="space-y-4">
        <form onSubmit={handleEmailLogin} className="space-y-3">
          <div className="space-y-1">
            <label className="text-xs font-semibold text-slate-700 dark:text-slate-300 flex items-center gap-1.5">
              <Mail className="h-3.5 w-3.5 text-medical-600 dark:text-medical-400" />
              <span>{language === "ar" ? "البريد الإلكتروني" : "Email Address"}</span>
            </label>
            <input
              type="email"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="doctor@hospital.org"
              className="w-full rounded-xl border border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-950 px-3 py-2 text-base sm:text-xs text-slate-900 dark:text-slate-100 focus:border-medical-500 focus:outline-none"
            />
          </div>

          <div className="space-y-1">
            <label className="text-xs font-semibold text-slate-700 dark:text-slate-300 flex items-center gap-1.5">
              <Lock className="h-3.5 w-3.5 text-medical-600 dark:text-medical-400" />
              <span>{language === "ar" ? "كلمة المرور" : "Password"}</span>
            </label>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="••••••••"
              className="w-full rounded-xl border border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-950 px-3 py-2 text-base sm:text-xs text-slate-900 dark:text-slate-100 focus:border-medical-500 focus:outline-none"
            />
          </div>

          <Button
            type="submit"
            variant="primary"
            size="md"
            isLoading={isLoading}
            className="w-full justify-center text-xs sm:text-sm font-semibold min-h-[42px]"
          >
            <LogIn className="h-4 w-4" />
            <span>{language === "ar" ? "دخول فوري" : "Sign In"}</span>
          </Button>
        </form>

        <div className="relative flex items-center justify-center">
          <div className="border-t border-slate-200 dark:border-slate-800 w-full" />
          <span className="bg-white dark:bg-slate-900 px-2 text-[10px] text-slate-400 uppercase font-bold absolute">
            {language === "ar" ? "أو" : "OR"}
          </span>
        </div>

        {/* Quick Guest Demo Login */}
        <Button
          type="button"
          variant="outline"
          size="md"
          onClick={handleGuestLogin}
          isLoading={isLoading}
          className="w-full justify-center text-xs font-semibold border-medical-200 dark:border-medical-900 bg-medical-50/50 dark:bg-medical-950/20 text-medical-700 dark:text-medical-300"
        >
          <UserCheck className="h-4 w-4" />
          <span>{language === "ar" ? "دخول سريع كطبيب زائر (Guest MVP)" : "Quick Guest Access (MVP Demo)"}</span>
        </Button>
      </div>
    </Modal>
  );
};
