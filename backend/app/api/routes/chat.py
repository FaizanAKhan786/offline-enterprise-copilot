"""
Chat routes: streaming and non-streaming completions with optional RAG.
"""

from __future__ import annotations

import time
import uuid

import orjson
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, rate_limit, require_permission
from app.core.security import TokenPayload
from app.db.session import get_db
from app.models.models import Conversation, Message
from app.schemas.schemas import ChatRequest, ChatResponse, StreamChunk
from app.services.cache.service import semantic_cache
from app.services.llm.service import llm_service
from app.services.rag.pipeline import rag_pipeline

router = APIRouter(prefix="/chat", tags=["Chat"])


@router.post("/completions")
async def chat_completions(
    body: ChatRequest,
    db: AsyncSession = Depends(get_db),
    user: TokenPayload = Depends(require_permission("chat")),
    _rl: None = Depends(rate_limit),
):
    """Chat completion with optional RAG and streaming."""
    model = body.model or llm_service.default_model

    # Resolve or create conversation
    conversation = await _get_or_create_conversation(db, body.conversation_id, user.sub, model, body.language)

    # Build conversation context from history
    context = await _build_context(db, conversation.id)

    # Save user message
    user_msg = Message(
        conversation_id=conversation.id,
        role="user",
        content=body.message,
    )
    db.add(user_msg)
    await db.flush()

    if body.stream:
        return StreamingResponse(
            _stream_response(body, model, context, conversation.id, db),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "X-Accel-Buffering": "no",
            },
        )

    # Non-streaming
    start = time.perf_counter()

    if body.use_rag:
        doc_ids = [str(d) for d in body.document_ids] if body.document_ids else None
        result = await rag_pipeline.query(
            body.message,
            document_ids=doc_ids,
            model=model,
            temperature=body.temperature,
            max_tokens=body.max_tokens,
            conversation_context=context,
        )
    else:
        # Check cache
        cached = await semantic_cache.get(body.message, model)
        if cached:
            result = cached
        else:
            result = await llm_service.generate(
                prompt=body.message,
                model=model,
                temperature=body.temperature,
                max_tokens=body.max_tokens,
                context=context,
            )
            result["sources"] = []
            result["confidence"] = None
            await semantic_cache.set(body.message, model, result)

    elapsed = int((time.perf_counter() - start) * 1000)

    # Save assistant message
    assistant_msg = Message(
        conversation_id=conversation.id,
        role="assistant",
        content=result["content"],
        model=model,
        tokens_used=result.get("tokens_used"),
        latency_ms=elapsed,
        sources={"citations": [s.model_dump() for s in result.get("sources", [])]},
        confidence=result.get("confidence"),
    )
    db.add(assistant_msg)
    await db.flush()

    return ChatResponse(
        conversation_id=conversation.id,
        message_id=assistant_msg.id,
        content=result["content"],
        model=model,
        sources=result.get("sources", []),
        confidence=result.get("confidence"),
        tokens_used=result.get("tokens_used"),
        latency_ms=elapsed,
    )


async def _stream_response(body, model, context, conversation_id, db):
    """Generator for SSE streaming response."""
    full_content = []

    if body.use_rag:
        doc_ids = [str(d) for d in body.document_ids] if body.document_ids else None
        stream, sources, confidence = await rag_pipeline.query_stream(
            body.message,
            document_ids=doc_ids,
            model=model,
            temperature=body.temperature,
            max_tokens=body.max_tokens,
            conversation_context=context,
        )
    else:
        stream = llm_service.generate_stream(
            prompt=body.message,
            model=model,
            temperature=body.temperature,
            max_tokens=body.max_tokens,
            context=context,
        )
        sources = []
        confidence = None

    async for token in stream:
        full_content.append(token)
        chunk = StreamChunk(
            conversation_id=str(conversation_id),
            delta=token,
            done=False,
        )
        yield f"data: {orjson.dumps(chunk.model_dump()).decode()}\n\n"

    # Final chunk with sources
    final = StreamChunk(
        conversation_id=str(conversation_id),
        delta="",
        done=True,
        sources=sources if sources else None,
        confidence=confidence,
    )
    yield f"data: {orjson.dumps(final.model_dump()).decode()}\n\n"

    # Save assistant message
    content = "".join(full_content)
    msg = Message(
        conversation_id=conversation_id,
        role="assistant",
        content=content,
        model=model,
        sources={"citations": [s.model_dump() for s in sources]} if sources else None,
        confidence=confidence,
    )
    db.add(msg)
    await db.commit()


async def _get_or_create_conversation(
    db: AsyncSession, conv_id: uuid.UUID | None, user_id: str, model: str, language: str
) -> Conversation:
    if conv_id:
        result = await db.execute(select(Conversation).where(Conversation.id == conv_id))
        conv = result.scalar_one_or_none()
        if conv:
            return conv

    conv = Conversation(
        user_id=uuid.UUID(user_id),
        model=model,
        language=language,
    )
    db.add(conv)
    await db.flush()
    return conv


async def _build_context(db: AsyncSession, conversation_id: uuid.UUID) -> list[dict[str, str]]:
    """Load recent conversation history for context."""
    result = await db.execute(
        select(Message)
        .where(Message.conversation_id == conversation_id)
        .order_by(Message.created_at.desc())
        .limit(20)
    )
    messages = result.scalars().all()
    return [
        {"role": m.role, "content": m.content}
        for m in reversed(messages)
    ]


@router.get("/conversations")
async def list_conversations(
    db: AsyncSession = Depends(get_db),
    user: TokenPayload = Depends(get_current_user),
):
    result = await db.execute(
        select(Conversation)
        .where(Conversation.user_id == uuid.UUID(user.sub))
        .order_by(Conversation.updated_at.desc())
        .limit(50)
    )
    conversations = result.scalars().all()
    return [
        {
            "id": str(c.id),
            "title": c.title,
            "model": c.model,
            "language": c.language,
            "updated_at": c.updated_at.isoformat(),
        }
        for c in conversations
    ]
