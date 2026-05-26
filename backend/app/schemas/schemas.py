"""
Pydantic schemas for API request/response validation.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, EmailStr, Field

from app.core.security import Role


# ── Auth ──────────────────────────────────────────────────────

class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=6)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    role: Role


class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)
    full_name: str = Field(min_length=1, max_length=256)
    role: Role = Role.VIEWER


class UserResponse(BaseModel):
    id: uuid.UUID
    email: str
    full_name: str
    role: Role
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


# ── Chat ──────────────────────────────────────────────────────

class ChatMessage(BaseModel):
    role: str = Field(pattern="^(user|assistant|system)$")
    content: str = Field(min_length=1)


class ChatRequest(BaseModel):
    message: str = Field(min_length=1)
    conversation_id: uuid.UUID | None = None
    model: str | None = None
    language: str = "en"
    use_rag: bool = False
    document_ids: list[uuid.UUID] = Field(default_factory=list)
    temperature: float = Field(default=0.7, ge=0.0, le=2.0)
    max_tokens: int = Field(default=4096, ge=1, le=32768)
    stream: bool = True


class SourceCitation(BaseModel):
    document_id: str
    filename: str
    chunk_text: str
    page: int | None = None
    relevance_score: float


class ChatResponse(BaseModel):
    conversation_id: uuid.UUID
    message_id: uuid.UUID
    content: str
    model: str
    sources: list[SourceCitation] = Field(default_factory=list)
    confidence: float | None = None
    tokens_used: int | None = None
    latency_ms: int | None = None


class StreamChunk(BaseModel):
    conversation_id: str
    delta: str
    done: bool = False
    sources: list[SourceCitation] | None = None
    confidence: float | None = None


# ── Documents ─────────────────────────────────────────────────

class DocumentResponse(BaseModel):
    id: uuid.UUID
    filename: str
    content_type: str
    file_size: int
    status: str
    chunk_count: int
    language: str
    created_at: datetime

    model_config = {"from_attributes": True}


class DocumentListResponse(BaseModel):
    documents: list[DocumentResponse]
    total: int


# ── Agents ────────────────────────────────────────────────────

class AgentExecuteRequest(BaseModel):
    workflow: str = Field(description="Workflow name: research, summarize, verify, translate, report")
    input_text: str = Field(min_length=1)
    document_ids: list[uuid.UUID] = Field(default_factory=list)
    target_language: str | None = None
    model: str | None = None
    config: dict[str, Any] = Field(default_factory=dict)


class AgentStepResult(BaseModel):
    agent: str
    action: str
    output: str
    duration_ms: int


class AgentExecuteResponse(BaseModel):
    workflow: str
    steps: list[AgentStepResult]
    final_output: str
    total_duration_ms: int


# ── Voice ─────────────────────────────────────────────────────

class TranscriptionResponse(BaseModel):
    text: str
    language: str
    duration_seconds: float


# ── Models ────────────────────────────────────────────────────

class ModelInfo(BaseModel):
    name: str
    size: str | None = None
    quantization: str | None = None
    family: str | None = None
    parameter_size: str | None = None
    is_available: bool = True


class ModelListResponse(BaseModel):
    models: list[ModelInfo]
    default: str


# ── Health ────────────────────────────────────────────────────

class ServiceHealth(BaseModel):
    service: str
    status: str  # healthy | degraded | unhealthy
    latency_ms: float | None = None
    details: str | None = None


class HealthResponse(BaseModel):
    status: str
    version: str
    services: list[ServiceHealth]
