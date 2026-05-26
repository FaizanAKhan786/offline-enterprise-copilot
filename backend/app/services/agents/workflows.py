"""
LangGraph agentic workflows: multi-step reasoning with tool use.
"""

from __future__ import annotations

import time
from typing import Any, TypedDict

from app.core.logging import get_logger
from app.schemas.schemas import AgentStepResult
from app.services.llm.service import llm_service
from app.services.rag.retrieval import retrieval_engine

logger = get_logger(__name__)


# ── State ────────────────────────────────────────────────────

class AgentState(TypedDict, total=False):
    input_text: str
    document_ids: list[str]
    model: str
    target_language: str | None
    steps: list[AgentStepResult]
    context: str
    draft: str
    verified: str
    translated: str
    final_output: str


# ── Agent Functions ──────────────────────────────────────────

async def research_agent(state: AgentState) -> AgentState:
    """Retrieve relevant context from documents."""
    start = time.perf_counter()
    query = state["input_text"]
    doc_ids = state.get("document_ids", [])

    results = await retrieval_engine.search(query, doc_ids or None, top_k=8)
    context = "\n\n".join(
        f"[{r.metadata.get('filename', '?')} p.{r.metadata.get('page', '?')}]: {r.text}"
        for r in results
    )

    elapsed = int((time.perf_counter() - start) * 1000)
    state["context"] = context or "No relevant documents found."
    state.setdefault("steps", []).append(
        AgentStepResult(
            agent="Research Agent",
            action="document_retrieval",
            output=f"Retrieved {len(results)} relevant chunks",
            duration_ms=elapsed,
        )
    )
    return state


async def summarization_agent(state: AgentState) -> AgentState:
    """Summarize the retrieved context."""
    start = time.perf_counter()
    prompt = f"""Summarize the following information concisely, preserving key facts and figures.
Focus on answering this question: {state['input_text']}

Information:
{state.get('context', 'No context available.')}

Provide a clear, structured summary."""

    result = await llm_service.generate(
        prompt=prompt,
        model=state.get("model"),
        temperature=0.3,
    )

    elapsed = int((time.perf_counter() - start) * 1000)
    state["draft"] = result["content"]
    state.setdefault("steps", []).append(
        AgentStepResult(
            agent="Summarization Agent",
            action="summarize",
            output=result["content"][:200] + "..." if len(result["content"]) > 200 else result["content"],
            duration_ms=elapsed,
        )
    )
    return state


async def verification_agent(state: AgentState) -> AgentState:
    """Verify claims in the draft against the source context."""
    start = time.perf_counter()
    prompt = f"""You are a fact-checking agent. Review the following draft against the source material.

DRAFT:
{state.get('draft', '')}

SOURCE MATERIAL:
{state.get('context', '')}

Tasks:
1. Identify any claims not supported by the source material.
2. Flag any potential hallucinations or inaccuracies.
3. Produce a verified version with corrections noted.

Output the verified text with [VERIFIED], [UNVERIFIED], or [CORRECTED] tags."""

    result = await llm_service.generate(
        prompt=prompt,
        model=state.get("model"),
        temperature=0.1,
    )

    elapsed = int((time.perf_counter() - start) * 1000)
    state["verified"] = result["content"]
    state.setdefault("steps", []).append(
        AgentStepResult(
            agent="Verification Agent",
            action="fact_check",
            output=result["content"][:200] + "...",
            duration_ms=elapsed,
        )
    )
    return state


async def translation_agent(state: AgentState) -> AgentState:
    """Translate the output to the target language."""
    start = time.perf_counter()
    target = state.get("target_language", "en")
    source_text = state.get("verified") or state.get("draft") or state.get("context", "")

    if target == "en":
        state["translated"] = source_text
        state.setdefault("steps", []).append(
            AgentStepResult(
                agent="Translation Agent",
                action="skip",
                output="Target language is English, no translation needed.",
                duration_ms=0,
            )
        )
        return state

    lang_names = {"ar": "Arabic", "hi": "Hindi", "en": "English"}
    lang_name = lang_names.get(target, target)

    prompt = f"Translate the following text to {lang_name}. Preserve formatting and technical terms.\n\n{source_text}"
    result = await llm_service.generate(
        prompt=prompt,
        model=state.get("model"),
        temperature=0.2,
    )

    elapsed = int((time.perf_counter() - start) * 1000)
    state["translated"] = result["content"]
    state.setdefault("steps", []).append(
        AgentStepResult(
            agent="Translation Agent",
            action="translate",
            output=f"Translated to {lang_name}",
            duration_ms=elapsed,
        )
    )
    return state


async def reporting_agent(state: AgentState) -> AgentState:
    """Compile a final structured report."""
    start = time.perf_counter()
    content = state.get("translated") or state.get("verified") or state.get("draft") or ""

    prompt = f"""Compile a professional report from the following analysis.

Question: {state['input_text']}
Analysis: {content}

Structure the report with:
1. Executive Summary
2. Key Findings
3. Detailed Analysis
4. Recommendations (if applicable)
5. Sources Referenced

Be clear, concise, and professional."""

    result = await llm_service.generate(
        prompt=prompt,
        model=state.get("model"),
        temperature=0.4,
    )

    elapsed = int((time.perf_counter() - start) * 1000)
    state["final_output"] = result["content"]
    state.setdefault("steps", []).append(
        AgentStepResult(
            agent="Reporting Agent",
            action="compile_report",
            output="Final report compiled",
            duration_ms=elapsed,
        )
    )
    return state


# ── Workflow Definitions ─────────────────────────────────────

WORKFLOWS: dict[str, list] = {
    "research": [research_agent, summarization_agent],
    "summarize": [research_agent, summarization_agent],
    "verify": [research_agent, summarization_agent, verification_agent],
    "translate": [research_agent, summarization_agent, translation_agent],
    "report": [research_agent, summarization_agent, verification_agent, translation_agent, reporting_agent],
}


async def execute_workflow(
    workflow_name: str,
    input_text: str,
    document_ids: list[str] | None = None,
    model: str | None = None,
    target_language: str | None = None,
    config: dict[str, Any] | None = None,
) -> AgentState:
    """Execute a named workflow as a sequential agent pipeline."""
    agents = WORKFLOWS.get(workflow_name)
    if not agents:
        raise ValueError(f"Unknown workflow: {workflow_name}. Available: {list(WORKFLOWS.keys())}")

    state: AgentState = {
        "input_text": input_text,
        "document_ids": document_ids or [],
        "model": model,
        "target_language": target_language,
        "steps": [],
    }

    total_start = time.perf_counter()

    for agent_fn in agents:
        logger.info("Executing agent", agent=agent_fn.__name__, workflow=workflow_name)
        state = await agent_fn(state)

    total_ms = int((time.perf_counter() - total_start) * 1000)

    # Set final output if not explicitly set
    if "final_output" not in state or not state["final_output"]:
        state["final_output"] = (
            state.get("translated")
            or state.get("verified")
            or state.get("draft")
            or state.get("context", "")
        )

    logger.info(
        "Workflow complete",
        workflow=workflow_name,
        steps=len(state.get("steps", [])),
        total_ms=total_ms,
    )

    return state
