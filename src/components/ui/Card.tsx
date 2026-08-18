import React from "react";
import { clsx } from "clsx";
import { twMerge } from "tailwind-merge";

interface CardProps extends React.HTMLAttributes<HTMLDivElement> {
  hoverable?: boolean;
  active?: boolean;
}

export const Card: React.FC<CardProps> = ({
  children,
  className,
  hoverable,
  active,
  ...props
}) => {
  return (
    <div
      className={twMerge(
        clsx(
          "rounded-2xl border bg-white dark:bg-slate-900 border-slate-200 dark:border-slate-800 p-4 transition-all duration-200 shadow-sm",
          hoverable &&
            "hover:border-medical-500/50 dark:hover:border-medical-500/40 hover:shadow-md hover:shadow-medical-950/5 cursor-pointer active:scale-[0.99]",
          active &&
            "border-medical-500 bg-medical-50/40 dark:bg-medical-950/20 shadow-sm",
          className
        )
      )}
      {...props}
    >
      {children}
    </div>
  );
};
