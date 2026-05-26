"use client";

import { useEffect, useState } from "react";
import { Sidebar } from "@/components/layout/Sidebar";
import { ChatPanel } from "@/components/chat/ChatPanel";
import { DocumentPanel } from "@/components/documents/DocumentPanel";
import { useAppStore } from "@/store";
import { api } from "@/lib/api";
import { LoginScreen } from "@/components/layout/LoginScreen";

export default function Home() {
  const { user, token, setAuth, setModels, setDocuments, setConversations, setSelectedModel } = useAppStore();
  const [docPanelOpen, setDocPanelOpen] = useState(false);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const savedToken = typeof window !== "undefined" ? localStorage.getItem("token") : null;
    if (savedToken) {
      api
        .getMe()
        .then((u) => setAuth(u, savedToken))
        .catch(() => localStorage.removeItem("token"))
        .finally(() => setLoading(false));
    } else {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (!token) return;
    api.getModels().then((r) => {
      setModels(r.models);
      setSelectedModel(r.default);
    }).catch(() => {});
    api.getDocuments().then((r) => setDocuments(r.documents)).catch(() => {});
    api.getConversations().then((r) => setConversations(r)).catch(() => {});
  }, [token]);

  if (loading) {
    return (
      <div className="h-screen flex items-center justify-center">
        <div className="w-8 h-8 border-2 border-accent border-t-transparent rounded-full animate-spin" />
      </div>
    );
  }

  if (!user) return <LoginScreen />;

  return (
    <div className="h-screen flex overflow-hidden">
      <Sidebar onOpenDocs={() => setDocPanelOpen(true)} />

      <main className="flex-1 flex flex-col min-w-0">
        <ChatPanel />
      </main>

      {docPanelOpen && (
        <DocumentPanel onClose={() => setDocPanelOpen(false)} />
      )}
    </div>
  );
}
