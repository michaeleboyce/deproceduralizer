#!/usr/bin/env python3
"""
Factory for creating LLM clients with different cascade strategies.

This module provides a unified interface for choosing between:
- Rate-limited cascade (preemptive rate limit checking)
- Error-driven cascade (reactive error handling with FIFO retry)

Usage:
    from pipeline.llm_factory import create_llm_client

    # Via code
    client = create_llm_client(strategy="error_driven")

    # Via command line argument
    parser.add_argument("--cascade", choices=["rate_limited", "error_driven"],
                       default="error_driven")
    client = create_llm_client(strategy=args.cascade)
"""

import os
from typing import Union
from dotenv import load_dotenv

from common import setup_logging

load_dotenv()
logger = setup_logging(__name__)


def create_llm_client(strategy: str = None, parallel_execution: bool = False) -> Union['LLMClient', 'ErrorDrivenLLMClient']:
    """
    Create an LLM client with the specified cascade strategy.

    Args:
        strategy: One of "rate_limited", "error_driven", "extended" (alias for rate_limited), or "simple" (alias for rate_limited)
                 If None, uses LLM_CASCADE_STRATEGY env var or intelligent defaults:
                 - If PIPELINE_WORKERS > 1: defaults to "rate_limited" (better for parallel processing)
                 - Otherwise: defaults to "error_driven" (better for sequential processing)
        parallel_execution: Enable parallel execution within tiers (only for rate_limited strategy)

    Returns:
        LLMClient or ErrorDrivenLLMClient instance

    Raises:
        ValueError: If strategy is not valid
    """
    # Determine strategy
    if strategy is None:
        strategy = os.getenv("LLM_CASCADE_STRATEGY", None)

        if strategy is None:
            # Intelligent default based on parallel workers
            workers = int(os.getenv("PIPELINE_WORKERS", "1"))
            if workers > 1:
                strategy = "rate_limited"
                logger.info(f"🔧 Auto-selecting rate_limited strategy (PIPELINE_WORKERS={workers})")
            else:
                strategy = "error_driven"

    strategy = strategy.lower()

    # Handle old parameter names for backward compatibility
    if strategy == "extended":
        logger.info("📝 Converting 'extended' to 'rate_limited' (backward compatibility)")
        strategy = "rate_limited"
    elif strategy == "simple":
        logger.info("📝 Converting 'simple' to 'rate_limited' (backward compatibility)")
        strategy = "rate_limited"

    if strategy == "rate_limited":
        from llm_client import LLMClient

        # Check if user wants extended or simple rate-limited cascade
        rate_limited_mode = os.getenv("LLM_CASCADE_MODE", "extended")

        # Use parameter value or check env var
        parallel = parallel_execution or (os.getenv("LLM_PARALLEL_EXECUTION", "false").lower() == "true")

        logger.info(f"🔧 Creating Rate-Limited LLM Client (mode: {rate_limited_mode}, parallel: {parallel})")
        return LLMClient(cascade_strategy=rate_limited_mode, parallel_execution=parallel)

    elif strategy == "error_driven":
        from llm_client_error_driven import ErrorDrivenLLMClient

        if parallel_execution:
            logger.warning("⚠️  Parallel execution not supported with error_driven strategy, ignoring parameter")

        logger.info(f"🔧 Creating Error-Driven LLM Client")
        return ErrorDrivenLLMClient()

    else:
        raise ValueError(
            f"Invalid cascade strategy: {strategy}. "
            f"Must be one of: 'rate_limited', 'error_driven' (also accepts legacy names: 'extended', 'simple')"
        )


def add_cascade_argument(parser):
    """
    Add cascade strategy argument to an ArgumentParser.

    Args:
        parser: argparse.ArgumentParser instance

    Example:
        parser = argparse.ArgumentParser()
        add_cascade_argument(parser)
        args = parser.parse_args()
        client = create_llm_client(strategy=args.cascade_strategy)
    """
    parser.add_argument(
        "--cascade-strategy",
        dest="cascade_strategy",
        choices=["rate_limited", "error_driven", "extended", "simple"],
        default=None,  # Will use env var or intelligent default in create_llm_client
        help=(
            "LLM cascade strategy: "
            "'rate_limited' (preemptive rate limit checking) or "
            "'error_driven' (reactive with FIFO retry). "
            "Legacy names: 'extended'/'simple' (both map to rate_limited). "
            "Default: Auto-selects based on PIPELINE_WORKERS (rate_limited if >1, else error_driven)"
        )
    )
