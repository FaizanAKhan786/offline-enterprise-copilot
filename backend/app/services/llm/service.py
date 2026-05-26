"""
LLM service: manages model inference via Ollama with streaming support.
"""

from __future__ import annotations

import time
from collections.abc import AsyncIterator
from typing import Any

import httpx

from app.core.config import get_settings
from app.core.logging import get_logger
from app.schemas.schemas import ModelInfo

logger = get_logger(__name__)
settings = get_settings()


class LLMService:
    """Handles all interactions with the Ollama inference server."""

    def __init__(self) -> None:
        self.base_url = settings.ollama_base_url
        self.default_model = settings.default_model
        self.timeout = settings.llm_timeout
        self._client = httpx.AsyncClient(
            base_url=self.base_url,
            timeout=httpx.Timeout(self.timeout, connect=10.0),
        )

    async def list_models(self) -> list[ModelInfo]:
        """List all models available in Ollama."""
        try:
            resp = await self._client.get("/api/tags")
            resp.raise_for_status()
            data = resp.json()
            models = []
            for m in data.get("models", []):
                models.append(
                    ModelInfo(
                        name=m["name"],
                        size=_format_bytes(m.get("size", 0)),
                        family=m.get("details", {}).get("family"),
                        parameter_size=m.get("details", {}).get("parameter_size"),
                        quantization=m.get("details", {}).get("quantization_level"),
                    )
                )
            return models
        except httpx.HTTPError as e:
            logger.error("Failed to list models", error=str(e))
            return []

    async def generate(
        self,
        prompt: str,
        model: str | None = None,
        system: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
        context: list[dict[str, str]] | None = None,
    ) -> dict[str, Any]:
        """Non-streaming generation."""
        model = model or self.default_model
        messages = self._build_messages(prompt, system, context)
        start = time.perf_counter()

        resp = await self._client.post(
            "/api/chat",
            json={
                "model": model,
                "messages": messages,
                "stream": False,
                "options": {
                    "temperature": temperature,
                    "num_predict": max_tokens,
                },
            },
        )
        resp.raise_for_status()
        data = resp.json()
        elapsed_ms = int((time.perf_counter() - start) * 1000)

        return {
            "content": data.get("message", {}).get("content", ""),
            "model": model,
            "tokens_used": data.get("eval_count", 0),
            "latency_ms": elapsed_ms,
        }

    async def generate_stream(
        self,
        prompt: str,
        model: str | None = None,
        system: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
        context: list[dict[str, str]] | None = None,
    ) -> AsyncIterator[str]:
        """Streaming generation — yields token chunks."""
        model = model or self.default_model
        messages = self._build_messages(prompt, system, context)

        async with self._client.stream(
            "POST",
            "/api/chat",
            json={
                "model": model,
                "messages": messages,
                "stream": True,
                "options": {
                    "temperature": temperature,
                    "num_predict": max_tokens,
                },
            },
        ) as resp:
            resp.raise_for_status()
            async for line in resp.aiter_lines():
                if not line:
                    continue
                import orjson
                chunk = orjson.loads(line)
                token = chunk.get("message", {}).get("content", "")
                if token:
                    yield token
                if chunk.get("done", False):
                    break

    async def embed(self, text: str, model: str | None = None) -> list[float]:
        """Generate embedding vector for text."""
        model = model or settings.embedding_model
        resp = await self._client.post(
            "/api/embeddings",
            json={"model": model, "prompt": text},
        )
        resp.raise_for_status()
        return resp.json()["embedding"]

    async def embed_batch(self, texts: list[str], model: str | None = None) -> list[list[float]]:
        """Generate embeddings for multiple texts."""
        return [await self.embed(t, model) for t in texts]

    async def health_check(self) -> bool:
        try:
            resp = await self._client.get("/api/tags")
            return resp.status_code == 200
        except httpx.HTTPError:
            return False

    def _build_messages(
        self,
        prompt: str,
        system: str | None,
        context: list[dict[str, str]] | None,
    ) -> list[dict[str, str]]:
        messages: list[dict[str, str]] = []
        if system:
            messages.append({"role": "system", "content": system})
        if context:
            messages.extend(context)
        messages.append({"role": "user", "content": prompt})
        return messages

    async def close(self) -> None:
        await self._client.aclose()


def _format_bytes(n: int) -> str:
    for unit in ("B", "KB", "MB", "GB"):
        if n < 1024:
            return f"{n:.1f} {unit}"
        n /= 1024
    return f"{n:.1f} TB"


# Singleton
llm_service = LLMService()
