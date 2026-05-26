"""
Hybrid retrieval engine: dense (Qdrant) + sparse (BM25) with reranking.
"""

from __future__ import annotations

import uuid
from typing import Any

from qdrant_client import AsyncQdrantClient, models
from rank_bm25 import BM25Okapi

from app.core.config import get_settings
from app.core.logging import get_logger
from app.services.llm.service import llm_service
from app.services.rag.processor import TextChunk

logger = get_logger(__name__)
settings = get_settings()


class RetrievalResult:
    __slots__ = ("text", "metadata", "score", "source")

    def __init__(self, text: str, metadata: dict[str, Any], score: float, source: str) -> None:
        self.text = text
        self.metadata = metadata
        self.score = score
        self.source = source  # "dense" | "sparse" | "hybrid"


class RetrievalEngine:
    """Hybrid retrieval combining dense vector search and BM25 keyword search."""

    def __init__(self) -> None:
        self._qdrant: AsyncQdrantClient | None = None
        self._bm25_corpus: dict[str, list[str]] = {}  # doc_id -> tokenized chunks
        self._bm25_chunks: dict[str, list[dict[str, Any]]] = {}
        self._bm25_index: dict[str, BM25Okapi] = {}

    async def _get_qdrant(self) -> AsyncQdrantClient:
        if self._qdrant is None:
            self._qdrant = AsyncQdrantClient(url=settings.qdrant_url)
            await self._ensure_collection()
        return self._qdrant

    async def _ensure_collection(self) -> None:
        client = self._qdrant
        collections = await client.get_collections()
        names = [c.name for c in collections.collections]
        if settings.qdrant_collection not in names:
            await client.create_collection(
                collection_name=settings.qdrant_collection,
                vectors_config=models.VectorParams(
                    size=settings.embedding_dimensions,
                    distance=models.Distance.COSINE,
                ),
            )
            # Create payload indices for metadata filtering
            await client.create_payload_index(
                collection_name=settings.qdrant_collection,
                field_name="document_id",
                field_schema=models.PayloadSchemaType.KEYWORD,
            )
            logger.info("Created Qdrant collection", name=settings.qdrant_collection)

    async def index_chunks(self, chunks: list[TextChunk], document_id: str) -> int:
        """Index chunks into both dense (Qdrant) and sparse (BM25) stores."""
        if not chunks:
            return 0

        client = await self._get_qdrant()

        # Generate embeddings
        texts = [c.text for c in chunks]
        embeddings = await llm_service.embed_batch(texts)

        # Upsert into Qdrant
        points = [
            models.PointStruct(
                id=str(uuid.uuid4()),
                vector=emb,
                payload={
                    "text": chunk.text,
                    "document_id": chunk.metadata.get("document_id", document_id),
                    "filename": chunk.metadata.get("filename", ""),
                    "page": chunk.metadata.get("page", 0),
                    "chunk_index": chunk.metadata.get("chunk_index", i),
                },
            )
            for i, (chunk, emb) in enumerate(zip(chunks, embeddings))
        ]

        # Batch upsert (100 at a time)
        batch_size = 100
        for i in range(0, len(points), batch_size):
            batch = points[i : i + batch_size]
            await client.upsert(
                collection_name=settings.qdrant_collection,
                points=batch,
            )

        # Build BM25 index for this document
        tokenized = [t.lower().split() for t in texts]
        self._bm25_corpus[document_id] = tokenized
        self._bm25_chunks[document_id] = [
            {"text": c.text, **c.metadata} for c in chunks
        ]
        self._bm25_index[document_id] = BM25Okapi(tokenized)

        logger.info("Indexed chunks", document_id=document_id, count=len(chunks))
        return len(chunks)

    async def search(
        self,
        query: str,
        document_ids: list[str] | None = None,
        top_k: int | None = None,
        alpha: float | None = None,
    ) -> list[RetrievalResult]:
        """Hybrid search combining dense and sparse results."""
        top_k = top_k or settings.top_k
        alpha = alpha if alpha is not None else settings.hybrid_alpha

        # Dense search
        dense_results = await self._dense_search(query, document_ids, top_k * 2)

        # Sparse search
        sparse_results = self._sparse_search(query, document_ids, top_k * 2)

        # Merge with reciprocal rank fusion
        merged = self._reciprocal_rank_fusion(dense_results, sparse_results, alpha)

        # Take top_k
        results = merged[:top_k]

        logger.info(
            "Hybrid search",
            query_len=len(query),
            dense_hits=len(dense_results),
            sparse_hits=len(sparse_results),
            returned=len(results),
        )
        return results

    async def _dense_search(
        self,
        query: str,
        document_ids: list[str] | None,
        limit: int,
    ) -> list[RetrievalResult]:
        client = await self._get_qdrant()
        query_embedding = await llm_service.embed(query)

        filter_cond = None
        if document_ids:
            filter_cond = models.Filter(
                must=[
                    models.FieldCondition(
                        key="document_id",
                        match=models.MatchAny(any=document_ids),
                    )
                ]
            )

        hits = await client.search(
            collection_name=settings.qdrant_collection,
            query_vector=query_embedding,
            query_filter=filter_cond,
            limit=limit,
        )

        return [
            RetrievalResult(
                text=hit.payload.get("text", ""),
                metadata={
                    "document_id": hit.payload.get("document_id", ""),
                    "filename": hit.payload.get("filename", ""),
                    "page": hit.payload.get("page", 0),
                },
                score=hit.score,
                source="dense",
            )
            for hit in hits
        ]

    def _sparse_search(
        self,
        query: str,
        document_ids: list[str] | None,
        limit: int,
    ) -> list[RetrievalResult]:
        tokenized_query = query.lower().split()
        results: list[RetrievalResult] = []

        target_docs = document_ids or list(self._bm25_index.keys())

        for doc_id in target_docs:
            if doc_id not in self._bm25_index:
                continue
            bm25 = self._bm25_index[doc_id]
            scores = bm25.get_scores(tokenized_query)
            chunks = self._bm25_chunks[doc_id]

            for i, score in enumerate(scores):
                if score > 0 and i < len(chunks):
                    results.append(
                        RetrievalResult(
                            text=chunks[i]["text"],
                            metadata={
                                "document_id": doc_id,
                                "filename": chunks[i].get("filename", ""),
                                "page": chunks[i].get("page", 0),
                            },
                            score=float(score),
                            source="sparse",
                        )
                    )

        results.sort(key=lambda r: r.score, reverse=True)
        return results[:limit]

    def _reciprocal_rank_fusion(
        self,
        dense: list[RetrievalResult],
        sparse: list[RetrievalResult],
        alpha: float,
        k: int = 60,
    ) -> list[RetrievalResult]:
        """Merge results using Reciprocal Rank Fusion (RRF)."""
        scores: dict[str, float] = {}
        result_map: dict[str, RetrievalResult] = {}

        for rank, r in enumerate(dense):
            key = r.metadata.get("document_id", "") + ":" + str(hash(r.text))
            scores[key] = scores.get(key, 0) + alpha / (k + rank + 1)
            result_map[key] = r

        for rank, r in enumerate(sparse):
            key = r.metadata.get("document_id", "") + ":" + str(hash(r.text))
            scores[key] = scores.get(key, 0) + (1 - alpha) / (k + rank + 1)
            if key not in result_map:
                result_map[key] = r

        sorted_keys = sorted(scores.keys(), key=lambda k: scores[k], reverse=True)
        return [
            RetrievalResult(
                text=result_map[k].text,
                metadata=result_map[k].metadata,
                score=scores[k],
                source="hybrid",
            )
            for k in sorted_keys
            if k in result_map
        ]

    async def delete_document(self, document_id: str) -> None:
        """Remove all chunks for a document."""
        client = await self._get_qdrant()
        await client.delete(
            collection_name=settings.qdrant_collection,
            points_selector=models.FilterSelector(
                filter=models.Filter(
                    must=[
                        models.FieldCondition(
                            key="document_id",
                            match=models.MatchValue(value=document_id),
                        )
                    ]
                )
            ),
        )
        self._bm25_corpus.pop(document_id, None)
        self._bm25_chunks.pop(document_id, None)
        self._bm25_index.pop(document_id, None)
        logger.info("Deleted document vectors", document_id=document_id)

    async def health_check(self) -> bool:
        try:
            client = await self._get_qdrant()
            await client.get_collections()
            return True
        except Exception:
            return False


retrieval_engine = RetrievalEngine()
