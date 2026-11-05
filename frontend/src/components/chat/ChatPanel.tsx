"use client";

import { useState, useRef, useEffect, useCallback } from "react";
import {
  Send, Mic, MicOff, Paperclip, Database, Loader2,
  Bot, User, Copy, Check, ThumbsUp, ThumbsDown,
  FileText, AlertTriangle, Sparkles,
} from "lucide-react";
import { useAppStore } from "@/store";
import { apiClient } from "@/lib/api";
import type { Message, Citation } from "@/types";

export function ChatPanel() {
  const {
    messages, setMessages, selectedModel, activeConversationId,
    token, language,
  } = useAppStore();

  const [input, setInput] = useState("");
  const [isStreaming, setIsStreaming] = useState(false);
  const [useRag, setUseRag] = useState(true);
  const [isRecording, setIsRecording] = useState(false);
  const [copiedId, setCopiedId] = useState<string | null>(null);

  const bottomRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  useEffect(() => {
    inputRef.current?.focus();
  }, [activeConversationId]);

  const handleSend = useCallback(async () => {
    const text = input.trim();
    if (!text || isStreaming) return;

    const userMsg: Message = {
      id: crypto.randomUUID(),
      role: "user",
      content: text,
      timestamp: new Date().toISOString(),
    };

    setMessages([...messages, userMsg]);
    setInput("");
    setIsStreaming(true);

    const assistantMsg: Message = {
      id: crypto.randomUUID(),
      role: "assistant",
      content: "",
      timestamp: new Date().toISOString(),
    };

    setMessages([...messages, userMsg, assistantMsg]);

    try {
      const stream = apiClient.chatStream(
        text,
        selectedModel,
        useRag,
        activeConversationId || undefined,
        language,
        token!,
      );

      let fullContent = "";
      const citations: Citation[] = [];
      let confidence: number | undefined;

      for await (const chunk of stream) {
        if (chunk.type === "token") {
          fullContent += chunk.content;
          setMessages([
            ...messages,
            userMsg,
            { ...assistantMsg, content: fullContent },
          ]);
        } else if (chunk.type === "citations") {
          citations.push(...(chunk.citations || []));
        } else if (chunk.type === "metadata") {
          confidence = chunk.confidence;
        }
      }

      setMessages([
        ...messages,
        userMsg,
        {
          ...assistantMsg,
          content: fullContent,
          citations: citations.length > 0 ? citations : undefined,
          confidence,
        },
      ]);
    } catch (err) {
      setMessages([
        ...messages,
        userMsg,
        {
          ...assistantMsg,
          content: "An error occurred while generating the response. Please try again.",
        },
      ]);
    } finally {
      setIsStreaming(false);
    }
  }, [input, isStreaming, messages, selectedModel, useRag, activeConversationId, language, token, setMessages]);

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const toggleRecording = async () => {
    if (isRecording) {
      mediaRecorderRef.current?.stop();
      setIsRecording(false);
      return;
    }

    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const recorder = new MediaRecorder(stream);
      const chunks: Blob[] = [];

      recorder.ondataavailable = (e) => chunks.push(e.data);
      recorder.onstop = async () => {
        stream.getTracks().forEach((t) => t.stop());
        const blob = new Blob(chunks, { type: "audio/webm" });
        try {
          const text = await apiClient.transcribe(blob, language, token!);
          setInput((prev) => prev + text);
        } catch {
          /* silent fail */
        }
      };

      mediaRecorderRef.current = recorder;
      recorder.start();
      setIsRecording(true);
    } catch {
      /* mic permission denied */
    }
  };

  const copyToClipboard = (id: string, text: string) => {
    navigator.clipboard.writeText(text);
    setCopiedId(id);
    setTimeout(() => setCopiedId(null), 2000);
  };

  return (
    <div className="flex-1 flex flex-col min-w-0 h-screen">
      {/* Messages Area */}
      <div className="flex-1 overflow-y-auto">
        {messages.length === 0 ? (
          <EmptyState />
        ) : (
          <div className="max-w-3xl mx-auto px-4 py-6 space-y-6">
            {messages.map((msg) => (
              <MessageBubble
                key={msg.id}
                message={msg}
                isStreaming={isStreaming && msg === messages[messages.length - 1]}
                onCopy={copyToClipboard}
                copied={copiedId === msg.id}
              />
            ))}
            <div ref={bottomRef} />
          </div>
        )}
      </div>

      {/* Input Area */}
      <div className="border-t border-border bg-surface-raised/50 backdrop-blur-sm px-4 py-3">
        <div className="max-w-3xl mx-auto">
          <div className="flex items-end gap-2 bg-surface border border-border rounded-2xl px-4 py-3 focus-within:border-accent/40 transition-colors">
            <textarea
              ref={inputRef}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Ask anything…"
              rows={1}
              className="flex-1 bg-transparent text-sm text-text-primary placeholder:text-text-muted outline-none resize-none max-h-32"
              style={{ minHeight: "20px" }}
              disabled={isStreaming}
            />

            <div className="flex items-center gap-1 shrink-0">
              {/* RAG Toggle */}
              <button
                onClick={() => setUseRag(!useRag)}
                className={`p-1.5 rounded-lg transition-colors ${
                  useRag
                    ? "text-accent bg-accent/10"
                    : "text-text-muted hover:text-text-secondary"
                }`}
                title={useRag ? "RAG enabled" : "RAG disabled"}
              >
                <Database className="w-4 h-4" />
              </button>

              {/* Voice */}
              <button
                onClick={toggleRecording}
                className={`p-1.5 rounded-lg transition-colors ${
                  isRecording
                    ? "text-red-400 bg-red-400/10 animate-pulse"
                    : "text-text-muted hover:text-text-secondary"
                }`}
              >
                {isRecording ? <MicOff className="w-4 h-4" /> : <Mic className="w-4 h-4" />}
              </button>

              {/* Send */}
              <button
                onClick={handleSend}
                disabled={!input.trim() || isStreaming}
                className="p-1.5 rounded-lg bg-accent text-white disabled:opacity-30 disabled:cursor-not-allowed hover:bg-accent/90 transition-colors"
              >
                {isStreaming ? (
                  <Loader2 className="w-4 h-4 animate-spin" />
                ) : (
                  <Send className="w-4 h-4" />
                )}
              </button>
            </div>
          </div>

          <p className="text-[10px] text-text-muted text-center mt-2">
            Running locally · Model: {selectedModel || "llama3:8b"} · {useRag ? "RAG on" : "RAG off"}
          </p>
        </div>
      </div>
    </div>
  );
}

/* ── Message Bubble ───────────────────────────────────────────── */

function MessageBubble({
  message,
  isStreaming,
  onCopy,
  copied,
}: {
  message: Message;
  isStreaming: boolean;
  onCopy: (id: string, text: string) => void;
  copied: boolean;
}) {
  const isUser = message.role === "user";

  return (
    <div className={`flex gap-3 ${isUser ? "justify-end" : ""}`}>
      {!isUser && (
        <div className="w-7 h-7 rounded-lg bg-accent/15 flex items-center justify-center shrink-0 mt-0.5">
          <Bot className="w-4 h-4 text-accent" />
        </div>
      )}

      <div className={`max-w-[85%] ${isUser ? "order-first" : ""}`}>
        <div
          className={`rounded-2xl px-4 py-2.5 text-sm leading-relaxed ${
            isUser
              ? "bg-accent/10 text-text-primary ml-auto rounded-br-md"
              : "bg-surface-raised text-text-primary rounded-bl-md"
          }`}
        >
          <div className="whitespace-pre-wrap break-words">
            {message.content}
            {isStreaming && (
              <span className="inline-block w-1.5 h-4 bg-accent/70 ml-0.5 animate-pulse rounded-sm" />
            )}
          </div>
        </div>

        {/* Citations */}
        {message.citations && message.citations.length > 0 && (
          <div className="flex flex-wrap gap-1.5 mt-2">
            {message.citations.map((c, i) => (
              <span
                key={i}
                className="inline-flex items-center gap-1 text-[10px] text-text-muted bg-surface-overlay px-2 py-0.5 rounded-full"
              >
                <FileText className="w-2.5 h-2.5" />
                {c.filename}
              </span>
            ))}
          </div>
        )}

        {/* Confidence */}
        {message.confidence != null && (
          <div className="flex items-center gap-1.5 mt-1.5">
            {message.confidence < 0.5 ? (
              <AlertTriangle className="w-3 h-3 text-yellow-500" />
            ) : (
              <Sparkles className="w-3 h-3 text-accent" />
            )}
            <span className="text-[10px] text-text-muted">
              Confidence: {Math.round(message.confidence * 100)}%
            </span>
          </div>
        )}

        {/* Actions */}
        {!isUser && message.content && !isStreaming && (
          <div className="flex items-center gap-1 mt-1.5">
            <button
              onClick={() => onCopy(message.id || "", message.content)}
              className="p-1 rounded text-text-muted hover:text-text-secondary transition-colors"
            >
              {copied ? <Check className="w-3 h-3 text-green-400" /> : <Copy className="w-3 h-3" />}
            </button>
            <button className="p-1 rounded text-text-muted hover:text-text-secondary transition-colors">
              <ThumbsUp className="w-3 h-3" />
            </button>
            <button className="p-1 rounded text-text-muted hover:text-text-secondary transition-colors">
              <ThumbsDown className="w-3 h-3" />
            </button>
          </div>
        )}
      </div>

      {isUser && (
        <div className="w-7 h-7 rounded-lg bg-surface-overlay flex items-center justify-center shrink-0 mt-0.5">
          <User className="w-4 h-4 text-text-muted" />
        </div>
      )}
    </div>
  );
}

/* ── Empty State ──────────────────────────────────────────────── */

function EmptyState() {
  return (
    <div className="h-full flex items-center justify-center">
      <div className="text-center space-y-4 max-w-md px-4">
        <div className="w-14 h-14 rounded-2xl bg-accent/10 flex items-center justify-center mx-auto">
          <Sparkles className="w-7 h-7 text-accent" />
        </div>
        <h2 className="text-lg font-medium text-text-primary">
          Offline Enterprise Copilot
        </h2>
        <p className="text-sm text-text-muted leading-relaxed">
          Your private AI assistant running entirely on-premises.
          Ask questions, analyze documents, run workflows — all without
          any data leaving your network.
        </p>
        <div className="grid grid-cols-2 gap-2 pt-2">
          {[
            "Summarize my uploaded documents",
            "Run a research workflow",
            "Translate this to Arabic",
            "Analyze quarterly metrics",
          ].map((prompt) => (
            <button
              key={prompt}
              className="text-left text-xs text-text-secondary bg-surface-raised border border-border rounded-xl px-3 py-2.5 hover:border-accent/30 hover:bg-accent/5 transition-all"
            >
              {prompt}
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}
