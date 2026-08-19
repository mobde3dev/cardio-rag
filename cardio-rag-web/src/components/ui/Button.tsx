import React from "react";
import { clsx } from "clsx";
import { twMerge } from "tailwind-merge";

interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: "primary" | "secondary" | "outline" | "ghost" | "danger";
  size?: "sm" | "md" | "lg" | "icon";
  isLoading?: boolean;
}

export const Button: React.FC<ButtonProps> = ({
  children,
  className,
  variant = "primary",
  size = "md",
  isLoading,
  disabled,
  ...props
}) => {
  const baseStyles =
    "inline-flex items-center justify-center font-medium transition-all duration-200 focus:outline-none focus:ring-2 focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed select-none rounded-xl active:scale-[0.98]";

  const variants = {
    primary:
      "bg-gradient-to-r from-medical-600 to-medical-700 hover:from-medical-500 hover:to-medical-600 text-white shadow-md shadow-medical-900/10 focus:ring-medical-500",
    secondary:
      "bg-slate-100 dark:bg-slate-800 hover:bg-slate-200 dark:hover:bg-slate-700 text-slate-900 dark:text-slate-100 focus:ring-slate-400",
    outline:
      "border border-slate-200 dark:border-slate-700 hover:bg-slate-50 dark:hover:bg-slate-800/60 text-slate-700 dark:text-slate-200 focus:ring-medical-500",
    ghost:
      "hover:bg-slate-100 dark:hover:bg-slate-800 text-slate-700 dark:text-slate-300 focus:ring-slate-400",
    danger:
      "bg-cardio-600 hover:bg-cardio-500 text-white shadow-sm focus:ring-cardio-500",
  };

  const sizes = {
    sm: "text-xs px-2.5 py-1.5 gap-1.5 min-h-[36px]",
    md: "text-xs sm:text-sm px-3.5 sm:px-4 py-2 gap-2 min-h-[40px]",
    lg: "text-sm sm:text-base px-4 sm:px-5 py-2.5 gap-2.5 min-h-[44px]",
    icon: "p-2 rounded-xl h-9 w-9 sm:h-9.5 sm:w-9.5 min-h-[36px] min-w-[36px]",
  };

  return (
    <button
      className={twMerge(clsx(baseStyles, variants[variant], sizes[size], className))}
      disabled={disabled || isLoading}
      {...props}
    >
      {isLoading ? (
        <span className="inline-block h-3.5 w-3.5 animate-spin rounded-full border-2 border-current border-t-transparent shrink-0" />
      ) : null}
      {children}
    </button>
  );
};
