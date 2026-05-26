"""
RAG pipeline: combines retrieval with citation-aware LLM generation.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Any

from app.core.logging import get_logger
from app.schemas.schemas import SourceCitation
from app.services.llm.service import llm_service
from app.services.rag.retrieval import RetrievalResult, retrieval_engine

logger = get_logger(__name__)

RAG_SYSTEM_PROMPT = """You are a precise, helpful enterprise AI assistant. Answer the user's question using ONLY the provided context. Follow these rules:

1. If the context contains the answer, provide it clearly with specific details.
2. Cite your sources by referencing [Source N] where N corresponds to the context chunk number.
3. If the context does not contain enough information, say so explicitly.
4. Never fabricate information not present in the context.
5. Be concise but thorough.

CONTEXT:
{context}

Answer the question based on the context above."""


class RAGPipeline:
    """End-to-end RAG pipeline with citation tracking."""

    async def query(
        self,
        question: str,
        document_ids: list[str] | None = None,
        model: str | None = None,
        temperature: float = 0.3,
        max_tokens: int = 4096,
        conversation_context: list[dict[str, str]] | None = None,
    ) -> dict[str, Any]:
        """Non-streaming RAG query."""
        # Retrieve
        results = await retrieval_engine.search(question, document_ids)
        context, sources = self._build_context(results)

        # Generate
        system = RAG_SYSTEM_PROMPT.format(context=context)
        response = await llm_service.generate(
            prompt=question,
            model=model,
            system=system,
            temperature=temperature,
            max_tokens=max_tokens,
            context=conversation_context,
        )

        # Confidence scoring (simple heuristic based on retrieval scores)
        confidence = self._compute_confidence(results, response["content"])

        return {
            **response,
            "sources": sources,
            "confidence": confidence,
        }

    async def query_stream(
        self,
        question: str,
        document_ids: list[str] | None = None,
        model: str | None = None,
        temperature: float = 0.3,
        max_tokens: int = 4096,
        conversation_context: list[dict[str, str]] | None = None,
    ) -> tuple[AsyncIterator[str], list[SourceCitation], float]:
        """Streaming RAG query — returns stream + sources."""
        results = await retrieval_engine.search(question, document_ids)
        context, sources = self._build_context(results)

        system = RAG_SYSTEM_PROMPT.format(context=context)
        stream = llm_service.generate_stream(
            prompt=question,
            model=model,
            system=system,
            temperature=temperature,
            max_tokens=max_tokens,
            context=conversation_context,
        )

        confidence = self._compute_confidence(results)
        return stream, sources, confidence

    def _build_context(
        self, results: list[RetrievalResult]
    ) -> tuple[str, list[SourceCitation]]:
        """Build context string and source citations from retrieval results."""
        if not results:
            return "No relevant context found.", []

        context_parts: list[str] = []
        sources: list[SourceCitation] = []

        for i, r in enumerate(results):
            context_parts.append(f"[Source {i + 1}] (from {r.metadata.get('filename', 'unknown')}, page {r.metadata.get('page', '?')}):\n{r.text}")
            sources.append(
                SourceCitation(
                    document_id=r.metadata.get("document_id", ""),
                    filename=r.metadata.get("filename", "unknown"),
                    chunk_text=r.text[:300],
                    page=r.metadata.get("page"),
                    relevance_score=round(r.score, 4),
                )
            )

        return "\n\n".join(context_parts), sources

    def _compute_confidence(
        self,
        results: list[RetrievalResult],
        response_text: str | None = None,
    ) -> float:
        """Heuristic confidence score based on retrieval quality."""
        if not results:
            return 0.0

        avg_score = sum(r.score for r in results) / len(results)
        top_score = results[0].score if results else 0.0

        # Weighted combination
        confidence = 0.6 * top_score + 0.4 * avg_score

        # Check for hedging language (simple heuristic)
        if response_text:
            hedges = ["i'm not sure", "i don't know", "not enough information", "cannot determine"]
            if any(h in response_text.lower() for h in hedges):
                confidence *= 0.5

        return round(min(confidence, 1.0), 3)


rag_pipeline = RAGPipeline()
