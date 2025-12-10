from abc import ABC, abstractmethod
from typing import Any, Optional


class BaseAgent(ABC):
    """Abstract base class for agents."""

    def __init__(self, llm_client: Optional[Any] = None) -> None:
        """Initialize the agent with an optional LLM client."""
        self.llm_client = llm_client

    @abstractmethod
    def run(self, *args: Any, **kwargs: Any) -> Any:
        """Execute the agent's main behavior."""
        raise NotImplementedError

    @abstractmethod
    def name(self) -> str:
        """Return the agent's display name."""
        raise NotImplementedError

    @abstractmethod
    def description(self) -> str:
        """Return a short description of the agent."""
        raise NotImplementedError
