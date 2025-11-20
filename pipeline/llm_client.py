#!/usr/bin/env python3
"""
Unified LLM client with sequential model cascade.

This module provides a single interface for calling LLMs with Pydantic validation.
Models are tried sequentially (one at a time) for better API stability.

Cascade Strategies:
- "simple": Gemini → Ollama (preserves Groq/OpenRouter rate limits)
- "extended": Gemini → Groq → OpenRouter → Ollama (maximum resilience)
"""

import os
import time
import logging
from typing import Optional, Type, TypeVar

from dotenv import load_dotenv
from pydantic import BaseModel

from common import setup_logging
from llm.types import LLMResponse
from llm.rate_limiter import RateLimiter
from llm.providers.gemini import GeminiProvider
from llm.providers.groq import GroqProvider
from llm.providers.openrouter import OpenRouterProvider
from llm.providers.ollama import OllamaProvider

# Load environment variables
load_dotenv()

logger = setup_logging(__name__, level=logging.DEBUG)

RESET = "\033[0m"
BOLD = "\033[1m"
DIM = "\033[2m"
GREEN = "\033[32m"
RED = "\033[31m"
YELLOW = "\033[33m"
CYAN = "\033[36m"
ORANGE = "\033[38;5;208m"
BLUE = "\033[34m"

T = TypeVar('T', bound=BaseModel)

# API Configuration
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

# Cascade strategy configuration
CASCADE_STRATEGY = os.getenv("LLM_CASCADE_STRATEGY", "extended")

# Gemini lineup (matching Google AI public catalog as of 2025-02)
GEMINI_MODELS = [
    {"name": "gemini-2.5-flash-lite", "rpm": 30, "rpd": 1500},
]

GROQ_MODELS = [
    # OpenAI GPT OSS models (prioritized)
    {"name": "openai/gpt-oss-120b", "rpm": 30, "rpd": 1000, "tpm": 250000, "max_output_tokens": 30000},
    {"name": "openai/gpt-oss-20b", "rpm": 30, "rpd": 1000, "tpm": 250000, "max_output_tokens": 30000},

    # Groq Compound models (8192 max_tokens limit)
    {"name": "groq/compound", "rpm": 200, "rpd": 10000, "tpm": 200000, "max_output_tokens": 8192},
    {"name": "groq/compound-mini", "rpm": 200, "rpd": 10000, "tpm": 200000, "max_output_tokens": 8192},

    # Llama models
    {"name": "llama-3.3-70b-versatile", "rpm": 30, "rpd": 1500, "tpm": 20000, "max_output_tokens": 30000},
    {"name": "llama-3.1-8b-instant", "rpm": 30, "rpd": 14400, "tpm": 30000, "max_output_tokens": 30000},
]

OPENROUTER_MODELS = [
    {"name": "qwen/qwen3-coder:free", "rpm": 30, "rpd": 1000, "tpm": 262000},
    {"name": "nousresearch/hermes-3-llama-3.1-405b:free", "rpm": 30, "rpd": 1000, "tpm": 131072},
    {"name": "deepseek/deepseek-r1:free", "rpm": 30, "rpd": 1000, "tpm": 163840},
    {"name": "deepseek/deepseek-r1-0528:free", "rpm": 30, "rpd": 1000, "tpm": 163840},
    {"name": "deepseek/deepseek-r1-0528-qwen3-8b:free", "rpm": 30, "rpd": 1000, "tpm": 32768},
    {"name": "deepseek/deepseek-chat-v3-0324:free", "rpm": 30, "rpd": 1000, "tpm": 163840},
    {"name": "qwen/qwen3-235b-a22b:free", "rpm": 30, "rpd": 1000, "tpm": 40960},
    {"name": "meta-llama/llama-3.3-70b-instruct:free", "rpm": 30, "rpd": 1000, "tpm": 131072},
    {"name": "qwen/qwen-2.5-72b-instruct:free", "rpm": 30, "rpd": 1000, "tpm": 32768},
    {"name": "google/gemma-3-27b-it:free", "rpm": 30, "rpd": 1000, "tpm": 131072},
    {"name": "google/gemma-3-12b-it:free", "rpm": 30, "rpd": 1000, "tpm": 32768},
    {"name": "mistralai/mistral-small-3.2-24b-instruct:free", "rpm": 30, "rpd": 1000, "tpm": 131072},
]

OLLAMA_HOST = "http://localhost:11434"
OLLAMA_MODEL = "phi4-mini"

class LLMClient:
    """
    Unified LLM client with Instructor integration and rate-limited cascade.
    Models are tried sequentially (one at a time) for better API stability.
    """

    def __init__(self, cascade_strategy: Optional[str] = None):
        self.rate_limiter = RateLimiter()
        self.cascade_strategy = (cascade_strategy or CASCADE_STRATEGY).lower()

        if self.cascade_strategy not in ["simple", "extended"]:
            logger.warning(f"Invalid cascade strategy '{self.cascade_strategy}', defaulting to 'simple'")
            self.cascade_strategy = "simple"

        # Initialize providers
        self.providers = {
            "gemini": GeminiProvider(self.rate_limiter),
            "groq": GroqProvider(self.rate_limiter),
            "openrouter": OpenRouterProvider(self.rate_limiter),
            "ollama": OllamaProvider(self.rate_limiter, OLLAMA_HOST)
        }

        # Initialize stats
        self.stats = {
            'cascade_strategy': self.cascade_strategy,
            'session_start_time': time.time(),
            'current_model': None,
            'current_model_calls': 0,
            'current_model_start_time': None,
            'last_gemini_call_time': 0,
            'last_gemini_attempt_time': 0,
            'last_groq_attempt_time': 0,
            'last_openrouter_attempt_time': 0,
            'last_gemini_fail_time': 0,
            'using_fallback': False,
            'model_call_counts': {},
            'tier_switches': [],
            'time_on_gemini': 0,
            'time_on_groq': 0,
            'time_on_openrouter': 0,
            'time_on_ollama': 0,
            'last_tier_switch_time': time.time()
        }

        strategy_desc = {
            'simple': 'Gemini (7) → Ollama (1)',
            'extended': 'Gemini (7) → Groq (6) → OpenRouter (12 free) → Ollama (1)'
        }
        logger.info(f"{BOLD}{CYAN}LLM Client initialized with '{self.cascade_strategy}' cascade strategy:{RESET}")
        logger.info(f"{DIM}  {strategy_desc[self.cascade_strategy]}{RESET}")

    def _log_model_switch(self, new_model: str, reason: str = "Rate limited"):
        current_time = time.time()
        previous_model = self.stats['current_model']

        if previous_model == new_model:
            return

        if previous_model:
            time_on_current = current_time - self.stats['last_tier_switch_time']
            if any(previous_model in m['name'] for m in GEMINI_MODELS):
                self.stats['time_on_gemini'] += time_on_current
            elif any(previous_model in m['name'] for m in GROQ_MODELS):
                self.stats['time_on_groq'] += time_on_current
            elif any(previous_model in m['name'] for m in OPENROUTER_MODELS):
                self.stats['time_on_openrouter'] += time_on_current
            elif previous_model == OLLAMA_MODEL:
                self.stats['time_on_ollama'] += time_on_current

        if previous_model:
            time_on_prev = current_time - self.stats['current_model_start_time']
            minutes = int(time_on_prev // 60)
            seconds = int(time_on_prev % 60)
            calls = self.stats['current_model_calls']

            logger.info(f"{YELLOW}⟳ Model Switch:{RESET} {DIM}{previous_model}{RESET} → {ORANGE}{new_model}{RESET}")
            logger.info(f"{DIM}  ├─ Previous model: {calls} calls in {minutes}m {seconds}s{RESET}")
            logger.info(f"{DIM}  └─ Reason: {reason}{RESET}")

            self.stats['tier_switches'].append({
                'timestamp': current_time,
                'from': previous_model,
                'to': new_model,
                'reason': reason
            })

        self.stats['current_model'] = new_model
        self.stats['current_model_calls'] = 0
        self.stats['current_model_start_time'] = current_time
        self.stats['last_tier_switch_time'] = current_time

    def generate(
        self,
        prompt: str,
        response_model: Type[T],
        section_id: Optional[str] = None
    ) -> Optional[LLMResponse]:

        # 1. Gemini Tier (sequential)
        self.stats['last_gemini_attempt_time'] = time.time()
        for model_config in GEMINI_MODELS:
            model_name = model_config["name"]
            if self.rate_limiter.wait_if_needed(model_config, block=False):
                self._log_model_switch(model_name, "Initial" if not self.stats['current_model'] else "Rate limited")
                self.stats['last_gemini_call_time'] = time.time()

                result, error = self.providers["gemini"].generate(prompt, response_model, model_name)

                if result:
                    self.rate_limiter.record_call(model_config)
                    logger.debug(f"{GREEN}Successfully used Gemini {model_name}{RESET}")
                    self.stats['current_model_calls'] += 1
                    self.stats['model_call_counts'][model_name] = \
                        self.stats['model_call_counts'].get(model_name, 0) + 1
                    return LLMResponse(data=result, model_used=model_name)
                else:
                    logger.info(f"{RED}✗ Gemini {model_name} failed{RESET}: {error or 'Unknown error'}")

        # 3. Groq Tier (Extended, sequential)
        if self.cascade_strategy == "extended":
            self.stats['last_groq_attempt_time'] = time.time()
            for i, model_config in enumerate(GROQ_MODELS):
                model_name = model_config["name"]
                if self.rate_limiter.wait_if_needed(model_config, block=False):
                    self._log_model_switch(model_name, "Gemini exhausted")

                    max_output_tokens = model_config.get("max_output_tokens", 30000)
                    result, error = self.providers["groq"].generate(
                        prompt, response_model, model_name, max_output_tokens=max_output_tokens
                    )

                    if result:
                        self.rate_limiter.record_call(model_config)
                        logger.debug(f"{GREEN}Successfully used Groq {model_name}{RESET}")
                        self.stats['current_model_calls'] += 1
                        self.stats['model_call_counts'][model_name] = \
                            self.stats['model_call_counts'].get(model_name, 0) + 1
                        return LLMResponse(data=result, model_used=model_name)
                    else:
                        logger.info(f"{RED}✗ Groq {model_name} failed{RESET}: {error or 'Unknown error'}")
                        if i < len(GROQ_MODELS) - 1:
                            time.sleep(1)

        # 4. OpenRouter Tier (Extended, sequential)
        if self.cascade_strategy == "extended":
            self.stats['last_openrouter_attempt_time'] = time.time()
            for i, model_config in enumerate(OPENROUTER_MODELS):
                model_name = model_config["name"]
                if self.rate_limiter.wait_if_needed(model_config, block=False):
                    self._log_model_switch(model_name, "Groq exhausted")

                    result, error = self.providers["openrouter"].generate(prompt, response_model, model_name)

                    if result:
                        self.rate_limiter.record_call(model_config)
                        logger.debug(f"{GREEN}Successfully used OpenRouter {model_name}{RESET}")
                        self.stats['current_model_calls'] += 1
                        self.stats['model_call_counts'][model_name] = \
                            self.stats['model_call_counts'].get(model_name, 0) + 1
                        return LLMResponse(data=result, model_used=model_name)
                    else:
                        logger.info(f"{RED}✗ OpenRouter {model_name} failed{RESET}: {error or 'Unknown error'}")
                        if i < len(OPENROUTER_MODELS) - 1:
                            time.sleep(1)

        # 5. Ollama Fallback
        self.stats['using_fallback'] = True
        self._log_model_switch(OLLAMA_MODEL, "All cloud models exhausted")
        
        result, error = self.providers["ollama"].generate(prompt, response_model, OLLAMA_MODEL)
        
        if result:
            self.stats['current_model_calls'] += 1
            self.stats['model_call_counts'][OLLAMA_MODEL] = \
                self.stats['model_call_counts'].get(OLLAMA_MODEL, 0) + 1
            return LLMResponse(data=result, model_used=OLLAMA_MODEL)
        else:
            logger.error(f"{RED}CRITICAL: All models including Ollama failed{RESET}. Last error: {error}")
            return None

    def get_stats_summary(self) -> str:
        """Generate a human-readable summary of session statistics."""
        duration = time.time() - self.stats['session_start_time']
        minutes = int(duration // 60)
        seconds = int(duration % 60)
        
        total_calls = sum(self.stats['model_call_counts'].values())
        
        summary = [
            "\n📊 LLM Client Session Summary",
            f"============================",
            f"⏱️  Duration: {minutes}m {seconds}s",
            f"🔄 Total Calls: {total_calls}",
            f"📈 Strategy: {self.cascade_strategy} (sequential)",
            "\n🏆 Model Usage:",
        ]
        
        sorted_models = sorted(
            self.stats['model_call_counts'].items(), 
            key=lambda x: x[1], 
            reverse=True
        )
        
        for model, count in sorted_models:
            percentage = (count / total_calls * 100) if total_calls > 0 else 0
            summary.append(f"  • {model}: {count} ({percentage:.1f}%)")
            
        if self.stats['tier_switches']:
            summary.append(f"\n🔀 Tier Switches: {len(self.stats['tier_switches'])}")
            
        return "\n".join(summary)
