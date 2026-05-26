import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Copilot — Offline Enterprise AI",
  description: "Air-gapped AI assistant platform with local LLM inference, RAG, and agentic workflows.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className="dark">
      <body className="noise-bg">
        {children}
      </body>
    </html>
  );
}
