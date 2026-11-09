"""Chat pipeline — the entry point that mirrors the flow diagram.

Topology:

    START -> guard -> (blocked?) -+-> END
                     |             |
                     +-> retrieve -+-> (passages?) -+-> generate -> validate -> END
                                                      |
                                                      +-> no_evidence -> END

Tracing: LangGraph auto-traces every node when ``LANGCHAIN_TRACING_V2=true``
+ ``LANGCHAIN_API_KEY`` are set. That satisfies the ``@trace("…")`` annotations
in the diagram with zero extra decorators.
"""

import logging
from functools import lru_cache
from typing import Optional

from langgraph.graph import END, StateGraph

from app.application.services.chat_state import ChatResult, ChatState
from app.application.services.nodes.generate import generate_node
from app.application.services.nodes.guard import guard_node
from app.application.services.nodes.no_evidence import no_evidence_node
from app.application.services.nodes.retrieve import retrieve_node
from app.application.services.nodes.routing import (
    route_after_guard,
    route_after_retrieve,
)
from app.application.services.nodes.validate import validate_node
from app.domains.interfaces.access import Principal

log = logging.getLogger(__name__)


@lru_cache(maxsize=1)
def build_chat_graph():
    """Compile the graph once; reuse across requests."""
    graph = StateGraph(ChatState)

    graph.add_node("guard", guard_node)
    graph.add_node("retrieve", retrieve_node)
    graph.add_node("generate", generate_node)
    graph.add_node("no_evidence", no_evidence_node)
    graph.add_node("validate", validate_node)

    graph.set_entry_point("guard")

    graph.add_conditional_edges(
        "guard",
        route_after_guard,
        {"retrieve": "retrieve", "__end__": END},
    )
    graph.add_conditional_edges(
        "retrieve",
        route_after_retrieve,
        {"generate": "generate", "no_evidence": "no_evidence"},
    )
    graph.add_edge("generate", "validate")
    graph.add_edge("no_evidence", END)
    graph.add_edge("validate", END)

    return graph.compile()


def chat(
    principal: Principal,
    question: str,
    thread_id: Optional[str] = None,
) -> ChatResult:
    """Run the full RAG pipeline for one question.

    Args:
        principal: caller identity (tenant / subject / groups) for access control.
        question: the user's latest question.
        thread_id: conversation id; pass None for a one-shot. When provided,
            prior turns are loaded for follow-up query rewriting + continuity.

    Returns:
        ChatResult with answer, sources, status, thread_id, guardrail outcomes.
    """
    if not question or not question.strip():
        raise ValueError("question must not be empty")

    graph = build_chat_graph()
    initial_state: ChatState = {
        "question": question,
        "principal": principal,
        "thread_id": thread_id,
        "blocked": False,
        "status": "answered",
    }
    final_state = graph.invoke(initial_state)

    outcomes = list(final_state.get("input_guard_outcomes") or [])
    outcomes.extend(final_state.get("output_guard_outcomes") or [])

    return ChatResult(
        answer=final_state.get("answer", ""),
        sources=final_state.get("sources", []),
        status=final_state.get("status", "answered"),
        thread_id=thread_id,
        guardrail_outcomes=outcomes,
    )
