import os
import time
import json
import requests
import logging
import re
from threading import Lock
from typing import Optional, Type, TypeVar, Any

from pydantic import BaseModel

from llm.providers.base import BaseLLMProvider
from llm.rate_limiter import RateLimiter
from llm.utils import repair_json_structure

logger = logging.getLogger(__name__)
T = TypeVar('T', bound=BaseModel)

# Global lock for Ollama calls
_OLLAMA_LOCK = Lock()

class OllamaProvider(BaseLLMProvider):
    def __init__(self, rate_limiter: RateLimiter, host: str = "http://localhost:11434"):
        self.rate_limiter = rate_limiter
        self.host = host

    @property
    def provider_name(self) -> str:
        return "ollama"

    def generate(
        self,
        prompt: str,
        response_model: Type[T],
        model_name: str,
        max_retries: int = 3,
        api_key: Optional[str] = None
    ) -> tuple[Optional[T], Optional[str]]:
        
        with _OLLAMA_LOCK:
            try:
                schema_json = response_model.model_json_schema()
                schema_str = str(schema_json)

                structured_prompt = f"""{prompt}

IMPORTANT: Respond with VALID JSON ONLY (no markdown, no explanations) that matches this exact schema:
{schema_str}

Ensure the response is a JSON OBJECT, not a list.
Return only the JSON object, nothing else."""

                for attempt in range(max_retries):
                    response = requests.post(
                        f"{self.host}/api/generate",
                        json={
                            "model": model_name,
                            "prompt": structured_prompt,
                            "stream": False,
                            "options": {
                                "temperature": 0.1,
                                "num_ctx": 4096
                            }
                        },
                        timeout=90
                    )
                    response.raise_for_status()
                    data = response.json()

                    response_text = data.get("response", "")

                    try:
                        # Try direct parse
                        try:
                            json_data = json.loads(response_text.strip())
                        except json.JSONDecodeError:
                            # Extract from markdown block
                            json_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', response_text, re.DOTALL)
                            if json_match:
                                json_data = json.loads(json_match.group(1))
                            else:
                                # Find first {...} object
                                obj_match = re.search(r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}', response_text, re.DOTALL)
                                if obj_match:
                                    json_data = json.loads(obj_match.group(0))
                                else:
                                    # Fallback: try to find a list [...] if we can't find an object
                                    list_match = re.search(r'\[.*\]', response_text, re.DOTALL)
                                    if list_match:
                                        json_data = json.loads(list_match.group(0))
                                    else:
                                        raise json.JSONDecodeError("No JSON found", response_text, 0)

                        # Attempt heuristic repair
                        json_data = repair_json_structure(json_data, response_model)

                        # Validate with Pydantic
                        validated = response_model.model_validate(json_data)
                        return validated, None

                    except Exception as e:
                        logger.warning(f"❌ Ollama validation error (attempt {attempt + 1}/{max_retries}): {str(e)[:200]}")
                        if attempt == max_retries - 1:
                            logger.error(f"Failed to validate after {max_retries} attempts with Ollama")
                            return None, f"Validation error: {str(e)[:100]}"
                        continue

                return None, f"Failed to validate after {max_retries} attempts"

            except requests.exceptions.Timeout:
                logger.debug(f"Timeout calling Ollama")
                return None, "Timeout"
            except requests.exceptions.RequestException as e:
                logger.debug(f"Error calling Ollama API: {e}")
                return None, str(e)
            except Exception as e:
                logger.error(f"Unexpected error with Ollama: {e}")
                return None, str(e)
