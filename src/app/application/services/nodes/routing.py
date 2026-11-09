"""Routing functions for LangGraph conditional edges."""

from app.application.services.chat_state import ChatState


def route_after_guard(state: ChatState) -> str:
    """Input guard blocked -> END immediately. Otherwise -> retrieve."""
    if state.get("blocked"):
        return "__end__"
    return "retrieve"


def route_after_retrieve(state: ChatState) -> str:
    """Passages above the relevance threshold -> generate. None -> no_evidence."""
    if state.get("retrieved_passages"):
        return "generate"
    return "no_evidence"
