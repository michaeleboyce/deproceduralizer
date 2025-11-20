#!/usr/bin/env python3
"""
Error-driven LLM cascade client that doesn't preemptively check rate limits.

This module provides an alternative cascade strategy that:
- Tries models until they error (no preemptive rate limit checks)
- Maintains an "active" stack of working models
- Maintains a "failed" queue of errored models
- Retries failed models after every 100 attempts since their last failure
- Uses FIFO (First-In-First-Out) for retries
- Moves successful retries to the top of the active stack

Key differences from original:
- No preemptive rate limiting - just try and handle errors
- Dynamic model ordering based on success/failure
- Automatic retry logic with FIFO queue

Usage:
    from pipeline.llm_client_error_driven import ErrorDrivenLLMClient
    from pipeline.models import ReportingRequirement

    client = ErrorDrivenLLMClient()

    result = client.generate(
        prompt="Analyze this section...",
        response_model=ReportingRequirement,
        section_id="dc-1-101"
    )

    if result:
        print(f"Used model: {result.model_used}")
        print(f"Data: {result.data}")

    # Get usage statistics
    stats = client.get_stats_summary()
    print(stats)
"""

import os
import time
from datetime import datetime
from threading import Lock
from typing import Optional, TypeVar, Type, Any
from pydantic import BaseModel
import requests
from dotenv import load_dotenv
from cerebras.cloud.sdk import Cerebras

from common import setup_logging

# Load environment variables
load_dotenv()

logger = setup_logging(__name__)

# Type variable for generic response model
T = TypeVar('T', bound=BaseModel)

# API Configuration
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
VERTEX_API_KEY = os.getenv("VERTEX_API_KEY")
CEREBRAS_API_KEY = os.getenv("CEREBRAS_API_KEY")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

# Model configurations (same as before, but rate limits are informational only)
# Vertex API models (Google AI Studio with higher limits)
VERTEX_MODELS = [
    {"name": "gemini-2.5-flash-lite", "tier": "vertex"},
]

# Standard Gemini API models (backup tier)
GEMINI_MODELS = [
    {"name": "gemini-2.5-flash-lite", "tier": "gemini"},
]

# Cerebras models (third tier - before Groq)
# Rate limits: 60K requests/day, 1M input tokens/day, 1M output tokens/day, 30 requests/min
CEREBRAS_MODELS = [
    {"name": "llama-3.3-70b", "tier": "cerebras"},
]

GROQ_MODELS = [
    {"name": "groq/compound", "tier": "groq"},
    {"name": "groq/compound-mini", "tier": "groq"},
    {"name": "moonshotai/kimi-k2-instruct", "tier": "groq"},
    {"name": "openai/gpt-oss-120b", "tier": "groq"},
    {"name": "qwen/qwen3-32b", "tier": "groq"},
    {"name": "llama-3.3-70b-versatile", "tier": "groq"},
    {"name": "llama-3.1-8b-instant", "tier": "groq"},
    {"name": "meta-llama/llama-4-maverick-17b-128e-instruct", "tier": "groq"},
    {"name": "meta-llama/llama-4-scout-17b-16e-instruct", "tier": "groq"},
]

OPENROUTER_MODELS = [
    {"name": "deepseek/deepseek-r1:free", "tier": "openrouter"},
    {"name": "deepseek/deepseek-chat-v3-0324:free", "tier": "openrouter"},
    {"name": "meta-llama/llama-3.3-70b-instruct:free", "tier": "openrouter"},
    {"name": "qwen/qwen3-235b-a22b:free", "tier": "openrouter"},
    {"name": "qwen/qwen-2.5-72b-instruct:free", "tier": "openrouter"},
]

OLLAMA_HOST = "http://localhost:11434"
OLLAMA_MODEL = "phi4-mini"
OLLAMA_CONFIG = {"name": OLLAMA_MODEL, "tier": "ollama"}

# Retry configuration
RETRY_AFTER_ATTEMPTS = 100  # Retry failed models after this many attempts since failure


class ErrorDrivenCascade:
    """
    Error-driven cascade strategy that doesn't preemptively check rate limits.

    Strategy:
    - Maintains an "active" list of models to try (ordered by success priority)
    - When a model errors, moves it to a "failed" queue
    - Every 100 attempts since a model's failure, retries it
    - If retry succeeds, moves model to top of active list
    - If retry fails, moves model back to failed queue with new failure timestamp
    - Uses FIFO for retry queue
    """

    def __init__(self, all_models: list[dict]):
        """
        Initialize cascade with all available models.

        Args:
            all_models: List of model configurations in priority order
        """
        # Active models to try (ordered by priority/success)
        self.active_models = all_models.copy()

        # Failed models waiting for retry: [(model_config, attempt_when_failed, num_failures)]
        self.failed_queue: list[tuple[dict, int, int]] = []

        # Total number of generation attempts made
        self.total_attempts = 0

        # Lock for thread-safe access
        self.lock = Lock()

        # Track which model is being tried for retry
        self.retry_in_progress: Optional[dict] = None

    def get_next_model(self) -> Optional[dict]:
        """
        Get the next model to try.

        Returns:
            Model configuration dict, or None if no models available
        """
        with self.lock:
            self.total_attempts += 1

            # Check if any failed models are ready for retry (100 attempts since failure)
            ready_for_retry = []
            for model_config, failed_at, num_failures in self.failed_queue:
                if self.total_attempts - failed_at >= RETRY_AFTER_ATTEMPTS:
                    ready_for_retry.append((model_config, failed_at, num_failures))

            # If we have models ready for retry, pop the first one (FIFO)
            if ready_for_retry:
                # Remove from failed queue and return for retry
                model_to_retry = ready_for_retry[0]
                self.failed_queue = [
                    (m, failed_at, num_failures)
                    for m, failed_at, num_failures in self.failed_queue
                    if m["name"] != model_to_retry[0]["name"]
                ]
                self.retry_in_progress = model_to_retry[0]

                attempts_since = self.total_attempts - model_to_retry[1]
                YELLOW = '\033[93m'
                CYAN = '\033[96m'
                RESET = '\033[0m'
                logger.info(f"{YELLOW}🔄 RETRY FROM FAILED QUEUE:{RESET} {CYAN}{model_to_retry[0]['name']}{RESET}")
                logger.info(f"  └─ Failed {model_to_retry[2]} times, {attempts_since} attempts since last failure")
                return model_to_retry[0]

            # Otherwise, try active models in order
            if self.active_models:
                return self.active_models[0]

            # If no active models and no failed to retry, we're stuck
            logger.error("❌ No models available to try! All models have failed.")
            return None

    def mark_success(self, model_config: dict):
        """
        Mark that a model succeeded.

        Args:
            model_config: Model that succeeded
        """
        with self.lock:
            model_name = model_config["name"]

            # If this was a retry that succeeded, celebrate!
            if self.retry_in_progress and self.retry_in_progress["name"] == model_name:
                GREEN = '\033[92m'
                RESET = '\033[0m'
                logger.info(f"{GREEN}✅ RETRY SUCCEEDED:{RESET} {model_name} is working again! Moving to top of active stack.")
                self.retry_in_progress = None

            # Remove from failed queue if present
            self.failed_queue = [
                (m, failed_at, num_failures)
                for m, failed_at, num_failures in self.failed_queue
                if m["name"] != model_name
            ]

            # Move to top of active list if not already there
            self.active_models = [m for m in self.active_models if m["name"] != model_name]
            self.active_models.insert(0, model_config)

    def mark_failure(self, model_config: dict, error_msg: str = ""):
        """
        Mark that a model failed.

        Args:
            model_config: Model that failed
            error_msg: Optional error message for logging
        """
        with self.lock:
            model_name = model_config["name"]

            # If this was a retry that failed, note it
            if self.retry_in_progress and self.retry_in_progress["name"] == model_name:
                RED = '\033[91m'
                RESET = '\033[0m'
                logger.info(f"{RED}❌ RETRY FAILED:{RESET} {model_name} still not working, moving back to failed queue")
                self.retry_in_progress = None

            # Remove from active models
            self.active_models = [m for m in self.active_models if m["name"] != model_name]

            # Check if already in failed queue
            found = False
            for i, (m, failed_at, num_failures) in enumerate(self.failed_queue):
                if m["name"] == model_name:
                    # Update failure count and timestamp
                    self.failed_queue[i] = (m, self.total_attempts, num_failures + 1)
                    found = True
                    logger.debug(f"Model {model_name} failed again (total failures: {num_failures + 1})")
                    break

            if not found:
                # Add to end of failed queue (FIFO)
                self.failed_queue.append((model_config, self.total_attempts, 1))
                logger.info(f"⚠️  {model_name} failed, moving to failed queue. Will retry after {RETRY_AFTER_ATTEMPTS} attempts.")
                if error_msg:
                    logger.debug(f"Error: {error_msg}")

    def get_status(self) -> dict:
        """Get current cascade status."""
        with self.lock:
            return {
                'total_attempts': self.total_attempts,
                'active_models': [m['name'] for m in self.active_models],
                'failed_queue': [(m['name'], failed_at, num_failures) for m, failed_at, num_failures in self.failed_queue],
                'retry_in_progress': self.retry_in_progress['name'] if self.retry_in_progress else None
            }


class LLMResponse(BaseModel):
    """Wrapper for LLM response with metadata."""
    data: Any  # Will be the validated Pydantic model instance
    model_used: str


class ErrorDrivenLLMClient:
    """
    Error-driven LLM client that tries models until they error.

    No preemptive rate limiting - just try and handle failures dynamically.
    """

    def __init__(self):
        """Initialize error-driven LLM client."""
        # Build list of all available models in priority order
        all_models = []

        # Add models based on API key availability (priority order)
        # 1. Vertex (highest tier - Google AI Studio)
        if VERTEX_API_KEY:
            all_models.extend(VERTEX_MODELS)
            logger.info(f"✓ Added {len(VERTEX_MODELS)} Vertex models")

        # 2. Standard Gemini (backup tier)
        if GEMINI_API_KEY:
            all_models.extend(GEMINI_MODELS)
            logger.info(f"✓ Added {len(GEMINI_MODELS)} Gemini models")

        # 3. Cerebras (third tier - high rate limits)
        if CEREBRAS_API_KEY:
            all_models.extend(CEREBRAS_MODELS)
            logger.info(f"✓ Added {len(CEREBRAS_MODELS)} Cerebras models")

        # 4. Groq (fourth tier)
        if GROQ_API_KEY:
            all_models.extend(GROQ_MODELS)
            logger.info(f"✓ Added {len(GROQ_MODELS)} Groq models")

        # 5. OpenRouter (fifth tier)
        if OPENROUTER_API_KEY:
            all_models.extend(OPENROUTER_MODELS)
            logger.info(f"✓ Added {len(OPENROUTER_MODELS)} OpenRouter models")

        # 6. Ollama (final fallback)
        all_models.append(OLLAMA_CONFIG)
        logger.info(f"✓ Added Ollama fallback")

        logger.info(f"🔄 Total models in cascade: {len(all_models)}")

        # Initialize cascade
        self.cascade = ErrorDrivenCascade(all_models)

        # Statistics tracking
        self.stats = {
            'session_start_time': time.time(),
            'current_model': None,
            'current_model_start_time': None,
            'model_call_counts': {},
            'model_success_counts': {},
            'model_failure_counts': {},
            'tier_switches': [],
        }

        # Log initialization
        model_count = len(all_models)
        tier_counts = {}
        for model in all_models:
            tier = model['tier']
            tier_counts[tier] = tier_counts.get(tier, 0) + 1

        tier_desc = ", ".join([f"{tier.capitalize()} ({count})" for tier, count in tier_counts.items()])
        logger.info(f"🚀 Error-Driven LLM Client initialized with {model_count} models:")
        logger.info(f"   {tier_desc}")
        logger.info(f"   Strategy: Try until error → Move to failed queue → Retry after {RETRY_AFTER_ATTEMPTS} attempts")

    def _log_model_switch(self, new_model: str, reason: str = ""):
        """Log a model switch."""
        previous_model = self.stats['current_model']

        # Only log if actually changing models
        if previous_model == new_model:
            return

        current_time = time.time()

        # Log the switch
        if previous_model:
            time_on_prev = current_time - self.stats['current_model_start_time']
            minutes = int(time_on_prev // 60)
            seconds = int(time_on_prev % 60)
            calls = self.stats['model_call_counts'].get(previous_model, 0)

            YELLOW = '\033[93m'
            ORANGE = '\033[38;5;208m'
            DIM = '\033[2m'
            RESET = '\033[0m'
            logger.info(f"{YELLOW}⟳ Model Switch:{RESET} {DIM}{previous_model}{RESET} → {ORANGE}{new_model}{RESET}")
            logger.info(f"  └─ Previous: {calls} calls in {minutes}m {seconds}s. Reason: {reason}")

            # Record tier switch
            self.stats['tier_switches'].append({
                'timestamp': current_time,
                'from': previous_model,
                'to': new_model,
                'reason': reason
            })

        # Update current model tracking
        self.stats['current_model'] = new_model
        self.stats['current_model_start_time'] = current_time

    def _call_vertex_with_instructor(
        self,
        prompt: str,
        response_model: Type[T],
        model_name: str,
        section_id: Optional[str] = None,
        max_retries: int = 3
    ) -> Optional[T]:
        """Call Vertex AI (Google AI Studio) API with Instructor for validated responses."""
        if not VERTEX_API_KEY:
            return None

        # Log API call with worker info
        import threading
        worker_id = threading.current_thread().name
        logger.info(f"🔵 [{worker_id}] Calling Vertex API: {model_name}")

        try:
            headers = {"Content-Type": "application/json"}

            schema_json = response_model.model_json_schema()
            schema_str = str(schema_json)

            structured_prompt = f"""{prompt}

IMPORTANT: Respond with VALID JSON ONLY (no markdown, no explanations) that matches this exact schema:
{schema_str}

Return only the JSON object, nothing else."""

            payload = {
                "contents": [{"parts": [{"text": structured_prompt}]}],
                "generationConfig": {
                    "temperature": 0.1,
                    "topP": 0.95,
                    "topK": 40,
                    "maxOutputTokens": 30000
                }
            }

            # Vertex uses same endpoint as Gemini but with different API key
            vertex_api_url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent"

            for attempt in range(max_retries):
                response = requests.post(
                    f"{vertex_api_url}?key={VERTEX_API_KEY}",
                    headers=headers,
                    json=payload,
                    timeout=30
                )

                if response.status_code == 429:
                    logger.debug(f"Vertex rate limited (429) for {model_name}")
                    return None

                response.raise_for_status()
                data = response.json()

                if "candidates" in data and len(data["candidates"]) > 0:
                    candidate = data["candidates"][0]
                    if "content" in candidate and "parts" in candidate["content"]:
                        response_text = candidate["content"]["parts"][0].get("text", "")

                        try:
                            import re
                            import json

                            try:
                                json_data = json.loads(response_text.strip())
                            except json.JSONDecodeError:
                                json_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', response_text, re.DOTALL)
                                if json_match:
                                    json_data = json.loads(json_match.group(1))
                                else:
                                    obj_match = re.search(r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}', response_text, re.DOTALL)
                                    if obj_match:
                                        json_data = json.loads(obj_match.group(0))
                                    else:
                                        raise json.JSONDecodeError("No JSON found", response_text, 0)

                            validated = response_model.model_validate(json_data)
                            return validated

                        except Exception as e:
                            logger.warning(f"❌ Vertex {model_name} validation error (attempt {attempt + 1}/{max_retries}):")
                            logger.warning(f"   Full error: {str(e)}")
                            if attempt == max_retries - 1:
                                logger.error(f"Failed to validate after {max_retries} attempts with Vertex {model_name}")
                                logger.error(f"   Final error details: {str(e)}")
                                return None

                return None

        except requests.exceptions.HTTPError as e:
            logger.warning(f"❌ Vertex API HTTP error for {model_name}:")
            logger.warning(f"   Status: {e.response.status_code if hasattr(e, 'response') else 'unknown'}")
            logger.warning(f"   Full error: {str(e)}")
            return None
        except Exception as e:
            logger.error(f"❌ Unexpected error with Vertex {model_name}: {str(e)}")
            return None

    def _call_gemini_with_instructor(
        self,
        prompt: str,
        response_model: Type[T],
        model_name: str,
        section_id: Optional[str] = None,
        max_retries: int = 3
    ) -> Optional[T]:
        """Call Gemini API with Instructor for validated responses."""
        if not GEMINI_API_KEY:
            return None

        # Log API call with worker info
        import threading
        worker_id = threading.current_thread().name
        logger.info(f"🔵 [{worker_id}] Calling Gemini API: {model_name}")

        try:
            headers = {"Content-Type": "application/json"}

            schema_json = response_model.model_json_schema()
            schema_str = str(schema_json)

            structured_prompt = f"""{prompt}

IMPORTANT: Respond with VALID JSON ONLY (no markdown, no explanations) that matches this exact schema:
{schema_str}

Return only the JSON object, nothing else."""

            payload = {
                "contents": [{"parts": [{"text": structured_prompt}]}],
                "generationConfig": {
                    "temperature": 0.1,
                    "topP": 0.95,
                    "topK": 40,
                    "maxOutputTokens": 30000
                }
            }

            gemini_api_url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent"

            for attempt in range(max_retries):
                response = requests.post(
                    f"{gemini_api_url}?key={GEMINI_API_KEY}",
                    headers=headers,
                    json=payload,
                    timeout=30
                )

                if response.status_code == 429:
                    logger.debug(f"Gemini rate limited (429) for {model_name}")
                    return None

                response.raise_for_status()
                data = response.json()

                if "candidates" in data and len(data["candidates"]) > 0:
                    candidate = data["candidates"][0]
                    if "content" in candidate and "parts" in candidate["content"]:
                        response_text = candidate["content"]["parts"][0].get("text", "")

                        try:
                            import re
                            import json

                            try:
                                json_data = json.loads(response_text.strip())
                            except json.JSONDecodeError:
                                json_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', response_text, re.DOTALL)
                                if json_match:
                                    json_data = json.loads(json_match.group(1))
                                else:
                                    obj_match = re.search(r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}', response_text, re.DOTALL)
                                    if obj_match:
                                        json_data = json.loads(obj_match.group(0))
                                    else:
                                        raise json.JSONDecodeError("No JSON found", response_text, 0)

                            validated = response_model.model_validate(json_data)
                            return validated

                        except Exception as e:
                            logger.warning(f"❌ Gemini {model_name} validation error (attempt {attempt + 1}/{max_retries}):")
                            logger.warning(f"   Full error: {str(e)}")
                            if attempt == max_retries - 1:
                                logger.error(f"Failed to validate after {max_retries} attempts with Gemini {model_name}")
                                logger.error(f"   Final error details: {str(e)}")
                                return None
                            continue

                return None

            return None

        except requests.exceptions.Timeout:
            logger.warning(f"⏱️  Gemini API timeout for {model_name} (30s)")
            return None
        except requests.exceptions.HTTPError as e:
            logger.warning(f"❌ Gemini API HTTP error for {model_name}:")
            logger.warning(f"   Status: {e.response.status_code if hasattr(e, 'response') else 'unknown'}")
            logger.warning(f"   Full error: {str(e)}")
            return None
        except requests.exceptions.RequestException as e:
            logger.warning(f"❌ Gemini API request error for {model_name}: {str(e)}")
            return None
        except Exception as e:
            logger.error(f"❌ Unexpected error with Gemini {model_name}: {str(e)}")
            return None

    def _call_cerebras_with_instructor(
        self,
        prompt: str,
        response_model: Type[T],
        model_name: str,
        section_id: Optional[str] = None,
        max_retries: int = 3
    ) -> Optional[T]:
        """Call Cerebras API with structured outputs."""
        if not CEREBRAS_API_KEY:
            return None

        # Log API call with worker info
        import threading
        worker_id = threading.current_thread().name
        logger.info(f"🔵 [{worker_id}] Calling Cerebras API: {model_name}")

        try:
            client = Cerebras(api_key=CEREBRAS_API_KEY)

            schema_json = response_model.model_json_schema()
            schema_str = str(schema_json)

            structured_prompt = f"""{prompt}

IMPORTANT: Respond with VALID JSON ONLY (no markdown, no explanations) that matches this exact schema:
{schema_str}

Return only the JSON object, nothing else."""

            for attempt in range(max_retries):
                try:
                    chat_completion = client.chat.completions.create(
                        messages=[
                            {
                                "role": "user",
                                "content": structured_prompt,
                            }
                        ],
                        model=model_name,
                        temperature=0.1,
                        max_tokens=30000
                    )

                    response_text = chat_completion.choices[0].message.content

                    try:
                        import re
                        import json

                        try:
                            json_data = json.loads(response_text.strip())
                        except json.JSONDecodeError:
                            json_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', response_text, re.DOTALL)
                            if json_match:
                                json_data = json.loads(json_match.group(1))
                            else:
                                obj_match = re.search(r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}', response_text, re.DOTALL)
                                if obj_match:
                                    json_data = json.loads(obj_match.group(0))
                                else:
                                    raise json.JSONDecodeError("No JSON found", response_text, 0)

                        validated = response_model.model_validate(json_data)
                        return validated

                    except Exception as e:
                        section_info = f" for section {section_id}" if section_id else ""
                        logger.warning(f"❌ Cerebras {model_name} validation error{section_info} (attempt {attempt + 1}/{max_retries}):")
                        logger.warning(f"   Error: {str(e)}")

                        # Log the actual LLM response for debugging
                        if 'response_text' in locals():
                            response_preview = response_text[:500] + "..." if len(response_text) > 500 else response_text
                            logger.warning(f"   LLM Response (first 500 chars): {response_preview}")

                        # Log what was parsed vs what was expected
                        if 'json_data' in locals() and isinstance(json_data, dict):
                            expected_fields = list(response_model.model_fields.keys())
                            received_fields = list(json_data.keys())
                            missing_fields = [f for f in expected_fields if f not in received_fields]
                            extra_fields = [f for f in received_fields if f not in expected_fields]

                            if missing_fields:
                                logger.warning(f"   Missing required fields: {missing_fields}")
                            if extra_fields:
                                logger.warning(f"   Extra fields (not in model): {extra_fields}")
                            logger.warning(f"   Received fields: {received_fields}")

                        if attempt == max_retries - 1:
                            logger.error(f"Failed to validate after {max_retries} attempts with Cerebras {model_name}")
                            return None
                        continue

                except Exception as api_error:
                    # Check if it's a rate limit error
                    error_str = str(api_error)
                    if "429" in error_str or "rate" in error_str.lower():
                        logger.debug(f"Cerebras rate limited for {model_name}")
                        return None

                    # For other errors, log and retry
                    if attempt == max_retries - 1:
                        logger.warning(f"❌ Cerebras API error for {model_name}: {str(api_error)}")
                        return None
                    continue

            return None

        except Exception as e:
            logger.error(f"❌ Unexpected error with Cerebras {model_name}: {str(e)}")
            return None

    def _call_groq_with_instructor(
        self,
        prompt: str,
        response_model: Type[T],
        model_name: str,
        section_id: Optional[str] = None,
        max_retries: int = 3
    ) -> Optional[T]:
        """Call Groq API with structured outputs."""
        if not GROQ_API_KEY:
            return None

        # Log API call with worker info
        import threading
        worker_id = threading.current_thread().name
        logger.info(f"🔵 [{worker_id}] Calling Groq API: {model_name}")

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

                if response.status_code == 429:
                    logger.debug(f"Groq rate limited for {model_name}")
                    return None

                response.raise_for_status()
                data = response.json()

                response_text = data.get("choices", [{}])[0].get("message", {}).get("content", "")

                try:
                    import re
                    import json

                    try:
                        json_data = json.loads(response_text.strip())
                    except json.JSONDecodeError:
                        json_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', response_text, re.DOTALL)
                        if json_match:
                            json_data = json.loads(json_match.group(1))
                        else:
                            obj_match = re.search(r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}', response_text, re.DOTALL)
                            if obj_match:
                                json_data = json.loads(obj_match.group(0))
                            else:
                                raise json.JSONDecodeError("No JSON found", response_text, 0)

                    validated = response_model.model_validate(json_data)
                    return validated

                except Exception as e:
                    section_info = f" for section {section_id}" if section_id else ""
                    logger.warning(f"❌ Groq {model_name} validation error{section_info} (attempt {attempt + 1}/{max_retries}):")
                    logger.warning(f"   Error: {str(e)}")

                    # Log the actual LLM response for debugging
                    if 'response_text' in locals():
                        response_preview = response_text[:500] + "..." if len(response_text) > 500 else response_text
                        logger.warning(f"   LLM Response (first 500 chars): {response_preview}")

                    # Log what was parsed vs what was expected
                    if 'json_data' in locals() and isinstance(json_data, dict):
                        expected_fields = list(response_model.model_fields.keys())
                        received_fields = list(json_data.keys())
                        missing_fields = [f for f in expected_fields if f not in received_fields]
                        extra_fields = [f for f in received_fields if f not in expected_fields]

                        if missing_fields:
                            logger.warning(f"   Missing required fields: {missing_fields}")
                        if extra_fields:
                            logger.warning(f"   Extra fields (not in model): {extra_fields}")
                        logger.warning(f"   Received fields: {received_fields}")

                    if attempt == max_retries - 1:
                        logger.error(f"Failed to validate after {max_retries} attempts with Groq {model_name}{section_info}")
                        return None
                    continue

            return None

        except requests.exceptions.Timeout:
            logger.warning(f"⏱️  Groq API timeout for {model_name} (30s)")
            return None
        except requests.exceptions.HTTPError as e:
            logger.warning(f"❌ Groq API HTTP error for {model_name}:")
            logger.warning(f"   Status: {e.response.status_code if hasattr(e, 'response') else 'unknown'}")
            logger.warning(f"   Full error: {str(e)}")
            return None
        except requests.exceptions.RequestException as e:
            logger.warning(f"❌ Groq API request error for {model_name}: {str(e)}")
            return None
        except Exception as e:
            logger.error(f"❌ Unexpected error with Groq {model_name}: {str(e)}")
            return None

    def _call_openrouter_with_instructor(
        self,
        prompt: str,
        response_model: Type[T],
        model_name: str,
        section_id: Optional[str] = None,
        max_retries: int = 3
    ) -> Optional[T]:
        """Call OpenRouter API with structured outputs."""
        if not OPENROUTER_API_KEY:
            return None

        # Log API call with worker info
        import threading
        worker_id = threading.current_thread().name
        logger.info(f"🔵 [{worker_id}] Calling OpenRouter API: {model_name}")

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
                        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
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
                    return None

                response.raise_for_status()
                data = response.json()

                response_text = data.get("choices", [{}])[0].get("message", {}).get("content", "")

                try:
                    import re
                    import json

                    try:
                        json_data = json.loads(response_text.strip())
                    except json.JSONDecodeError:
                        json_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', response_text, re.DOTALL)
                        if json_match:
                            json_data = json.loads(json_match.group(1))
                        else:
                            obj_match = re.search(r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}', response_text, re.DOTALL)
                            if obj_match:
                                json_data = json.loads(obj_match.group(0))
                            else:
                                raise json.JSONDecodeError("No JSON found", response_text, 0)

                    validated = response_model.model_validate(json_data)
                    return validated

                except Exception as e:
                    section_info = f" for section {section_id}" if section_id else ""
                    logger.warning(f"❌ OpenRouter {model_name} validation error{section_info} (attempt {attempt + 1}/{max_retries}):")
                    logger.warning(f"   Error: {str(e)}")

                    # Log the actual LLM response for debugging
                    if 'response_text' in locals():
                        response_preview = response_text[:500] + "..." if len(response_text) > 500 else response_text
                        logger.warning(f"   LLM Response (first 500 chars): {response_preview}")

                    # Log what was parsed vs what was expected
                    if 'json_data' in locals() and isinstance(json_data, dict):
                        expected_fields = list(response_model.model_fields.keys())
                        received_fields = list(json_data.keys())
                        missing_fields = [f for f in expected_fields if f not in received_fields]
                        extra_fields = [f for f in received_fields if f not in expected_fields]

                        if missing_fields:
                            logger.warning(f"   Missing required fields: {missing_fields}")
                        if extra_fields:
                            logger.warning(f"   Extra fields (not in model): {extra_fields}")
                        logger.warning(f"   Received fields: {received_fields}")

                    if attempt == max_retries - 1:
                        logger.error(f"Failed to validate after {max_retries} attempts with OpenRouter {model_name}")
                        return None
                    continue

            return None

        except requests.exceptions.Timeout:
            logger.warning(f"⏱️  OpenRouter API timeout for {model_name} (30s)")
            return None
        except requests.exceptions.HTTPError as e:
            logger.warning(f"❌ OpenRouter API HTTP error for {model_name}:")
            logger.warning(f"   Status: {e.response.status_code if hasattr(e, 'response') else 'unknown'}")
            logger.warning(f"   Full error: {str(e)}")
            if hasattr(e, 'response') and e.response.text:
                logger.warning(f"   Response body: {e.response.text[:500]}")
            return None
        except requests.exceptions.RequestException as e:
            logger.warning(f"❌ OpenRouter API request error for {model_name}: {str(e)}")
            return None
        except Exception as e:
            logger.error(f"❌ Unexpected error with OpenRouter {model_name}: {str(e)}")
            return None

    def _repair_json_structure(self, json_data: Any, response_model: Type[T]) -> Any:
        """Heuristically repair JSON structure to match response model."""
        if isinstance(json_data, list):
            fields = response_model.model_fields
            if len(fields) == 1:
                field_name = next(iter(fields))
                logger.debug(f"Repairing JSON: wrapping list in '{field_name}'")
                return {field_name: json_data}
        return json_data

    def _call_ollama_with_instructor(
        self,
        prompt: str,
        response_model: Type[T],
        model_name: str = OLLAMA_MODEL,
        section_id: Optional[str] = None,
        max_retries: int = 3
    ) -> Optional[T]:
        """Call Ollama API with validated responses."""
        # Log API call with worker info
        import threading
        worker_id = threading.current_thread().name
        logger.info(f"🔵 [{worker_id}] Calling Ollama API: {model_name}")

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

                try:
                    import re
                    import json

                    try:
                        json_data = json.loads(response_text.strip())
                    except json.JSONDecodeError:
                        json_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', response_text, re.DOTALL)
                        if json_match:
                            json_data = json.loads(json_match.group(1))
                        else:
                            obj_match = re.search(r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}', response_text, re.DOTALL)
                            if obj_match:
                                json_data = json.loads(obj_match.group(0))
                            else:
                                list_match = re.search(r'\[.*\]', response_text, re.DOTALL)
                                if list_match:
                                    json_data = json.loads(list_match.group(0))
                                else:
                                    raise json.JSONDecodeError("No JSON found", response_text, 0)

                    json_data = self._repair_json_structure(json_data, response_model)
                    validated = response_model.model_validate(json_data)
                    return validated

                except Exception as e:
                    section_info = f" for section {section_id}" if section_id else ""
                    logger.warning(f"❌ Ollama validation error{section_info} (attempt {attempt + 1}/{max_retries}):")
                    logger.warning(f"   Error: {str(e)}")

                    # Log the actual LLM response for debugging
                    if 'response_text' in locals():
                        response_preview = response_text[:500] + "..." if len(response_text) > 500 else response_text
                        logger.warning(f"   LLM Response (first 500 chars): {response_preview}")

                    # Log what was parsed vs what was expected
                    if 'json_data' in locals() and isinstance(json_data, dict):
                        expected_fields = list(response_model.model_fields.keys())
                        received_fields = list(json_data.keys())
                        missing_fields = [f for f in expected_fields if f not in received_fields]
                        extra_fields = [f for f in received_fields if f not in expected_fields]

                        if missing_fields:
                            logger.warning(f"   Missing required fields: {missing_fields}")
                        if extra_fields:
                            logger.warning(f"   Extra fields (not in model): {extra_fields}")
                        logger.warning(f"   Received fields: {received_fields}")

                    if attempt == max_retries - 1:
                        logger.error(f"Failed to validate after {max_retries} attempts with Ollama")
                        return None
                    continue

            return None

        except requests.exceptions.Timeout:
            logger.warning(f"⏱️  Ollama API timeout (90s)")
            return None
        except requests.exceptions.HTTPError as e:
            logger.warning(f"❌ Ollama API HTTP error:")
            logger.warning(f"   Status: {e.response.status_code if hasattr(e, 'response') else 'unknown'}")
            logger.warning(f"   Full error: {str(e)}")
            return None
        except requests.exceptions.RequestException as e:
            logger.warning(f"❌ Ollama API request error: {str(e)}")
            return None
        except Exception as e:
            logger.error(f"❌ Unexpected error with Ollama: {str(e)}")
            return None

    def generate(
        self,
        prompt: str,
        response_model: Type[T],
        section_id: Optional[str] = None
    ) -> Optional[LLMResponse]:
        """
        Generate structured output using error-driven cascade.

        Args:
            prompt: The prompt to send to the LLM
            response_model: Pydantic model class for validation
            section_id: Optional section ID for logging

        Returns:
            LLMResponse with validated data and model_used, or None if all models failed
        """
        # Get worker ID from environment (set by ThreadPoolExecutor)
        import threading
        worker_id = threading.current_thread().name

        # Get next model to try from cascade
        model_config = self.cascade.get_next_model()

        if not model_config:
            logger.error(f"[Worker {worker_id}] No models available!")
            return None

        model_name = model_config["name"]
        tier = model_config["tier"]

        # Log model switch with worker ID
        self._log_model_switch(model_name, f"[Worker {worker_id}] Cascade selected {tier} tier")

        # Try the model
        result = None
        error_msg = ""

        try:
            logger.debug(f"[Worker {worker_id}] Trying {tier}:{model_name} for {section_id or 'unknown'}")

            if tier == "vertex":
                result = self._call_vertex_with_instructor(prompt, response_model, model_name, section_id)
            elif tier == "gemini":
                result = self._call_gemini_with_instructor(prompt, response_model, model_name, section_id)
            elif tier == "cerebras":
                result = self._call_cerebras_with_instructor(prompt, response_model, model_name, section_id)
            elif tier == "groq":
                result = self._call_groq_with_instructor(prompt, response_model, model_name, section_id)
            elif tier == "openrouter":
                result = self._call_openrouter_with_instructor(prompt, response_model, model_name, section_id)
            elif tier == "ollama":
                result = self._call_ollama_with_instructor(prompt, response_model, model_name, section_id)

            if result:
                # Success!
                self.cascade.mark_success(model_config)

                # Update statistics
                self.stats['model_call_counts'][model_name] = self.stats['model_call_counts'].get(model_name, 0) + 1
                self.stats['model_success_counts'][model_name] = self.stats['model_success_counts'].get(model_name, 0) + 1

                logger.debug(f"✓ {model_name} succeeded" + (f" for {section_id}" if section_id else ""))

                return LLMResponse(data=result, model_used=model_name)
            else:
                error_msg = "Model returned None"

        except Exception as e:
            error_msg = str(e)
            logger.debug(f"Exception with {model_name}: {error_msg}")

        # Model failed - mark it and try again with next model
        self.cascade.mark_failure(model_config, error_msg)
        self.stats['model_failure_counts'][model_name] = self.stats['model_failure_counts'].get(model_name, 0) + 1

        # Recursively try next model
        return self.generate(prompt, response_model, section_id)

    def get_stats_summary(self) -> str:
        """Generate a formatted summary of LLM usage statistics."""
        total_calls = sum(self.stats['model_call_counts'].values())
        if total_calls == 0:
            return "No LLM calls made yet."

        session_time = time.time() - self.stats['session_start_time']
        session_minutes = int(session_time // 60)
        session_seconds = int(session_time % 60)

        # Get cascade status
        cascade_status = self.cascade.get_status()

        # Sort models by call count
        sorted_models = sorted(
            self.stats['model_call_counts'].items(),
            key=lambda x: x[1],
            reverse=True
        )

        # Build summary
        lines = []
        lines.append("")
        lines.append("=" * 70)
        lines.append("ERROR-DRIVEN CASCADE - LLM USAGE STATISTICS")
        lines.append("=" * 70)
        lines.append(f"Strategy: Error-driven with FIFO retry after {RETRY_AFTER_ATTEMPTS} attempts")
        lines.append(f"Session Duration: {session_minutes}m {session_seconds}s")
        lines.append(f"Total Attempts: {cascade_status['total_attempts']}")
        lines.append("")

        # Cascade status
        lines.append("Current Cascade Status:")
        lines.append(f"  Active Models: {', '.join(cascade_status['active_models']) if cascade_status['active_models'] else 'None'}")

        if cascade_status['failed_queue']:
            lines.append(f"  Failed Queue ({len(cascade_status['failed_queue'])} models):")
            for model_name, failed_at, num_failures in cascade_status['failed_queue']:
                attempts_since = cascade_status['total_attempts'] - failed_at
                retry_in = max(0, RETRY_AFTER_ATTEMPTS - attempts_since)
                lines.append(f"    - {model_name}: {num_failures} failures, retry in {retry_in} attempts")
        else:
            lines.append(f"  Failed Queue: Empty")

        if cascade_status['retry_in_progress']:
            lines.append(f"  Retry In Progress: {cascade_status['retry_in_progress']}")

        lines.append("")

        # Model usage
        lines.append("Model Usage:")
        for model_name, count in sorted_models:
            percentage = (count / total_calls) * 100
            successes = self.stats['model_success_counts'].get(model_name, 0)
            failures = self.stats['model_failure_counts'].get(model_name, 0)
            total_attempts = successes + failures
            success_rate = (successes / total_attempts * 100) if total_attempts > 0 else 0
            lines.append(f"  {model_name}:")
            lines.append(f"    ├─ Calls: {count} ({percentage:.1f}%)")
            lines.append(f"    └─ Success Rate: {success_rate:.1f}% ({successes}/{total_attempts} attempts)")
        lines.append(f"  Total Successful Calls: {total_calls}")
        lines.append("")

        # Tier switches
        if self.stats['tier_switches']:
            lines.append(f"Model Switches: {len(self.stats['tier_switches'])} total")
            lines.append("")

        lines.append("=" * 70)

        return "\n".join(lines)
