import React from "react";
import { clsx } from "clsx";

interface ScoreMeterProps {
  score: number; // 0.0 to 1.0
  label?: string;
  showPercent?: boolean;
}

export const ScoreMeter: React.FC<ScoreMeterProps> = ({
  score,
  label,
  showPercent = true,
}) => {
  const percentage = Math.round(score * 100);

  const getColorClass = () => {
    if (percentage >= 85) return "bg-emerald-500";
    if (percentage >= 70) return "bg-medical-500";
    if (percentage >= 50) return "bg-amber-500";
    return "bg-cardio-500";
  };

  return (
    <div className="w-full space-y-1">
      {(label || showPercent) && (
        <div className="flex justify-between items-center text-[11px] font-semibold text-slate-600 dark:text-slate-300">
          {label && <span>{label}</span>}
          {showPercent && (
            <span className="font-mono text-medical-600 dark:text-medical-400">
              {percentage}%
            </span>
          )}
        </div>
      )}
      <div className="h-1.5 w-full bg-slate-100 dark:bg-slate-800 rounded-full overflow-hidden">
        <div
          className={clsx("h-full transition-all duration-500", getColorClass())}
          style={{ width: `${percentage}%` }}
        />
      </div>
    </div>
  );
};
