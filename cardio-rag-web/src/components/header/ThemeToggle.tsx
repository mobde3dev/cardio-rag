"use client";

import React from "react";
import { Sun, Moon } from "lucide-react";
import { Button } from "@/components/ui/Button";

interface ThemeToggleProps {
  isDark: boolean;
  onToggle: () => void;
}

export const ThemeToggle: React.FC<ThemeToggleProps> = ({ isDark, onToggle }) => {
  return (
    <Button
      variant="outline"
      size="icon"
      onClick={onToggle}
      aria-label="Toggle dark/light theme"
      className="border-slate-200 dark:border-slate-800 text-slate-600 dark:text-slate-300"
    >
      {isDark ? (
        <Sun className="h-4 w-4 text-amber-400 transition-transform duration-300 hover:rotate-45" />
      ) : (
        <Moon className="h-4 w-4 text-slate-700 transition-transform duration-300 hover:-rotate-12" />
      )}
    </Button>
  );
};
