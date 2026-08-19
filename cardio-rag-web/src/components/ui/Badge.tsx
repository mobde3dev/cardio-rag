import React from "react";
import { clsx } from "clsx";
import { twMerge } from "tailwind-merge";

interface BadgeProps extends React.HTMLAttributes<HTMLSpanElement> {
  variant?: "medical" | "cardio" | "neutral" | "warning" | "success" | "outline";
  size?: "sm" | "md";
}

export const Badge: React.FC<BadgeProps> = ({
  children,
  className,
  variant = "medical",
  size = "md",
  ...props
}) => {
  const baseStyles =
    "inline-flex items-center font-medium rounded-full transition-colors select-none";

  const variants = {
    medical:
      "bg-medical-50 dark:bg-medical-950/60 text-medical-700 dark:text-medical-300 border border-medical-200 dark:border-medical-800/80",
    cardio:
      "bg-cardio-50 dark:bg-cardio-950/60 text-cardio-700 dark:text-cardio-300 border border-cardio-200 dark:border-cardio-800/80",
    neutral:
      "bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-300 border border-slate-200 dark:border-slate-700",
    warning:
      "bg-amber-50 dark:bg-amber-950/60 text-amber-800 dark:text-amber-300 border border-amber-200 dark:border-amber-800/80",
    success:
      "bg-emerald-50 dark:bg-emerald-950/60 text-emerald-700 dark:text-emerald-300 border border-emerald-200 dark:border-emerald-800/80",
    outline:
      "bg-transparent text-slate-600 dark:text-slate-400 border border-slate-300 dark:border-slate-700",
  };

  const sizes = {
    sm: "text-[11px] px-2 py-0.5 gap-1",
    md: "text-xs px-2.5 py-1 gap-1.5",
  };

  return (
    <span
      className={twMerge(clsx(baseStyles, variants[variant], sizes[size], className))}
      {...props}
    >
      {children}
    </span>
  );
};
