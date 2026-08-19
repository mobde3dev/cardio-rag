"use client";

import React from "react";

interface MessageContentProps {
  content: string;
}

export const MessageContent: React.FC<MessageContentProps> = ({ content }) => {
  // Format inline bold/italic/code strings and HTML line breaks (<br>, <br/>)
  const formatInline = (text: string) => {
    // Split by <br>, bold (**text**), code (`text`), or italic (*text*)
    const parts = text.split(/(<br\s*\/?>|\*\*.*?\*\*|`.*?`|\*.*?\*)/gi);
    return parts.map((part, pIdx) => {
      if (!part) return null;

      // Handle <br> / <br/> tags
      if (/<br\s*\/?>/i.test(part)) {
        return <br key={pIdx} className="my-0.5" />;
      }

      // Handle bold text (**text**)
      if (part.startsWith("**") && part.endsWith("**") && part.length >= 4) {
        return (
          <strong
            key={pIdx}
            className="font-bold text-slate-900 dark:text-slate-100"
          >
            {part.slice(2, -2)}
          </strong>
        );
      }

      // Handle inline code (`text`)
      if (part.startsWith("`") && part.endsWith("`") && part.length >= 2) {
        return (
          <code
            key={pIdx}
            dir="ltr"
            className="px-1.5 py-0.5 rounded-md bg-slate-100 dark:bg-slate-800/90 text-teal-700 dark:text-teal-300 font-mono text-[12px] border border-slate-200/60 dark:border-slate-700/60 inline-block font-medium"
          >
            {part.slice(1, -1)}
          </code>
        );
      }

      // Handle single-asterisk italic (*text*)
      if (part.startsWith("*") && part.endsWith("*") && part.length >= 2 && !part.startsWith("**")) {
        return (
          <span
            key={pIdx}
            className="text-slate-600 dark:text-slate-300 font-medium"
          >
            {part.slice(1, -1)}
          </span>
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
      const bodyRows = rows
        .slice(1)
        .filter((r) => !r.every((c) => c.includes("---") || c === ""));

      elements.push(
        <div
          key={`table-${key}`}
          className="my-3.5 overflow-hidden rounded-xl border border-slate-200/90 dark:border-slate-800 bg-white/70 dark:bg-slate-900/60 shadow-xs"
        >
          <div className="overflow-x-auto">
            <table className="w-full text-start border-collapse text-xs sm:text-[13.5px]">
              <thead>
                <tr className="bg-slate-100/90 dark:bg-slate-800/90 border-b border-slate-200 dark:border-slate-700/80">
                  {headerRow.map((cell, cIdx) => (
                    <th
                      key={cIdx}
                      dir="auto"
                      className="px-3.5 py-2.5 text-start font-semibold text-slate-900 dark:text-slate-100 tracking-tight"
                    >
                      {formatInline(cell)}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-200/70 dark:divide-slate-800/80">
                {bodyRows.map((row, rIdx) => (
                  <tr
                    key={rIdx}
                    className="hover:bg-slate-50/80 dark:hover:bg-slate-800/40 transition-colors"
                  >
                    {row.map((cell, cIdx) => (
                      <td
                        key={cIdx}
                        dir="auto"
                        className="px-3.5 py-2.5 text-start text-slate-700 dark:text-slate-300 leading-relaxed align-top"
                      >
                        {formatInline(cell)}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      );
      tableBuffer = [];
    };

    lines.forEach((line, idx) => {
      const trimmed = line.trim();

      // Horizontal rules
      if (trimmed === "---" || trimmed === "***" || trimmed === "___") {
        if (tableBuffer.length > 0) flushTable(idx);
        elements.push(
          <hr
            key={`hr-${idx}`}
            className="my-3.5 border-slate-200/80 dark:border-slate-800"
          />
        );
        return;
      }

      // Table line detection
      if (trimmed.startsWith("|") && trimmed.endsWith("|")) {
        tableBuffer.push(trimmed);
        return;
      } else if (tableBuffer.length > 0) {
        flushTable(idx);
      }

      // Headers (H3 / H2 / H4)
      if (line.startsWith("### ") || line.startsWith("## ")) {
        elements.push(
          <h4
            key={idx}
            dir="auto"
            className="text-sm sm:text-[15px] font-bold text-teal-700 dark:text-teal-300 mt-4 mb-2 tracking-tight flex items-center gap-1.5"
          >
            {line.replace(/^#+\s*/, "")}
          </h4>
        );
        return;
      }

      // Standalone bold line acting as a subsection title
      if (
        trimmed.startsWith("**") &&
        trimmed.endsWith("**") &&
        !trimmed.slice(2, -2).includes("**")
      ) {
        elements.push(
          <h5
            key={idx}
            dir="auto"
            className="text-xs sm:text-sm font-bold text-slate-900 dark:text-slate-100 mt-3 mb-1.5"
          >
            {trimmed.replace(/\*\*/g, "")}
          </h5>
        );
        return;
      }

      // Asterisk note / disclaimer line (e.g. *This info is...* or *المعلومات المتاحة...*)
      if (
        trimmed.startsWith("*") &&
        trimmed.endsWith("*") &&
        trimmed.length > 2 &&
        !trimmed.startsWith("**")
      ) {
        const cleanText = trimmed.slice(1, -1).trim();
        elements.push(
          <p
            key={idx}
            dir="auto"
            className="text-xs sm:text-[13px] text-slate-500 dark:text-slate-400 font-medium my-2 leading-relaxed bg-slate-50 dark:bg-slate-800/40 px-3 py-2 rounded-xl border border-slate-200/60 dark:border-slate-800"
          >
            {formatInline(cleanText)}
          </p>
        );
        return;
      }

      // Unordered list
      if (trimmed.startsWith("- ") || trimmed.startsWith("• ")) {
        elements.push(
          <li
            key={idx}
            dir="auto"
            className="text-[13.5px] sm:text-[14.5px] text-slate-700 dark:text-slate-200 leading-relaxed ms-5 list-disc my-1.5"
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
            dir="auto"
            className="text-[13.5px] sm:text-[14.5px] text-slate-700 dark:text-slate-200 leading-relaxed ms-5 list-decimal my-1.5"
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
          dir="auto"
          className="text-[13.5px] sm:text-[14.5px] text-slate-800 dark:text-slate-200 leading-relaxed my-1.5 font-normal"
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

  return (
    <div dir="auto" className="space-y-1 text-start">
      {renderFormattedElements(content)}
    </div>
  );
};
