from abc import ABC, abstractmethod
from typing import Optional, Type, TypeVar, Any, List
from pydantic import BaseModel

T = TypeVar('T', bound=BaseModel)

class BaseLLMProvider(ABC):
    """Abstract base class for LLM providers."""

    @abstractmethod
    def generate(
        self,
        prompt: str,
        response_model: Type[T],
        model_name: str,
        max_retries: int = 3,
        api_key: Optional[str] = None
    ) -> tuple[Optional[T], Optional[str]]:
        """
        Generate a response from the LLM.

        Args:
            prompt: The prompt to send
            response_model: Pydantic model for validation
            model_name: Name of the model to use
            max_retries: Number of retries for validation failures
            api_key: Optional API key override

        Returns:
            Tuple of (validated_result, error_message)
        """
        pass

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Return the name of the provider (e.g., 'gemini', 'groq')."""
        pass
