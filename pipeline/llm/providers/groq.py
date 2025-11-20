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
from llm.utils import clean_json_string, repair_json_structure

logger = logging.getLogger(__name__)
T = TypeVar('T', bound=BaseModel)

class GroqProvider(BaseLLMProvider):
    def __init__(self, rate_limiter: RateLimiter):
        self.rate_limiter = rate_limiter
        self.api_key = os.getenv("GROQ_API_KEY")

    @property
    def provider_name(self) -> str:
        return "groq"

    def generate(
        self,
        prompt: str,
        response_model: Type[T],
        model_name: str,
        max_retries: int = 3,
        api_key: Optional[str] = None,
        max_output_tokens: int = 30000
    ) -> tuple[Optional[T], Optional[str]]:
        
        key = api_key if api_key is not None else self.api_key
        if not key:
            logger.debug("GROQ_API_KEY not set, skipping Groq")
            return None, "GROQ_API_KEY not set"

        try:
            schema_json = response_model.model_json_schema()
            schema_str = str(schema_json)

            structured_prompt = f"""{prompt}

IMPORTANT: Respond with VALID JSON ONLY (no markdown, no explanations) that matches this exact schema:
{schema_str}

Return only the JSON object, nothing else."""

            for attempt in range(max_retries):
                response = requests.post(
                    "https://api.groq.com/openai/v1/chat/completions",
                    headers={
                        "Authorization": f"Bearer {key}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": model_name,
                        "messages": [{"role": "user", "content": structured_prompt}],
                        "temperature": 0.1,
                        "max_tokens": max_output_tokens
                    },
                    timeout=30
                )

                if response.status_code == 429:
                    logger.debug(f"Groq rate limited for {model_name}")
                    logger.error(f"Full Groq 429 response: {response.text}")
                    self._handle_rate_limit(response, model_name)
                    return None, "Rate limited (429)"

                if response.status_code >= 400:
                    logger.error(f"Groq API error (HTTP {response.status_code}) for {model_name}:")
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
                    logger.warning(f"❌ Groq {model_name} validation error (attempt {attempt + 1}/{max_retries}): {str(e)[:200]}")
                    if attempt == max_retries - 1:
                        logger.error(f"Failed to validate after {max_retries} attempts with Groq {model_name}")
                        return None, f"Validation error: {str(e)[:100]}"
                    continue

            return None, f"Failed to validate after {max_retries} attempts"

        except requests.exceptions.Timeout:
            logger.debug(f"Timeout calling Groq API ({model_name})")
            return None, "Timeout"
        except requests.exceptions.RequestException as e:
            logger.debug(f"Error calling Groq API ({model_name}): {e}")
            return None, str(e)
        except Exception as e:
            logger.error(f"Unexpected error with Groq ({model_name}): {e}")
            return None, str(e)

    def _handle_rate_limit(self, response, model_name):
        try:
            error_data = response.json()
            error_msg = error_data.get("error", {}).get("message", "")
            error_type = error_data.get("error", {}).get("type", "")
            error_code = error_data.get("error", {}).get("code", "")

            is_daily_quota = (
                "daily" in error_msg.lower() or
                "tokens per day" in error_msg.lower() or
                "TPD" in error_msg or
                error_code == "daily_quota_exceeded" or
                error_type == "tokens"
            )

            if is_daily_quota:
                retry_match = re.search(r'try again in (\d+)h(\d+)m|(\d+)m(\d+)', error_msg)
                if retry_match:
                    groups = retry_match.groups()
                    if groups[0]:
                        hours = int(groups[0])
                        minutes = int(groups[1])
                        retry_seconds = hours * 3600 + minutes * 60
                    else:
                        minutes = int(groups[2]) if groups[2] else 0
                        retry_seconds = minutes * 60
                    retry_until = time.time() + retry_seconds
                else:
                    tomorrow_midnight = datetime.utcnow().replace(
                        hour=0, minute=0, second=0, microsecond=0
                    ) + timedelta(days=1)
                    retry_until = tomorrow_midnight.timestamp()

                retry_time_str = datetime.fromtimestamp(retry_until).strftime('%Y-%m-%d %H:%M UTC')
                reason = f"Daily quota exhausted (TPD)"

                self.rate_limiter.block_model(model_name, retry_until, reason)
                logger.error(f"❌ {model_name} daily quota exhausted! Blocked until {retry_time_str}")
            else:
                logger.debug(f"Groq per-minute rate limit for {model_name}, trying next model")

        except Exception as e:
            logger.error(f"Failed to parse Groq 429 response: {e}")
            logger.error(f"429 response: {response.text}")
