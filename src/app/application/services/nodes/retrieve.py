"""RETRIEVE node — history -> rewrite -> embed -> vector search -> threshold filter.

This is the only node that talks to the vector store, embeddings, and chat
history. Failures in chat-history loading are non-fatal (log + continue with
empty history); vector-store / embedding failures propagate (chat can't work
without them).
"""

import logging
from typing import Any

from app.application.dependencies.providers import (
    build_access_filter,
    build_chat_history_repository,
    get_db_session,
    get_embeddings,
    get_vector_store,
)
from app.application.services.chat_state import ChatState, RetrievedPassage
from app.application.services.query_rewriter import rewrite_followup_query
from app.core.config import get_settings

log = logging.getLogger(__name__)


def retrieve_node(state: ChatState) -> dict[str, Any]:
    principal = state["principal"]
    thread_id = state.get("thread_id")
    # If the guard node redacted the question, use the redacted version.
    question = state.get("rewritten_query") or state["question"]
    settings = get_settings()

    # --- load chat history (non-fatal on failure) ---
    history: list[dict[str, Any]] = []
    if thread_id:
        try:
            with get_db_session() as session:
                history = build_chat_history_repository(session).get_history(
                    thread_id, limit=settings.chat.history_turns
                )
        except Exception:
            log.exception("Failed to load chat history (continuing with empty history)")

    # --- follow-up rewrite: 1 LLM call, only if we have history ---
    if history and settings.chat.rewrite_followup:
        query_text = rewrite_followup_query(question, history)
    else:
        query_text = question

    # --- embed the (possibly rewritten) query ---
    embedding = get_embeddings().embed_query(query_text)

    # --- tenant / group / subject access filter ---
    access_filter = build_access_filter().build(principal)

    # --- vector search ---
    store = get_vector_store()
    raw = store.query(
        vector=embedding,
        top_k=settings.retrieval.default_k,
        filter=access_filter or None,
    )

    # --- relevance threshold ---
    threshold = settings.retrieval.similarity_threshold
    passages: list[RetrievedPassage] = []
    for r in raw:
        if r["score"] >= threshold:
            meta = r.get("metadata", {})
            passages.append(
                RetrievedPassage(
                    id=r["id"],
                    score=float(r["score"]),
                    metadata=meta,
                    text=meta.get("text", ""),
                )
            )

    log.info(
        "retrieve: %d raw hits, %d above threshold %.2f (query=%r)",
        len(raw),
        len(passages),
        threshold,
        query_text[:80],
    )

    return {
        "history": history,
        "rewritten_query": query_text,
        "query_embedding": embedding,
        "access_filter": access_filter,
        "retrieved_passages": passages,
    }
