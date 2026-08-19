"use client";

import React from "react";

interface MessageContentProps {
  content: string;
}

export const MessageContent: React.FC<MessageContentProps> = ({ content }) => {
  // Format inline bold/code strings
  const formatInline = (text: string) => {
    // Split by bold (**text**)
    const parts = text.split(/(\*\*.*?\*\*|`.*?`)/g);
    return parts.map((part, pIdx) => {
      if (part.startsWith("**") && part.endsWith("**")) {
        return (
          <strong
            key={pIdx}
            className="font-bold text-slate-900 dark:text-slate-100"
          >
            {part.slice(2, -2)}
          </strong>
        );
      }
      if (part.startsWith("`") && part.endsWith("`")) {
        return (
          <code
            key={pIdx}
            className="px-1.5 py-0.5 rounded-md bg-slate-100 dark:bg-slate-800 text-medical-700 dark:text-medical-300 font-mono text-[11px]"
          >
            {part.slice(1, -1)}
          </code>
        );
      }
      return part;
    });
  };

  // Group table blocks and format markdown
  const renderFormattedElements = (text: string) => {
    const lines = text.split("\n");
    const elements: React.ReactNode[] = [];
    let tableBuffer: string[] = [];

    const flushTable = (key: number) => {
      if (tableBuffer.length === 0) return;
      const rows = tableBuffer.map((line) =>
        line
          .split("|")
          .filter((_, idx, arr) => idx > 0 && idx < arr.length - 1)
          .map((c) => c.trim())
      );

      const headerRow = rows[0] || [];
      const bodyRows = rows.slice(1).filter((r) => !r.every((c) => c.includes("---") || c === ""));

      elements.push(
        <div key={`table-${key}`} className="clinical-table-wrapper my-2">
          <table className="clinical-table">
            <thead>
              <tr>
                {headerRow.map((cell, cIdx) => (
                  <th key={cIdx}>{formatInline(cell)}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {bodyRows.map((row, rIdx) => (
                <tr key={rIdx}>
                  {row.map((cell, cIdx) => (
                    <td key={cIdx}>{formatInline(cell)}</td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      );
      tableBuffer = [];
    };

    lines.forEach((line, idx) => {
      const trimmed = line.trim();

      // Table line detection
      if (trimmed.startsWith("|") && trimmed.endsWith("|")) {
        tableBuffer.push(trimmed);
        return;
      } else if (tableBuffer.length > 0) {
        flushTable(idx);
      }

      // Headers
      if (line.startsWith("### ") || line.startsWith("## ")) {
        elements.push(
          <h4
            key={idx}
            className="text-xs sm:text-sm font-bold text-medical-700 dark:text-medical-300 mt-3 mb-1 tracking-tight"
          >
            {line.replace(/^#+\s*/, "")}
          </h4>
        );
        return;
      }

      // Standalone bold line
      if (trimmed.startsWith("**") && trimmed.endsWith("**") && !trimmed.slice(2, -2).includes("**")) {
        elements.push(
          <h5
            key={idx}
            className="text-xs sm:text-sm font-bold text-slate-900 dark:text-slate-100 mt-2 mb-1"
          >
            {trimmed.replace(/\*\*/g, "")}
          </h5>
        );
        return;
      }

      // Unordered list
      if (trimmed.startsWith("- ") || trimmed.startsWith("• ")) {
        elements.push(
          <li
            key={idx}
            className="text-xs sm:text-[13px] text-slate-700 dark:text-slate-300 leading-relaxed ms-4 list-disc my-1"
          >
            {formatInline(trimmed.replace(/^[-•]\s*/, ""))}
          </li>
        );
        return;
      }

      // Ordered list
      if (/^\d+\.\s/.test(trimmed)) {
        elements.push(
          <li
            key={idx}
            className="text-xs sm:text-[13px] text-slate-700 dark:text-slate-300 leading-relaxed ms-4 list-decimal my-1"
          >
            {formatInline(trimmed.replace(/^\d+\.\s*/, ""))}
          </li>
        );
        return;
      }

      // Empty line
      if (trimmed === "") {
        elements.push(<div key={idx} className="h-1.5" />);
        return;
      }

      // Regular paragraph
      elements.push(
        <p
          key={idx}
          className="text-xs sm:text-[13px] text-slate-700 dark:text-slate-300 leading-relaxed my-1 font-normal"
        >
          {formatInline(line)}
        </p>
      );
    });

    if (tableBuffer.length > 0) {
      flushTable(lines.length);
    }

    return elements;
  };

  return <div className="space-y-0.5">{renderFormattedElements(content)}</div>;
};
