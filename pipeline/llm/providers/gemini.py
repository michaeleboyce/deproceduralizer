import os
import time
import json
import requests
import logging
import re
from datetime import datetime, timedelta
from typing import Optional, Type, TypeVar, Any, List

from pydantic import BaseModel

from llm.providers.base import BaseLLMProvider
from llm.rate_limiter import RateLimiter
from llm.utils import repair_json_structure

logger = logging.getLogger(__name__)
T = TypeVar('T', bound=BaseModel)

class GeminiProvider(BaseLLMProvider):
    def __init__(self, rate_limiter: RateLimiter):
        self.rate_limiter = rate_limiter
        self.api_key = os.getenv("GEMINI_API_KEY")

    @property
    def provider_name(self) -> str:
        return "gemini"

    def _build_versions_to_try(self, model_name: str) -> List[str]:
        """
        Determine which Gemini API versions to try for the given	model.
        """
        forced_version = os.getenv("GEMINI_API_VERSION")
        if forced_version:
            return [forced_version]

        # Default to v1beta first (faster access to previews) then fall back to v1
        return ["v1beta", "v1"]

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
            return None, "API key not provided"

        try:
            headers = {
                "Content-Type": "application/json"
            }

            schema_json = response_model.model_json_schema()
            schema_str = str(schema_json)

            structured_prompt = f"""{prompt}

IMPORTANT: Respond with VALID JSON ONLY (no markdown, no explanations) that matches this exact schema:
{schema_str}

Return only the JSON object, nothing else."""

            payload = {
                "contents": [{
                    "parts": [{
                        "text": structured_prompt
                    }]
                }],
                "generationConfig": {
                    "temperature": 0.1,
                    "topP": 0.95,
                    "topK": 40,
                    "maxOutputTokens": 30000
                }
            }

            versions_to_try = self._build_versions_to_try(model_name)

            for version_index, api_version in enumerate(versions_to_try):
                gemini_api_url = f"https://generativelanguage.googleapis.com/{api_version}/models/{model_name}:generateContent"
                logger.debug(f"Gemini request for {model_name} using API {api_version}")
                retry_due_to_version = False

                for attempt in range(max_retries):
                    response = requests.post(
                        f"{gemini_api_url}?key={key}",
                        headers=headers,
                        json=payload,
                        timeout=30
                    )

                    if response.status_code == 429:
                        logger.debug(f"Gemini rate limited (429) for {model_name}")
                        logger.error(f"Full Gemini 429 response: {response.text}")
                        self._handle_rate_limit(response, model_name)
                        return None, "Rate limited (429)"

                    if response.status_code == 404:
                        logger.warning(
                            f"Gemini model {model_name} not available via {api_version} API "
                            f"(attempt {attempt + 1}/{max_retries})."
                        )
                        logger.debug(f"Full Gemini 404 response: {response.text}")
                        retry_due_to_version = True
                        break

                    if response.status_code >= 400:
                        logger.error(f"Gemini API error (HTTP {response.status_code}) for {model_name}:")
                        logger.error(f"Full response: {response.text}")
                        response.raise_for_status()

                    data = response.json()

                    if "candidates" in data and len(data["candidates"]) > 0:
                        candidate = data["candidates"][0]
                        if "content" in candidate and "parts" in candidate["content"]:
                            response_text = candidate["content"]["parts"][0].get("text", "")

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
                                            raise json.JSONDecodeError("No JSON found", response_text, 0)

                                # Validate with Pydantic
                                validated = response_model.model_validate(json_data)
                                return validated, None

                            except Exception as e:
                                logger.warning(f"❌ Gemini {model_name} validation error (attempt {attempt + 1}/{max_retries}): {str(e)[:200]}")
                                if attempt == max_retries - 1:
                                    logger.error(f"Failed to validate after {max_retries} attempts with Gemini {model_name}")
                                    return None, f"Validation error: {str(e)[:100]}"
                                continue

                    logger.error(f"Unexpected Gemini response format for {model_name}")
                    return None, "Unexpected response format"

                if retry_due_to_version:
                    if version_index < len(versions_to_try) - 1:
                        logger.info(
                            f"Retrying Gemini model {model_name} using API version {versions_to_try[version_index + 1]}"
                        )
                        continue
                    return None, f"Model {model_name} not available via Gemini API"

            return None, f"Failed to validate after {max_retries} attempts"

        except requests.exceptions.Timeout:
            logger.debug(f"Timeout calling Gemini API ({model_name})")
            return None, "Timeout"
        except requests.exceptions.RequestException as e:
            logger.debug(f"Error calling Gemini API ({model_name}): {e}")
            return None, str(e)
        except Exception as e:
            logger.error(f"Unexpected error with Gemini ({model_name}): {e}")
            return None, str(e)

    def _handle_rate_limit(self, response, model_name):
        try:
            error_data = response.json()
            retry_delay = None
            quota_metric = None

            if "error" in error_data and "details" in error_data["error"]:
                for detail in error_data["error"]["details"]:
                    if detail.get("@type") == "type.googleapis.com/google.rpc.RetryInfo":
                        retry_delay_str = detail.get("retryDelay", "")
                        if retry_delay_str.endswith("s"):
                            retry_delay = float(retry_delay_str[:-1])

                    if detail.get("@type") == "type.googleapis.com/google.rpc.QuotaFailure":
                        violations = detail.get("violations", [])
                        if violations:
                            quota_metric = violations[0].get("quotaMetric", "")

            if retry_delay:
                retry_until = time.time() + retry_delay
                retry_time_str = datetime.fromtimestamp(retry_until).strftime('%H:%M:%S')

                is_daily_quota = quota_metric and "PerDay" in quota_metric

                if is_daily_quota:
                    tomorrow_midnight = datetime.utcnow().replace(
                        hour=0, minute=0, second=0, microsecond=0
                    ) + timedelta(days=1)
                    retry_until = tomorrow_midnight.timestamp()
                    retry_time_str = tomorrow_midnight.strftime('%Y-%m-%d %H:%M UTC')
                    reason = f"Daily quota exhausted ({quota_metric})"
                else:
                    reason = f"Rate limit (retry in {retry_delay:.1f}s)"

                self.rate_limiter.block_model(model_name, retry_until, reason)
                logger.info(f"⏱️  {model_name} blocked until {retry_time_str}: {reason}")
            else:
                logger.error(f"429 response without retryDelay: {response.text}")
        except Exception as e:
            logger.error(f"Failed to parse Gemini 429 response: {e}")
            logger.error(f"429 response: {response.text}")
