"use client";

import { useState, useRef, useCallback } from "react";
import {
  Upload, FileText, Trash2, X, Loader2,
  CheckCircle, AlertCircle, File, Image,
} from "lucide-react";
import { useAppStore } from "@/store";
import { apiClient } from "@/lib/api";
import type { DocumentMeta } from "@/types";

interface DocumentPanelProps {
  onClose: () => void;
}

export function DocumentPanel({ onClose }: DocumentPanelProps) {
  const { documents, setDocuments, token } = useAppStore();
  const [uploading, setUploading] = useState(false);
  const [dragOver, setDragOver] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const uploadFile = useCallback(
    async (file: File) => {
      setUploading(true);
      try {
        const doc = await apiClient.uploadDocument(file, token!);
        setDocuments([doc, ...documents]);
      } catch {
        /* handle silently */
      } finally {
        setUploading(false);
      }
    },
    [documents, token, setDocuments],
  );

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      setDragOver(false);
      const file = e.dataTransfer.files[0];
      if (file) uploadFile(file);
    },
    [uploadFile],
  );

  const handleDelete = async (id: string) => {
    try {
      await apiClient.deleteDocument(id, token!);
      setDocuments(documents.filter((d) => d.id !== id));
    } catch {
      /* handle silently */
    }
  };

  const fileIcon = (filename: string) => {
    const ext = filename.split(".").pop()?.toLowerCase();
    if (["png", "jpg", "jpeg", "webp", "gif"].includes(ext || ""))
      return <Image className="w-4 h-4 text-purple-400" />;
    if (ext === "pdf")
      return <FileText className="w-4 h-4 text-red-400" />;
    return <File className="w-4 h-4 text-blue-400" />;
  };

  const formatSize = (bytes: number) => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  };

  return (
    <div className="w-80 h-screen flex flex-col bg-surface-raised border-l border-border shrink-0">
      {/* Header */}
      <div className="h-14 flex items-center justify-between px-4 border-b border-border">
        <h2 className="text-sm font-medium text-text-primary">Documents</h2>
        <button
          onClick={onClose}
          className="p-1 rounded-md hover:bg-surface-overlay text-text-muted transition-colors"
        >
          <X className="w-4 h-4" />
        </button>
      </div>

      {/* Upload Zone */}
      <div className="p-3">
        <div
          onDrop={handleDrop}
          onDragOver={(e) => {
            e.preventDefault();
            setDragOver(true);
          }}
          onDragLeave={() => setDragOver(false)}
          onClick={() => fileInputRef.current?.click()}
          className={`border-2 border-dashed rounded-xl p-6 text-center cursor-pointer transition-all ${
            dragOver
              ? "border-accent bg-accent/5"
              : "border-border hover:border-accent/30 hover:bg-accent/5"
          }`}
        >
          {uploading ? (
            <Loader2 className="w-6 h-6 text-accent mx-auto animate-spin" />
          ) : (
            <Upload className="w-6 h-6 text-text-muted mx-auto" />
          )}
          <p className="text-xs text-text-muted mt-2">
            {uploading ? "Processing…" : "Drop files or click to upload"}
          </p>
          <p className="text-[10px] text-text-muted/60 mt-1">
            PDF, DOCX, TXT, PNG, JPG
          </p>
        </div>
        <input
          ref={fileInputRef}
          type="file"
          accept=".pdf,.docx,.txt,.png,.jpg,.jpeg,.webp"
          className="hidden"
          onChange={(e) => {
            const file = e.target.files?.[0];
            if (file) uploadFile(file);
            e.target.value = "";
          }}
        />
      </div>

      {/* Document List */}
      <div className="flex-1 overflow-y-auto px-3 pb-3 space-y-1">
        {documents.length === 0 ? (
          <div className="text-center py-8">
            <FileText className="w-8 h-8 text-text-muted/30 mx-auto" />
            <p className="text-xs text-text-muted mt-2">No documents yet</p>
          </div>
        ) : (
          documents.map((doc) => (
            <div
              key={doc.id}
              className="group flex items-center gap-2.5 px-3 py-2.5 rounded-lg hover:bg-surface-overlay transition-colors"
            >
              <div className="shrink-0">{fileIcon(doc.filename)}</div>
              <div className="flex-1 min-w-0">
                <p className="text-xs text-text-primary truncate">
                  {doc.filename}
                </p>
                <div className="flex items-center gap-2 mt-0.5">
                  <span className="text-[10px] text-text-muted">
                    {formatSize(doc.file_size)}
                  </span>
                  <span className="text-[10px] text-text-muted">·</span>
                  <span className="text-[10px] text-text-muted">
                    {doc.chunk_count} chunks
                  </span>
                  {doc.status === "ready" && (
                    <CheckCircle className="w-2.5 h-2.5 text-green-400" />
                  )}
                  {doc.status === "error" && (
                    <AlertCircle className="w-2.5 h-2.5 text-red-400" />
                  )}
                </div>
              </div>
              <button
                onClick={() => handleDelete(doc.id)}
                className="p-1 rounded text-text-muted opacity-0 group-hover:opacity-100 hover:text-red-400 transition-all"
              >
                <Trash2 className="w-3.5 h-3.5" />
              </button>
            </div>
          ))
        )}
      </div>

      {/* Stats */}
      <div className="border-t border-border px-4 py-2.5">
        <div className="flex justify-between text-[10px] text-text-muted">
          <span>{documents.length} documents</span>
          <span>
            {documents.reduce((acc, d) => acc + d.chunk_count, 0)} total chunks
          </span>
        </div>
      </div>
    </div>
  );
}
