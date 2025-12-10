"""Celery tasks for ingestion and retrieval-augmented generation."""

from __future__ import annotations

import os
from typing import List, Optional

from celery import Celery

from app.rag.vector_store import VectorStore
from app.rag.rag_agent import RAGAgent

celery_app = Celery(
    "tasks",
    broker=os.getenv("CELERY_BROKER_URL", "redis://redis:6379/0"),
    backend=os.getenv("CELERY_RESULT_BACKEND", "redis://redis:6379/0"),
)

# Configure Celery to suppress deprecation warnings and be Celery 6.0 ready
celery_app.conf.update(
    broker_connection_retry_on_startup=True,  # Explicitly set for Celery 6.0 compatibility
)


# Lazily instantiated singletons for heavy objects
_vector_store: Optional[VectorStore] = None
_rag_agent: Optional[RAGAgent] = None


def _get_vector_store() -> VectorStore:
    global _vector_store
    if _vector_store is None:
        _vector_store = VectorStore()
    return _vector_store


def _get_rag_agent() -> RAGAgent:
    global _rag_agent
    if _rag_agent is None:
        _rag_agent = RAGAgent(_get_vector_store())
    return _rag_agent


@celery_app.task
def run_llm(prompt: str) -> str:
    """Execute a RAG pipeline for the provided prompt."""
    agent = _get_rag_agent()
    return agent.run(prompt)


@celery_app.task
def ingest_data(items: List[str]) -> str:
    """Ingest a list of text items into the vector store."""
    store = _get_vector_store()
    store.add_texts(items)
    return f"Ingested {len(items)} items"
