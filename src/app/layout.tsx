import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "CardioRAG — Clinical Cardiology AI Decision Support",
  description:
    "Evidence-based cardiology guidelines RAG assistant powered by Groq, NICE NG136, WHO 2021, and NICE NG238.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="ar" dir="rtl" className="dark h-full">
      <body className="h-full bg-slate-50 dark:bg-slate-950 text-slate-900 dark:text-slate-100 transition-colors duration-200">
        {children}
      </body>
    </html>
  );
}
