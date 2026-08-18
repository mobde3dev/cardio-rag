import React from "react";

interface MessageContentProps {
  content: string;
}

export const MessageContent: React.FC<MessageContentProps> = ({ content }) => {
  // Process markdown elements simply & robustly
  const renderFormattedText = (text: string) => {
    const lines = text.split("\n");
    return lines.map((line, idx) => {
      // Markdown Table Row
      if (line.trim().startsWith("|") && line.trim().endsWith("|")) {
        const cells = line.split("|").filter((c) => c.trim() !== "");
        if (line.includes("---")) {
          return null; // separator
        }
        return (
          <div
            key={idx}
            className="grid grid-flow-col auto-cols-fr gap-2 py-1 px-2 border-b border-slate-100 dark:border-slate-800 text-xs text-slate-700 dark:text-slate-300"
          >
            {cells.map((cell, cIdx) => (
              <span key={cIdx} className="break-words font-medium">
                {cell.trim()}
              </span>
            ))}
          </div>
        );
      }

      // Bold Header or Bullet
      if (line.startsWith("### ") || line.startsWith("## ")) {
        return (
          <h4
            key={idx}
            className="text-sm font-bold text-slate-900 dark:text-slate-100 mt-3 mb-1 text-medical-700 dark:text-medical-300"
          >
            {line.replace(/^#+\s*/, "")}
          </h4>
        );
      }

      if (line.startsWith("**") && line.endsWith("**")) {
        return (
          <h5
            key={idx}
            className="text-xs font-bold text-slate-900 dark:text-slate-100 mt-2 mb-1"
          >
            {line.replace(/\*\*/g, "")}
          </h5>
        );
      }

      if (line.trim().startsWith("- ") || line.trim().startsWith("• ")) {
        return (
          <li
            key={idx}
            className="text-xs text-slate-700 dark:text-slate-300 leading-relaxed ml-4 rtl:mr-4 rtl:ml-0 list-disc my-0.5"
          >
            {line.replace(/^[-•]\s*/, "")}
          </li>
        );
      }

      if (/^\d+\.\s/.test(line.trim())) {
        return (
          <li
            key={idx}
            className="text-xs text-slate-700 dark:text-slate-300 leading-relaxed ml-4 rtl:mr-4 rtl:ml-0 list-decimal my-0.5"
          >
            {line.replace(/^\d+\.\s*/, "")}
          </li>
        );
      }

      if (line.trim() === "") {
        return <div key={idx} className="h-1.5" />;
      }

      return (
        <p
          key={idx}
          className="text-xs text-slate-700 dark:text-slate-300 leading-relaxed my-1 font-normal"
        >
          {line}
        </p>
      );
    });
  };

  return <div className="space-y-0.5">{renderFormattedText(content)}</div>;
};
