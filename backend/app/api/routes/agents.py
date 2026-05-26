"""
Agent workflow execution routes.
"""

from __future__ import annotations

import time

from fastapi import APIRouter, Depends

from app.api.deps import require_permission, rate_limit
from app.core.security import TokenPayload
from app.schemas.schemas import AgentExecuteRequest, AgentExecuteResponse
from app.services.agents.workflows import execute_workflow

router = APIRouter(prefix="/agents", tags=["Agents"])


@router.post("/execute", response_model=AgentExecuteResponse)
async def execute_agent_workflow(
    body: AgentExecuteRequest,
    user: TokenPayload = Depends(require_permission("agents:execute")),
    _rl: None = Depends(rate_limit),
):
    """Execute a named agent workflow (research, summarize, verify, translate, report)."""
    start = time.perf_counter()

    state = await execute_workflow(
        workflow_name=body.workflow,
        input_text=body.input_text,
        document_ids=[str(d) for d in body.document_ids] if body.document_ids else None,
        model=body.model,
        target_language=body.target_language,
        config=body.config,
    )

    total_ms = int((time.perf_counter() - start) * 1000)

    return AgentExecuteResponse(
        workflow=body.workflow,
        steps=state.get("steps", []),
        final_output=state.get("final_output", ""),
        total_duration_ms=total_ms,
    )


@router.get("/workflows")
async def list_workflows():
    """List available agent workflows."""
    return {
        "workflows": [
            {"name": "research", "description": "Research and summarize from documents", "agents": ["Research", "Summarization"]},
            {"name": "summarize", "description": "Summarize document content", "agents": ["Research", "Summarization"]},
            {"name": "verify", "description": "Research, summarize, and fact-check", "agents": ["Research", "Summarization", "Verification"]},
            {"name": "translate", "description": "Research, summarize, and translate", "agents": ["Research", "Summarization", "Translation"]},
            {"name": "report", "description": "Full pipeline: research → summarize → verify → translate → report", "agents": ["Research", "Summarization", "Verification", "Translation", "Reporting"]},
        ]
    }
