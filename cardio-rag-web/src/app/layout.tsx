import type { Metadata, Viewport } from "next";
import "./globals.css";
import logo from "./assets/logo.png";

export const metadata: Metadata = {
  title: "CardioRAG",
  description:
    "Evidence-based cardiology guidelines RAG assistant powered by Groq, NICE NG136, WHO 2021, and NICE NG238.",
  icons: {
    icon: logo.src,
  },
};

export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
  maximumScale: 5,
  viewportFit: "cover",
  themeColor: [
    { media: "(prefers-color-scheme: light)", color: "#faf5ff" },
    { media: "(prefers-color-scheme: dark)", color: "#070b14" },
  ],
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