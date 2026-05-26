"use client";

import {
  MessageSquare, FileText, Workflow, BarChart3,
  Plus, ChevronLeft, ChevronRight, LogOut, Settings,
  Globe, Cpu,
} from "lucide-react";
import { useAppStore } from "@/store";

interface SidebarProps {
  onOpenDocs: () => void;
}

export function Sidebar({ onOpenDocs }: SidebarProps) {
  const {
    sidebarOpen, toggleSidebar, conversations, activeConversationId,
    setActiveConversation, setMessages, selectedModel, setSelectedModel,
    models, user, logout, language, setLanguage,
  } = useAppStore();

  const collapsed = !sidebarOpen;

  return (
    <aside
      className={`${collapsed ? "w-16" : "w-72"} h-screen flex flex-col bg-surface-raised border-r border-border transition-all duration-200 shrink-0`}
    >
      {/* Header */}
      <div className="h-14 flex items-center justify-between px-3 border-b border-border">
        {!collapsed && (
          <div className="flex items-center gap-2.5 min-w-0">
            <div className="w-7 h-7 rounded-lg bg-accent/15 flex items-center justify-center shrink-0">
              <Cpu className="w-4 h-4 text-accent" />
            </div>
            <span className="text-sm font-medium text-text-primary truncate">Copilot</span>
          </div>
        )}
        <button
          onClick={toggleSidebar}
          className="p-1.5 rounded-md hover:bg-surface-overlay text-text-muted transition-colors"
        >
          {collapsed ? <ChevronRight className="w-4 h-4" /> : <ChevronLeft className="w-4 h-4" />}
        </button>
      </div>

      {/* New Chat */}
      <div className="px-2 pt-3 pb-2">
        <button
          onClick={() => { setActiveConversation(null); setMessages([]); }}
          className={`w-full flex items-center gap-2.5 px-3 py-2 rounded-lg border border-border hover:border-accent/30 hover:bg-accent/5 text-text-secondary hover:text-text-primary text-sm transition-all ${collapsed ? "justify-center" : ""}`}
        >
          <Plus className="w-4 h-4 shrink-0" />
          {!collapsed && <span>New Chat</span>}
        </button>
      </div>

      {/* Model Selector */}
      {!collapsed && (
        <div className="px-3 pb-2">
          <select
            value={selectedModel}
            onChange={(e) => setSelectedModel(e.target.value)}
            className="w-full px-2.5 py-1.5 text-xs bg-surface border border-border rounded-md text-text-secondary focus:border-accent outline-none"
          >
            {models.map((m) => (
              <option key={m.name} value={m.name}>{m.name}</option>
            ))}
            {models.length === 0 && <option>llama3:8b</option>}
          </select>
        </div>
      )}

      {/* Conversations */}
      <div className="flex-1 overflow-y-auto px-2 py-1 space-y-0.5">
        {!collapsed && (
          <p className="text-[10px] uppercase tracking-widest text-text-muted px-2 py-1.5">Recent</p>
        )}
        {conversations.map((c) => (
          <button
            key={c.id}
            onClick={() => setActiveConversation(c.id)}
            className={`w-full flex items-center gap-2.5 px-2.5 py-2 rounded-lg text-sm transition-colors truncate ${
              activeConversationId === c.id
                ? "bg-accent/10 text-accent"
                : "text-text-secondary hover:bg-surface-overlay hover:text-text-primary"
            } ${collapsed ? "justify-center" : ""}`}
          >
            <MessageSquare className="w-3.5 h-3.5 shrink-0" />
            {!collapsed && <span className="truncate">{c.title}</span>}
          </button>
        ))}
      </div>

      {/* Bottom Nav */}
      <div className="border-t border-border p-2 space-y-0.5">
        <SidebarButton icon={<FileText className="w-4 h-4" />} label="Documents" onClick={onOpenDocs} collapsed={collapsed} />
        <SidebarButton icon={<Workflow className="w-4 h-4" />} label="Workflows" collapsed={collapsed} />
        <SidebarButton icon={<BarChart3 className="w-4 h-4" />} label="Analytics" collapsed={collapsed} />

        {/* Language Toggle */}
        {!collapsed && (
          <div className="flex items-center gap-2 px-2.5 py-2">
            <Globe className="w-4 h-4 text-text-muted" />
            <select
              value={language}
              onChange={(e) => setLanguage(e.target.value)}
              className="flex-1 text-xs bg-transparent text-text-secondary outline-none"
            >
              <option value="en">English</option>
              <option value="ar">العربية</option>
              <option value="hi">हिन्दी</option>
            </select>
          </div>
        )}

        {/* User */}
        <div className={`flex items-center gap-2.5 px-2.5 py-2 ${collapsed ? "justify-center" : ""}`}>
          <div className="w-6 h-6 rounded-full bg-accent/20 flex items-center justify-center text-[10px] font-medium text-accent shrink-0">
            {user?.full_name?.charAt(0) || "U"}
          </div>
          {!collapsed && (
            <>
              <span className="text-xs text-text-secondary truncate flex-1">{user?.full_name}</span>
              <button onClick={logout} className="p-1 hover:bg-surface-overlay rounded text-text-muted">
                <LogOut className="w-3.5 h-3.5" />
              </button>
            </>
          )}
        </div>
      </div>
    </aside>
  );
}

function SidebarButton({
  icon, label, onClick, collapsed,
}: {
  icon: React.ReactNode; label: string; onClick?: () => void; collapsed: boolean;
}) {
  return (
    <button
      onClick={onClick}
      className={`w-full flex items-center gap-2.5 px-2.5 py-2 rounded-lg text-sm text-text-secondary hover:bg-surface-overlay hover:text-text-primary transition-colors ${collapsed ? "justify-center" : ""}`}
    >
      {icon}
      {!collapsed && <span>{label}</span>}
    </button>
  );
}
