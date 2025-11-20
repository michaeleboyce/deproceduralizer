import os
import time
import json
import requests
import logging
import re
from datetime import datetime, timedelta
from typing import Optional, Type, TypeVar, Any

from pydantic import BaseModel

from llm.providers.base import BaseLLMProvider
from llm.rate_limiter import RateLimiter
from llm.utils import clean_json_string

logger = logging.getLogger(__name__)
T = TypeVar('T', bound=BaseModel)

class OpenRouterProvider(BaseLLMProvider):
    def __init__(self, rate_limiter: RateLimiter):
        self.rate_limiter = rate_limiter
        self.api_key = os.getenv("OPENROUTER_API_KEY")

    @property
    def provider_name(self) -> str:
        return "openrouter"

    def generate(
        self,
        prompt: str,
        response_model: Type[T],
        model_name: str,
        max_retries: int = 3,
        api_key: Optional[str] = None
    ) -> tuple[Optional[T], Optional[str]]:
        
        key = api_key if api_key is not None else self.api_key
        if not key:
            logger.debug("OPENROUTER_API_KEY not set, skipping OpenRouter")
            return None, "OPENROUTER_API_KEY not set"

        try:
            schema_json = response_model.model_json_schema()
            schema_str = str(schema_json)

            structured_prompt = f"""{prompt}

IMPORTANT: Respond with VALID JSON ONLY (no markdown, no explanations) that matches this exact schema:
{schema_str}

Return only the JSON object, nothing else."""

            for attempt in range(max_retries):
                response = requests.post(
                    "https://openrouter.ai/api/v1/chat/completions",
                    headers={
                        "Authorization": f"Bearer {key}",
                        "Content-Type": "application/json",
                        "HTTP-Referer": "https://github.com/deproceduralizer",
                        "X-Title": "DC Code Deproceduralizer",
                    },
                    json={
                        "model": model_name,
                        "messages": [{"role": "user", "content": structured_prompt}],
                        "temperature": 0.1,
                        "max_tokens": 30000
                    },
                    timeout=30
                )

                if response.status_code == 429:
                    logger.debug(f"OpenRouter rate limited for {model_name}")
                    logger.error(f"Full OpenRouter 429 response: {response.text}")
                    self._handle_rate_limit(response, model_name)
                    return None, "Rate limited (429)"

                if response.status_code >= 400:
                    logger.error(f"OpenRouter API error (HTTP {response.status_code}) for {model_name}:")
                    logger.error(f"Full response: {response.text}")
                    response.raise_for_status()

                response.raise_for_status()
                data = response.json()

                response_text = data.get("choices", [{}])[0].get("message", {}).get("content", "")

                try:
                    # Try direct parse
                    try:
                        cleaned_text = clean_json_string(response_text.strip())
                        json_data = json.loads(cleaned_text)
                    except json.JSONDecodeError:
                        # Extract from markdown block
                        json_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', response_text, re.DOTALL)
                        if json_match:
                            cleaned_json = clean_json_string(json_match.group(1))
                            json_data = json.loads(cleaned_json)
                        else:
                            # Find first {...} object
                            obj_match = re.search(r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}', response_text, re.DOTALL)
                            if obj_match:
                                cleaned_obj = clean_json_string(obj_match.group(0))
                                json_data = json.loads(cleaned_obj)
                            else:
                                raise json.JSONDecodeError("No JSON found", response_text, 0)

                    # Validate with Pydantic
                    validated = response_model.model_validate(json_data)
                    return validated, None

                except Exception as e:
                    logger.warning(f"❌ OpenRouter {model_name} validation error (attempt {attempt + 1}/{max_retries}): {str(e)[:200]}")
                    if attempt == max_retries - 1:
                        logger.error(f"Failed to validate after {max_retries} attempts with OpenRouter {model_name}")
                        return None, f"Validation error: {str(e)[:100]}"
                    continue

            return None, f"Failed to validate after {max_retries} attempts"

        except requests.exceptions.Timeout:
            logger.debug(f"Timeout calling OpenRouter API ({model_name})")
            return None, "Timeout"
        except requests.exceptions.RequestException as e:
            logger.debug(f"Error calling OpenRouter API ({model_name}): {e}")
            return None, str(e)
        except Exception as e:
            logger.error(f"Unexpected error with OpenRouter ({model_name}): {e}")
            return None, str(e)

    def _handle_rate_limit(self, response, model_name):
        try:
            error_data = response.json()
            error_msg = error_data.get("error", {}).get("message", "")
            error_code = error_data.get("error", {}).get("code")
            metadata = error_data.get("error", {}).get("metadata", {})

            is_daily_limit = (
                "free-models-per-day" in error_msg.lower() or
                "daily free tier limit" in error_msg.lower() or
                "free model requests per day" in error_msg.lower() or
                error_code == 429
            )

            headers_metadata = metadata.get("headers", {})
            reset_timestamp_str = headers_metadata.get("X-RateLimit-Reset")

            if reset_timestamp_str:
                try:
                    reset_timestamp = int(reset_timestamp_str) / 1000
                    retry_until = reset_timestamp
                    retry_time_str = datetime.fromtimestamp(retry_until).strftime('%Y-%m-%d %H:%M UTC')
                    reason = "Daily limit (X-RateLimit-Reset)"
                except (ValueError, TypeError):
                    tomorrow_midnight = datetime.utcnow().replace(
                        hour=0, minute=0, second=0, microsecond=0
                    ) + timedelta(days=1)
                    retry_until = tomorrow_midnight.timestamp()
                    retry_time_str = tomorrow_midnight.strftime('%Y-%m-%d %H:%M UTC')
                    reason = "Daily limit exhausted"
            elif is_daily_limit:
                tomorrow_midnight = datetime.utcnow().replace(
                    hour=0, minute=0, second=0, microsecond=0
                ) + timedelta(days=1)
                retry_until = tomorrow_midnight.timestamp()
                retry_time_str = tomorrow_midnight.strftime('%Y-%m-%d %H:%M UTC')
                reason = "Daily free tier limit exhausted"

                self.rate_limiter.block_model(model_name, retry_until, reason)
                logger.error(f"❌ {model_name} daily limit reached! Blocked until {retry_time_str}")
            else:
                logger.debug(f"OpenRouter per-minute rate limit for {model_name}, trying next model")

        except Exception as e:
            logger.error(f"Failed to parse OpenRouter 429 response: {e}")
            logger.error(f"429 response: {response.text}")
