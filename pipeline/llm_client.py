#!/usr/bin/env python3
"""
Unified LLM client wrapper with dual cascade strategies.

This module provides a single interface for calling LLMs with Pydantic validation:
- Gemini API (primary, with per-model rate limiting and cascade)
- Groq API (secondary, OpenAI-compatible, 7 models)
- Ollama (final fallback, local)

Cascade Strategies:
- "simple" (default): Gemini → Ollama (preserves Groq rate limits)
- "extended": Gemini → Groq (9 models) → Ollama (maximum resilience)

Key features:
- Automatic validation and retry via Pydantic
- Per-model rate limiting with intelligent cascade
- Enhanced statistics tracking (model usage, timing, tier switches)
- Smart logging (only on model changes, summary at end)
- Returns validated Pydantic model instances (not raw JSON)
- Graceful fallback handling with periodic retries

Usage:
    from pipeline.llm_client import LLMClient
    from pipeline.models import ReportingRequirement

    # Simple strategy (default)
    client = LLMClient(cascade_strategy="simple")

    # Extended strategy (with Groq)
    client = LLMClient(cascade_strategy="extended")

    result = client.generate(
        prompt="Analyze this section for reporting requirements...",
        response_model=ReportingRequirement,
        section_id="dc-1-101"
    )

    if result:
        print(f"Used model: {result.model_used}")
        print(f"Data: {result.data}")  # Validated Pydantic instance

    # Get usage statistics
    stats = client.get_stats_summary()
    print(stats)
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
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

# Cascade strategy configuration
CASCADE_STRATEGY = os.getenv("LLM_CASCADE_STRATEGY", "simple")  # "simple" or "extended"

# Model configurations with rate limits (RPM, RPD, TPM)
# Ordered by model version: 2.5 Flash → 2.5 Flash-Lite → 2.0 Flash → 2.0 Flash-Lite
GEMINI_MODELS = [
    {"name": "gemini-2.5-flash", "rpm": 10, "rpd": 250},
    {"name": "gemini-2.5-flash-lite", "rpm": 15, "rpd": 1000},
    {"name": "gemini-2.0-flash", "rpm": 15, "rpd": 200},
    {"name": "gemini-2.0-flash-lite", "rpm": 30, "rpd": 200},
]

# Groq model configurations (OpenAI-compatible API)
# Ordered by capability: compound models first, then high-capacity models
GROQ_MODELS = [
    # Compound models (highest quality)
    {"name": "groq/compound", "rpm": 30, "rpd": 250, "tpm": 70000},
    {"name": "groq/compound-mini", "rpm": 30, "rpd": 250, "tpm": 70000},

    # High-capacity models
    {"name": "moonshotai/kimi-k2-instruct", "rpm": 60, "rpd": 1000, "tpm": 10000},
    {"name": "openai/gpt-oss-120b", "rpm": 30, "rpd": 1000, "tpm": 8000},
    {"name": "qwen/qwen3-32b", "rpm": 60, "rpd": 1000, "tpm": 6000},
    {"name": "llama-3.3-70b-versatile", "rpm": 30, "rpd": 1000, "tpm": 12000},
    {"name": "llama-3.1-8b-instant", "rpm": 30, "rpd": 14400, "tpm": 6000},
    {"name": "meta-llama/llama-4-maverick-17b-128e-instruct", "rpm": 30, "rpd": 1000, "tpm": 6000},
    {"name": "meta-llama/llama-4-scout-17b-16e-instruct", "rpm": 30, "rpd": 1000, "tpm": 30000},
]

OLLAMA_HOST = "http://localhost:11434"
OLLAMA_MODEL = "phi4-mini"

# Rate limiting configuration
RPM_WINDOW = 60  # seconds
GEMINI_CALL_DELAY = 0.1  # seconds between Gemini calls to avoid rate limits
GEMINI_RETRY_INTERVAL = 600  # seconds (10 minutes) before retrying Gemini after fallback


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

    Supports dual cascade strategies:
    - "simple": Gemini → Ollama (default)
    - "extended": Gemini → Groq → Ollama
    """

    def __init__(self, cascade_strategy: Optional[str] = None):
        """
        Initialize LLM client with rate limiter and stats tracking.

        Args:
            cascade_strategy: "simple" or "extended" (defaults to env var LLM_CASCADE_STRATEGY)
        """
        self.rate_limiter = RateLimiter()
        self.cascade_strategy = (cascade_strategy or CASCADE_STRATEGY).lower()

        # Validate strategy
        if self.cascade_strategy not in ["simple", "extended"]:
            logger.warning(f"Invalid cascade strategy '{self.cascade_strategy}', defaulting to 'simple'")
            self.cascade_strategy = "simple"

        # Enhanced statistics tracking
        self.stats = {
            # Strategy info
            'cascade_strategy': self.cascade_strategy,
            'session_start_time': time.time(),

            # Current model tracking
            'current_model': None,
            'current_model_calls': 0,
            'current_model_start_time': None,

            # Tier attempt times
            'last_gemini_call_time': 0,
            'last_gemini_attempt_time': 0,
            'last_groq_attempt_time': 0,
            'last_gemini_fail_time': 0,

            # Fallback state
            'using_fallback': False,
            'using_groq_fallback': False,
            'fallback_to_ollama_logged': False,
            'groq_fallback_logged': False,

            # Per-model call counts
            'model_call_counts': {},

            # Tier switches (timestamp, from_model, to_model, reason)
            'tier_switches': [],

            # Tier time tracking
            'time_on_gemini': 0,
            'time_on_groq': 0,
            'time_on_ollama': 0,
            'last_tier_switch_time': time.time()
        }

        # Log initialization
        strategy_desc = {
            'simple': 'Gemini (4) → Ollama (1)',
            'extended': 'Gemini (4) → Groq (9) → Ollama (1)'
        }
        logger.info(f"LLM Client initialized with '{self.cascade_strategy}' cascade strategy:")
        logger.info(f"  {strategy_desc[self.cascade_strategy]}")

    def _log_model_switch(self, new_model: str, reason: str = "Rate limited"):
        """
        Log a model switch and update statistics.

        Args:
            new_model: The new model being switched to
            reason: Reason for the switch
        """
        current_time = time.time()
        previous_model = self.stats['current_model']

        # Only log if actually changing models
        if previous_model == new_model:
            return

        # Update tier time tracking
        if previous_model:
            time_on_current = current_time - self.stats['last_tier_switch_time']
            if any(previous_model in m['name'] for m in GEMINI_MODELS):
                self.stats['time_on_gemini'] += time_on_current
            elif any(previous_model in m['name'] for m in GROQ_MODELS):
                self.stats['time_on_groq'] += time_on_current
            elif previous_model == OLLAMA_MODEL:
                self.stats['time_on_ollama'] += time_on_current

        # Log the switch
        if previous_model:
            # Calculate time and calls for previous model
            time_on_prev = current_time - self.stats['current_model_start_time']
            minutes = int(time_on_prev // 60)
            seconds = int(time_on_prev % 60)
            calls = self.stats['current_model_calls']

            # Log switch with stats and colors
            YELLOW = '\033[93m'
            ORANGE = '\033[38;5;208m'
            DIM = '\033[2m'
            RESET = '\033[0m'
            logger.info(f"{YELLOW}⟳ Model Switch:{RESET} {DIM}{previous_model}{RESET} → {ORANGE}{new_model}{RESET}")
            logger.info(f"  ├─ Previous model: {calls} calls in {minutes}m {seconds}s")

            # Show time since last attempt at different tiers
            if 'gemini' in new_model.lower():
                logger.info(f"  ├─ Time since last Gemini attempt: 0s")
            elif any(new_model in m['name'] for m in GROQ_MODELS):
                time_since_gemini = current_time - self.stats.get('last_gemini_attempt_time', current_time)
                logger.info(f"  ├─ Time since last Gemini attempt: {int(time_since_gemini)}s")
            elif new_model == OLLAMA_MODEL:
                time_since_gemini = current_time - self.stats.get('last_gemini_attempt_time', current_time)
                time_since_groq = current_time - self.stats.get('last_groq_attempt_time', current_time)
                logger.info(f"  ├─ Time since last Gemini attempt: {int(time_since_gemini)}s")
                if self.cascade_strategy == "extended":
                    logger.info(f"  ├─ Time since last Groq attempt: {int(time_since_groq)}s")

            logger.info(f"  └─ Reason: {DIM}{reason}{RESET}")

            # Record tier switch
            self.stats['tier_switches'].append({
                'timestamp': current_time,
                'from': previous_model,
                'to': new_model,
                'reason': reason
            })

        # Update current model tracking
        self.stats['current_model'] = new_model
        self.stats['current_model_calls'] = 0
        self.stats['current_model_start_time'] = current_time
        self.stats['last_tier_switch_time'] = current_time

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

    def _repair_json_structure(self, json_data: Any, response_model: Type[T]) -> Any:
        """
        Heuristically repair JSON structure to match response model.
        
        Common repairs:
        - If model expects object with single list field but got a list, wrap it.
        """
        # Only attempt repair if we got a list but expected a dict (Pydantic models are dicts in JSON)
        if isinstance(json_data, list):
            # Check if response_model has exactly one field that is a list
            fields = response_model.model_fields
            if len(fields) == 1:
                field_name = next(iter(fields))
                # We assume if it's a single field, it's likely the list wrapper we want
                # This is a safe heuristic for our specific use cases (ObligationsList, etc.)
                logger.debug(f"Repairing JSON: wrapping list in '{field_name}'")
                return {field_name: json_data}
                
        return json_data

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

Ensure the response is a JSON OBJECT, not a list.
Return only the JSON object, nothing else."""

            # Retry loop for validation errors
            for attempt in range(max_retries):
                response = requests.post(
                    f"{OLLAMA_HOST}/api/generate",
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
                                # Fallback: try to find a list [...] if we can't find an object
                                list_match = re.search(r'\[.*\]', response_text, re.DOTALL)
                                if list_match:
                                    json_data = json.loads(list_match.group(0))
                                else:
                                    raise json.JSONDecodeError("No JSON found", response_text, 0)

                    # Attempt heuristic repair
                    json_data = self._repair_json_structure(json_data, response_model)

                    # Validate with Pydantic
                    validated = response_model.model_validate(json_data)
                    return validated

                except Exception as e:
                    logger.debug(f"Validation error (attempt {attempt + 1}/{max_retries}): {e}")
                    if attempt == max_retries - 1:
                        logger.error(f"Failed to validate after {max_retries} attempts with Ollama. Error: {str(e)[:200]}...")
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

    def _call_groq_with_instructor(
        self,
        prompt: str,
        response_model: Type[T],
        model_name: str,
        max_retries: int = 3
    ) -> Optional[T]:
        """
        Call Groq API (OpenAI-compatible) with structured outputs.

        Args:
            prompt: The prompt to send to the LLM
            response_model: Pydantic model class for validation
            model_name: Groq model name (e.g., "moonshotai/kimi-k2-instruct")
            max_retries: Number of validation retries

        Returns:
            Validated Pydantic model instance or None if failed
        """
        if not GROQ_API_KEY:
            logger.debug("GROQ_API_KEY not set, skipping Groq")
            return None

        try:
            # Use requests instead of OpenAI client to have more control
            schema_json = response_model.model_json_schema()
            schema_str = str(schema_json)

            structured_prompt = f"""{prompt}

IMPORTANT: Respond with VALID JSON ONLY (no markdown, no explanations) that matches this exact schema:
{schema_str}

Return only the JSON object, nothing else."""

            # Retry loop for validation errors
            for attempt in range(max_retries):
                response = requests.post(
                    "https://api.groq.com/openai/v1/chat/completions",
                    headers={
                        "Authorization": f"Bearer {GROQ_API_KEY}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": model_name,
                        "messages": [{"role": "user", "content": structured_prompt}],
                        "temperature": 0.1,
                        "max_tokens": 30000
                    },
                    timeout=30
                )

                # Check for rate limiting
                if response.status_code == 429:
                    logger.debug(f"Groq rate limited for {model_name}")
                    return None

                response.raise_for_status()
                data = response.json()

                response_text = data.get("choices", [{}])[0].get("message", {}).get("content", "")

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
                        logger.error(f"Failed to validate after {max_retries} attempts with {model_name}")
                        return None
                    # Continue to next retry
                    continue

            return None

        except requests.exceptions.Timeout:
            logger.debug(f"Timeout calling Groq API ({model_name})")
            return None
        except requests.exceptions.RequestException as e:
            logger.debug(f"Error calling Groq API ({model_name}): {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error with Groq ({model_name}): {e}")
            return None

    def generate(
        self,
        prompt: str,
        response_model: Type[T],
        section_id: Optional[str] = None
    ) -> Optional[LLMResponse]:
        """
        Generate structured output using dual-strategy LLM cascade.

        Strategy "simple": Gemini → Ollama
        Strategy "extended": Gemini → Groq → Ollama

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
        using_groq_fallback = self.stats.get('using_groq_fallback', False)

        # If we're using fallback and it's been 3+ minutes, try Gemini again
        should_retry_gemini = (
            (using_fallback or using_groq_fallback) and
            (current_time - last_gemini_fail) >= GEMINI_RETRY_INTERVAL
        )

        # === TIER 1: Try Gemini models ===
        if GEMINI_API_KEY and (not using_fallback or should_retry_gemini):
            if should_retry_gemini:
                current_model = self.stats.get('current_model', 'unknown')
                calls = self.stats.get('current_model_calls', 0)
                time_on_current = current_time - self.stats.get('current_model_start_time', current_time)
                minutes = int(time_on_current // 60)
                seconds = int(time_on_current % 60)
                logger.info(f"⟳ Retrying Gemini after {minutes}m {seconds}s on {current_model} ({calls} calls)")

            # Add delay between Gemini calls to avoid rate limits
            if self.stats.get('last_gemini_call_time', 0) > 0:
                time_since_last = current_time - self.stats.get('last_gemini_call_time', 0)
                if time_since_last < GEMINI_CALL_DELAY:
                    time.sleep(GEMINI_CALL_DELAY - time_since_last)

            self.stats['last_gemini_attempt_time'] = time.time()

            for model_config in GEMINI_MODELS:
                model_name = model_config["name"]

                # Check rate limits for this specific model
                if not self.rate_limiter.wait_if_needed(model_config):
                    logger.debug(f"{model_name} rate limited, trying next model")
                    continue

                # Log model switch if changing
                self._log_model_switch(model_name, "Rate limited" if self.stats['current_model'] else "Initial")

                self.stats['last_gemini_call_time'] = time.time()
                result = self._call_gemini_with_instructor(prompt, response_model, model_name)

                if result:
                    self.rate_limiter.record_call(model_config)
                    logger.debug(f"Successfully used {model_name}" + (f" for {section_id}" if section_id else ""))

                    # Track call count
                    self.stats['current_model_calls'] += 1
                    self.stats['model_call_counts'][model_name] = self.stats['model_call_counts'].get(model_name, 0) + 1

                    # Successfully used Gemini, clear fallback state
                    if using_fallback or using_groq_fallback:
                        logger.info("✓ Gemini is working again, resuming normal operation")
                        self.stats['using_fallback'] = False
                        self.stats['using_groq_fallback'] = False

                    return LLMResponse(data=result, model_used=model_name)
                else:
                    logger.debug(f"Failed with {model_name}, trying next model")

        # Gemini tier exhausted
        self.stats['last_gemini_fail_time'] = current_time

        # === TIER 2: Try Groq models (extended strategy only) ===
        if self.cascade_strategy == "extended" and GROQ_API_KEY:
            self.stats['last_groq_attempt_time'] = current_time

            for model_config in GROQ_MODELS:
                model_name = model_config["name"]

                # Check rate limits for this specific model
                if not self.rate_limiter.wait_if_needed(model_config):
                    logger.debug(f"{model_name} rate limited, trying next model")
                    continue

                # Log model switch if changing
                if not self.stats.get('groq_fallback_logged'):
                    logger.info(f"⚡ Gemini exhausted, trying Groq tier")
                    self.stats['groq_fallback_logged'] = True

                self._log_model_switch(model_name, "Gemini exhausted")

                result = self._call_groq_with_instructor(prompt, response_model, model_name)

                if result:
                    self.rate_limiter.record_call(model_config)
                    logger.debug(f"Successfully used Groq {model_name}" + (f" for {section_id}" if section_id else ""))

                    # Track call count
                    self.stats['current_model_calls'] += 1
                    self.stats['model_call_counts'][model_name] = self.stats['model_call_counts'].get(model_name, 0) + 1
                    self.stats['using_groq_fallback'] = True

                    return LLMResponse(data=result, model_used=model_name)
                else:
                    logger.debug(f"Failed with Groq {model_name}, trying next model")

        # === TIER 3: Fallback to Ollama ===
        if not self.stats.get('fallback_to_ollama_logged'):
            if self.cascade_strategy == "extended":
                logger.info(f"⚠ All Gemini and Groq models exhausted, falling back to Ollama {OLLAMA_MODEL}")
            else:
                logger.info(f"⚠ All Gemini models exhausted, falling back to Ollama {OLLAMA_MODEL}")
            logger.info(f"  Will retry Gemini every {GEMINI_RETRY_INTERVAL}s")
            self.stats['fallback_to_ollama_logged'] = True

        self.stats['using_fallback'] = True
        self._log_model_switch(OLLAMA_MODEL, "All cloud models exhausted")

        result = self._call_ollama_with_instructor(prompt, response_model, OLLAMA_MODEL)
        if result:
            # Track call count
            self.stats['current_model_calls'] += 1
            self.stats['model_call_counts'][OLLAMA_MODEL] = self.stats['model_call_counts'].get(OLLAMA_MODEL, 0) + 1

            return LLMResponse(data=result, model_used=OLLAMA_MODEL)

        return None

    def get_stats_summary(self) -> str:
        """
        Generate a formatted summary of LLM usage statistics.

        Returns:
            Formatted string with usage statistics
        """
        # Calculate totals
        total_calls = sum(self.stats['model_call_counts'].values())
        if total_calls == 0:
            return "No LLM calls made yet."

        session_time = time.time() - self.stats['session_start_time']
        session_minutes = int(session_time // 60)
        session_seconds = int(session_time % 60)

        # Sort models by call count
        sorted_models = sorted(
            self.stats['model_call_counts'].items(),
            key=lambda x: x[1],
            reverse=True
        )

        # Build summary
        lines = []
        lines.append("")
        lines.append("=" * 60)
        lines.append("LLM USAGE STATISTICS")
        lines.append("=" * 60)
        lines.append(f"Cascade Strategy: {self.stats['cascade_strategy']}")
        lines.append(f"Session Duration: {session_minutes}m {session_seconds}s")
        lines.append("")

        # Model usage
        lines.append("Model Usage:")
        for model_name, count in sorted_models:
            percentage = (count / total_calls) * 100
            lines.append(f"  {model_name}: {count} calls ({percentage:.1f}%)")
        lines.append(f"  Total: {total_calls} calls")
        lines.append("")

        # Tier performance
        lines.append("Tier Performance:")

        # Gemini stats
        gemini_calls = sum(count for model, count in sorted_models if any(model in m['name'] for m in GEMINI_MODELS))
        if gemini_calls > 0:
            gemini_minutes = int(self.stats['time_on_gemini'] // 60)
            gemini_seconds = int(self.stats['time_on_gemini'] % 60)
            lines.append(f"  ├─ Gemini: {gemini_calls} calls ({gemini_minutes}m {gemini_seconds}s)")

        # Groq stats (if extended strategy)
        if self.cascade_strategy == "extended":
            groq_calls = sum(count for model, count in sorted_models if any(model in m['name'] for m in GROQ_MODELS))
            if groq_calls > 0:
                groq_minutes = int(self.stats['time_on_groq'] // 60)
                groq_seconds = int(self.stats['time_on_groq'] % 60)
                groq_switches = len([s for s in self.stats['tier_switches'] if any(s['to'] in m['name'] for m in GROQ_MODELS)])
                lines.append(f"  ├─ Groq: {groq_calls} calls ({groq_minutes}m {groq_seconds}s, {groq_switches} fallback periods)")

        # Ollama stats
        ollama_calls = self.stats['model_call_counts'].get(OLLAMA_MODEL, 0)
        if ollama_calls > 0:
            ollama_minutes = int(self.stats['time_on_ollama'] // 60)
            ollama_seconds = int(self.stats['time_on_ollama'] % 60)
            ollama_switches = len([s for s in self.stats['tier_switches'] if s['to'] == OLLAMA_MODEL])
            lines.append(f"  └─ Ollama: {ollama_calls} calls ({ollama_minutes}m {ollama_seconds}s, {ollama_switches} fallback periods)")

        lines.append("")

        # Tier switches summary
        if self.stats['tier_switches']:
            lines.append(f"Tier Switches: {len(self.stats['tier_switches'])} total")
            lines.append("")

        lines.append("=" * 60)

        return "\n".join(lines)
