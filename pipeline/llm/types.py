from typing import Any, Optional
from pydantic import BaseModel

class LLMResponse(BaseModel):
    """Wrapper for LLM response with metadata."""
    data: Any  # Will be the validated Pydantic model instance
    model_used: str
