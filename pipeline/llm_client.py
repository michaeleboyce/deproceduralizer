#!/usr/bin/env python3
"""
Unified LLM client wrapper with Instructor integration.

This module provides a single interface for calling LLMs with Pydantic validation:
- Gemini API (primary, with per-model rate limiting and cascade)
- Ollama (fallback when Gemini is rate limited)

Key features:
- Automatic validation and retry via Instructor
- Rate limiting with model cascade (Gemini 2.5 Flash → 2.5 Flash-Lite → 2.0 Flash → 2.0 Flash-Lite → Ollama)
- Returns validated Pydantic model instances (not raw JSON)
- Graceful fallback handling with periodic Gemini retries

Usage:
    from pipeline.llm_client import LLMClient
    from pipeline.models import ReportingRequirement

    client = LLMClient()
    result = client.generate(
        prompt="Analyze this section for reporting requirements...",
        response_model=ReportingRequirement,
        section_id="dc-1-101"
    )

    if result:
        print(f"Used model: {result.model_used}")
        print(f"Data: {result.data}")  # Validated Pydantic instance
"""

import instructor
import os
import time
from datetime import datetime
from typing import Optional, TypeVar, Type, Any, Dict
from pydantic import BaseModel
import requests
from dotenv import load_dotenv

from common import setup_logging

# Load environment variables
load_dotenv()

logger = setup_logging(__name__)

# Type variable for generic response model
T = TypeVar('T', bound=BaseModel)

# API Configuration
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# Model configurations with rate limits (RPM, RPD)
# Ordered by model version: 2.5 Flash → 2.5 Flash-Lite → 2.0 Flash → 2.0 Flash-Lite
GEMINI_MODELS = [
    {"name": "gemini-2.5-flash", "rpm": 10, "rpd": 250},
    {"name": "gemini-2.5-flash-lite", "rpm": 15, "rpd": 1000},
    {"name": "gemini-2.0-flash", "rpm": 15, "rpd": 200},
    {"name": "gemini-2.0-flash-lite", "rpm": 30, "rpd": 200},
]

OLLAMA_HOST = "http://localhost:11434"
OLLAMA_MODEL = "phi4-mini"

# Rate limiting configuration
RPM_WINDOW = 60  # seconds
GEMINI_CALL_DELAY = 0.1  # seconds between Gemini calls to avoid rate limits
GEMINI_RETRY_INTERVAL = 180  # seconds (3 minutes) before retrying Gemini after fallback


class RateLimiter:
    """Track API calls and enforce rate limits per model."""

    def __init__(self):
        # Track calls per model: model_name -> {"minute_calls": [], "day_calls": 0, "day_start": date}
        self.model_trackers = {}

    def _get_tracker(self, model_config: dict):
        """Get or create tracker for a model."""
        model_name = model_config["name"]
        if model_name not in self.model_trackers:
            self.model_trackers[model_name] = {
                "minute_calls": [],
                "day_calls": 0,
                "day_start": datetime.utcnow().date()
            }
        return self.model_trackers[model_name]

    def wait_if_needed(self, model_config: dict) -> bool:
        """
        Check if model is within rate limits.

        Returns:
            True if model can be used, False to skip to next model
        """
        now = datetime.utcnow()
        tracker = self._get_tracker(model_config)
        rpm_limit = model_config["rpm"]
        rpd_limit = model_config["rpd"]

        # Reset day counter if new day
        if now.date() > tracker["day_start"]:
            tracker["day_calls"] = 0
            tracker["day_start"] = now.date()

        # Check daily limit
        if tracker["day_calls"] >= rpd_limit:
            logger.debug(f"Hit daily limit for {model_config['name']} ({rpd_limit}), trying next model")
            return False

        # Remove calls older than 1 minute
        cutoff = now.timestamp() - RPM_WINDOW
        tracker["minute_calls"] = [t for t in tracker["minute_calls"] if t > cutoff]

        # Check per-minute limit
        if len(tracker["minute_calls"]) >= rpm_limit:
            logger.debug(f"Hit per-minute limit for {model_config['name']} ({rpm_limit} RPM), trying next model")
            return False

        return True

    def record_call(self, model_config: dict):
        """Record that an API call was made for this model."""
        tracker = self._get_tracker(model_config)
        tracker["minute_calls"].append(datetime.utcnow().timestamp())
        tracker["day_calls"] += 1


class LLMResponse(BaseModel):
    """Wrapper for LLM response with metadata."""
    data: Any  # Will be the validated Pydantic model instance
    model_used: str


class LLMClient:
    """
    Unified LLM client with Instructor integration and rate-limited cascade.

    Automatically tries Gemini models in sequence, falling back to Ollama,
    with periodic retries of Gemini after fallback.
    """

    def __init__(self):
        """Initialize LLM client with rate limiter."""
        self.rate_limiter = RateLimiter()
        self.stats = {
            'last_gemini_call_time': 0,
            'last_gemini_fail_time': 0,
            'using_fallback': False,
            'fallback_to_ollama_logged': False
        }

    def _call_gemini_with_instructor(
        self,
        prompt: str,
        response_model: Type[T],
        model_name: str,
        max_retries: int = 3
    ) -> Optional[T]:
        """
        Call Gemini API with Instructor for validated responses.

        Args:
            prompt: The prompt to send to the LLM
            response_model: Pydantic model class for validation
            model_name: Gemini model name
            max_retries: Number of validation retries

        Returns:
            Validated Pydantic model instance or None if failed
        """
        if not GEMINI_API_KEY:
            return None

        try:
            # Create a custom client for Gemini that works with instructor
            # Instructor expects an OpenAI-compatible client, so we'll handle Gemini manually
            # and validate with Pydantic

            headers = {
                "Content-Type": "application/json"
            }

            # Construct the payload
            # For structured output, we ask the model to return JSON matching the schema
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

            gemini_api_url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent"

            # Retry loop for validation errors
            for attempt in range(max_retries):
                response = requests.post(
                    f"{gemini_api_url}?key={GEMINI_API_KEY}",
                    headers=headers,
                    json=payload,
                    timeout=30
                )

                # Check for rate limiting
                if response.status_code == 429:
                    logger.debug(f"Gemini rate limited (429) for {model_name}")
                    return None

                response.raise_for_status()
                data = response.json()

                # Extract text from Gemini response
                if "candidates" in data and len(data["candidates"]) > 0:
                    candidate = data["candidates"][0]
                    if "content" in candidate and "parts" in candidate["content"]:
                        response_text = candidate["content"]["parts"][0].get("text", "")

                        # Try to parse and validate with Pydantic
                        try:
                            # Clean up response text (remove markdown if present)
                            import re
                            import json

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
                            return validated

                        except Exception as e:
                            logger.debug(f"Validation error (attempt {attempt + 1}/{max_retries}): {e}")
                            if attempt == max_retries - 1:
                                logger.error(f"Failed to validate after {max_retries} attempts with {model_name}")
                                return None
                            # Continue to next retry
                            continue

                logger.error(f"Unexpected Gemini response format for {model_name}")
                return None

            return None

        except requests.exceptions.Timeout:
            logger.debug(f"Timeout calling Gemini API ({model_name})")
            return None
        except requests.exceptions.RequestException as e:
            logger.debug(f"Error calling Gemini API ({model_name}): {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error with Gemini ({model_name}): {e}")
            return None

    def _call_ollama_with_instructor(
        self,
        prompt: str,
        response_model: Type[T],
        model_name: str = OLLAMA_MODEL,
        max_retries: int = 3
    ) -> Optional[T]:
        """
        Call Ollama API with Instructor for validated responses.

        Args:
            prompt: The prompt to send to the LLM
            response_model: Pydantic model class for validation
            model_name: Ollama model name
            max_retries: Number of validation retries

        Returns:
            Validated Pydantic model instance or None if failed
        """
        try:
            # Similar approach for Ollama
            schema_json = response_model.model_json_schema()
            schema_str = str(schema_json)

            structured_prompt = f"""{prompt}

IMPORTANT: Respond with VALID JSON ONLY (no markdown, no explanations) that matches this exact schema:
{schema_str}

Return only the JSON object, nothing else."""

            # Retry loop for validation errors
            for attempt in range(max_retries):
                response = requests.post(
                    f"{OLLAMA_HOST}/api/generate",
                    json={
                        "model": model_name,
                        "prompt": structured_prompt,
                        "stream": False
                    },
                    timeout=90
                )
                response.raise_for_status()
                data = response.json()

                response_text = data.get("response", "")

                # Try to parse and validate with Pydantic
                try:
                    import re
                    import json

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
                    return validated

                except Exception as e:
                    logger.debug(f"Validation error (attempt {attempt + 1}/{max_retries}): {e}")
                    if attempt == max_retries - 1:
                        logger.error(f"Failed to validate after {max_retries} attempts with Ollama")
                        return None
                    # Continue to next retry
                    continue

            return None

        except requests.exceptions.Timeout:
            logger.debug(f"Timeout calling Ollama")
            return None
        except requests.exceptions.RequestException as e:
            logger.debug(f"Error calling Ollama API: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error with Ollama: {e}")
            return None

    def generate(
        self,
        prompt: str,
        response_model: Type[T],
        section_id: Optional[str] = None
    ) -> Optional[LLMResponse]:
        """
        Generate structured output using LLM cascade with automatic validation.

        Tries Gemini models in order, falling back to Ollama if needed.
        Returns validated Pydantic model instance.

        Args:
            prompt: The prompt to send to the LLM
            response_model: Pydantic model class for validation
            section_id: Optional section ID for logging

        Returns:
            LLMResponse with validated data and model_used, or None if failed
        """
        current_time = time.time()

        # Check if we should retry Gemini (if we've been using fallback for a while)
        last_gemini_fail = self.stats.get('last_gemini_fail_time', 0)
        using_fallback = self.stats.get('using_fallback', False)

        # If we're using fallback and it's been 3+ minutes, try Gemini again
        should_retry_gemini = (
            using_fallback and
            (current_time - last_gemini_fail) >= GEMINI_RETRY_INTERVAL
        )

        # Try each Gemini model in sequence
        if GEMINI_API_KEY and (not using_fallback or should_retry_gemini):
            if should_retry_gemini:
                logger.info("⟳ Retrying Gemini after fallback period")

            # Add delay between Gemini calls to avoid rate limits
            if self.stats.get('last_gemini_call_time', 0) > 0:
                time_since_last = current_time - self.stats.get('last_gemini_call_time', 0)
                if time_since_last < GEMINI_CALL_DELAY:
                    time.sleep(GEMINI_CALL_DELAY - time_since_last)

            for model_config in GEMINI_MODELS:
                model_name = model_config["name"]

                # Check rate limits for this specific model
                if not self.rate_limiter.wait_if_needed(model_config):
                    logger.debug(f"{model_name} rate limited, trying next model")
                    continue

                self.stats['last_gemini_call_time'] = time.time()
                result = self._call_gemini_with_instructor(prompt, response_model, model_name)

                if result:
                    self.rate_limiter.record_call(model_config)
                    logger.debug(f"Successfully used {model_name}" + (f" for {section_id}" if section_id else ""))

                    # Successfully used Gemini, clear fallback state
                    if using_fallback:
                        logger.info("✓ Gemini is working again, resuming normal operation")
                        self.stats['using_fallback'] = False

                    return LLMResponse(data=result, model_used=model_name)
                else:
                    logger.debug(f"Failed with {model_name}, trying next model")

        # All Gemini models failed or rate limited, fallback to Ollama
        self.stats['last_gemini_fail_time'] = current_time
        if not self.stats.get('fallback_to_ollama_logged'):
            logger.info(f"⚠ All Gemini models exhausted, falling back to Ollama {OLLAMA_MODEL}")
            logger.info(f"  Will retry Gemini every {GEMINI_RETRY_INTERVAL}s")
            self.stats['fallback_to_ollama_logged'] = True
        self.stats['using_fallback'] = True

        result = self._call_ollama_with_instructor(prompt, response_model, OLLAMA_MODEL)
        if result:
            return LLMResponse(data=result, model_used=OLLAMA_MODEL)

        return None
