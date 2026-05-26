"""
Model management, voice transcription, and health check routes.
"""

from __future__ import annotations

import time

from fastapi import APIRouter, Depends, File, UploadFile

from app.api.deps import get_current_user, require_permission
from app.core.config import get_settings
from app.core.security import TokenPayload
from app.schemas.schemas import (
    HealthResponse,
    ModelListResponse,
    ServiceHealth,
    TranscriptionResponse,
)
from app.services.cache.service import semantic_cache
from app.services.llm.service import llm_service
from app.services.rag.retrieval import retrieval_engine
from app.services.voice.service import voice_service

settings = get_settings()

# ── Models ────────────────────────────────────────────────────

models_router = APIRouter(prefix="/models", tags=["Models"])


@models_router.get("", response_model=ModelListResponse)
async def list_models(user: TokenPayload = Depends(get_current_user)):
    models = await llm_service.list_models()
    return ModelListResponse(models=models, default=settings.default_model)


# ── Voice ─────────────────────────────────────────────────────

voice_router = APIRouter(prefix="/voice", tags=["Voice"])


@voice_router.post("/transcribe", response_model=TranscriptionResponse)
async def transcribe_audio(
    file: UploadFile = File(...),
    user: TokenPayload = Depends(require_permission("voice:use")),
):
    audio_bytes = await file.read()
    return await voice_service.transcribe(audio_bytes, file.filename or "audio.wav")


# ── Health ────────────────────────────────────────────────────

health_router = APIRouter(tags=["Health"])


@health_router.get("/health", response_model=HealthResponse)
async def health_check():
    services: list[ServiceHealth] = []

    # Ollama
    start = time.perf_counter()
    ollama_ok = await llm_service.health_check()
    services.append(ServiceHealth(
        service="ollama",
        status="healthy" if ollama_ok else "unhealthy",
        latency_ms=round((time.perf_counter() - start) * 1000, 1),
    ))

    # Qdrant
    start = time.perf_counter()
    qdrant_ok = await retrieval_engine.health_check()
    services.append(ServiceHealth(
        service="qdrant",
        status="healthy" if qdrant_ok else "unhealthy",
        latency_ms=round((time.perf_counter() - start) * 1000, 1),
    ))

    # Redis
    start = time.perf_counter()
    redis_ok = await semantic_cache.health_check()
    services.append(ServiceHealth(
        service="redis",
        status="healthy" if redis_ok else "unhealthy",
        latency_ms=round((time.perf_counter() - start) * 1000, 1),
    ))

    overall = "healthy" if all(s.status == "healthy" for s in services) else "degraded"

    return HealthResponse(
        status=overall,
        version=settings.app_version,
        services=services,
    )
