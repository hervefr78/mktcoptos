from __future__ import annotations

from typing import List

from .vector_store import VectorStore


class RAGAgent:
    """Simple retrieval-augmented generation agent."""

    def __init__(self, vector_store: VectorStore) -> None:
        self.vector_store = vector_store

    def run(self, prompt: str) -> str:
        """Retrieve context for the prompt and produce a response.

        The current implementation returns the retrieved context alongside the
        original prompt. In a production system this is where an LLM call would
        be made using the retrieved documents as context.
        """

        documents: List[str] = self.vector_store.similarity_search(prompt)
        if not documents:
            return f"No relevant documents found for: {prompt}"
        context = "\n".join(documents)
        return f"Prompt: {prompt}\nContext:\n{context}"
