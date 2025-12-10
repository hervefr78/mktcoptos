from typing import Any, Optional

from .base import BaseAgent
from ..rag.vector_store import VectorStore


class RAGAgent(BaseAgent):
    """Agent that performs retrieval augmented generation."""

    def __init__(
        self,
        llm_client: Optional[Any] = None,
        vector_store: Optional[VectorStore] = None,
    ) -> None:
        super().__init__(llm_client=llm_client)
        # Delay creation of the vector store until the agent is run to avoid
        # loading heavy models during initialization.
        self.vector_store = vector_store

    def name(self) -> str:
        return "rag"

    def description(self) -> str:
        return "Retrieves context from a vector store and generates a response."

    def run(self, prompt: str, k: int = 5) -> Any:
        """Retrieve relevant context and generate a response.

        Args:
            prompt: The user prompt or query.
            k: Number of similar context chunks to retrieve.

        Returns:
            The generated response from the LLM client.
        """
        if self.llm_client is None or not hasattr(self.llm_client, "generate"):
            raise AttributeError("llm_client must implement a 'generate' method")

        store = self.vector_store or VectorStore()
        self.vector_store = store
        results = store.similarity_search(prompt, k=k)
        context = "\n".join(results)
        combined_prompt = f"{prompt}\n\n{context}" if context else prompt
        # Explicitly set max_tokens to prevent infinite generation
        return self.llm_client.generate(
            combined_prompt,
            max_tokens=3000  # Reasonable for RAG-enhanced responses
        )
