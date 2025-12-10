import importlib
import pkgutil
import os
import asyncio
from typing import Dict, Optional

from .agents.base import BaseAgent
from .llm_service import LLMService


class UnifiedLLMClient:
    """
    Unified LLM client that uses settings to select provider and model.
    This replaces the old LocalLLMClient and CloudLLMClient with a single
    settings-aware implementation.
    """

    def __init__(self) -> None:
        """Initialize the unified client (provider selected from settings)"""
        pass

    def generate(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        """
        Generate a completion using the configured LLM provider from settings.

        Args:
            prompt: The user prompt
            system_prompt: Optional system prompt

        Returns:
            Generated text
        """
        # Run the async function in a sync context (for backward compatibility)
        return asyncio.run(
            LLMService.generate(
                prompt=prompt,
                system_prompt=system_prompt,
                max_tokens=2000,  # Explicitly set to prevent infinite generation
                stream=False
            )
        )

    async def generate_async(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 2000,
        stream: bool = False
    ):
        """
        Async version of generate for use in async contexts.

        Args:
            prompt: The user prompt
            system_prompt: Optional system prompt
            temperature: Temperature for generation
            max_tokens: Maximum tokens to generate
            stream: Whether to stream the response

        Returns:
            Generated text or async generator if streaming
        """
        return await LLMService.generate(
            prompt=prompt,
            system_prompt=system_prompt,
            temperature=temperature,
            max_tokens=max_tokens,
            stream=stream
        )

    async def generate_image(
        self,
        prompt: str,
        size: Optional[str] = None,
        quality: Optional[str] = None,
        style: Optional[str] = None
    ) -> str:
        """
        Generate image using configured provider from settings.

        Args:
            prompt: Image description prompt
            size: Image size (e.g., "1024x1024")
            quality: Image quality ("standard" or "hd")
            style: Image style ("natural" or "vivid")

        Returns:
            URL of generated image
        """
        return await LLMService.generate_image(
            prompt=prompt,
            size=size,
            quality=quality,
            style=style
        )


class AgentManager:
    """Loads and stores available agents dynamically."""

    def __init__(self) -> None:
        self.available_agents: Dict[str, BaseAgent] = {}
        # Use the new unified client that reads from settings
        self.llm_client = UnifiedLLMClient()
        self._load_agents()

    def _load_agents(self) -> None:
        """Dynamically import all agent modules and register them."""
        package = importlib.import_module(f"{__package__}.agents")
        for _, module_name, _ in pkgutil.iter_modules(package.__path__):
            module = importlib.import_module(f"{package.__name__}.{module_name}")
            for obj in module.__dict__.values():
                if (
                    isinstance(obj, type)
                    and issubclass(obj, BaseAgent)
                    and obj is not BaseAgent
                ):
                    instance = obj(llm_client=self.llm_client)
                    self.available_agents[instance.name()] = instance
