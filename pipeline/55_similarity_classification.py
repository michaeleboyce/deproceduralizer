#!/usr/bin/env python3
"""
Classify similarity relationships between DC Code sections using LLM analysis.

Uses Gemini 2.0 Flash (free tier) with fallback to Ollama phi3.5 to classify
why similar sections are related: duplicate, superseded, related, or conflicting.

Usage:
  python pipeline/55_similarity_classification.py \
    --similarities data/outputs/similarities_subset.ndjson \
    --sections data/outputs/sections_subset.ndjson \
    --out data/outputs/similarity_classifications_subset.ndjson
"""

import argparse
import json
import os
import pickle
import re
import requests
import time
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict
from tqdm import tqdm

from common import NDJSONReader, NDJSONWriter, setup_logging, validate_record, PIPELINE_VERSION

logger = setup_logging(__name__)

# API Configuration
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_MODELS = [
    "gemini-2.5-flash",
    "gemini-2.5-flash-lite",
    "gemini-2.0-flash",
    "gemini-2.0-flash-lite"
]

OLLAMA_HOST = "http://localhost:11434"
OLLAMA_MODEL = "phi3.5"

# Rate limiting for Gemini free tier
GEMINI_RPM_LIMIT = 15  # requests per minute
GEMINI_RPD_LIMIT = 1500  # requests per day
RPM_WINDOW = 60  # seconds

CHECKPOINT_FILE = Path("data/interim/similarity_classification.ckpt")
MAX_TEXT_LENGTH = 2000  # Truncate each section text


class RateLimiter:
    """Track API calls and enforce rate limits."""

    def __init__(self, rpm_limit: int, rpd_limit: int):
        self.rpm_limit = rpm_limit
        self.rpd_limit = rpd_limit
        self.minute_calls = []
        self.day_calls = 0
        self.day_start = datetime.utcnow().date()

    def wait_if_needed(self):
        """Sleep if we're approaching rate limits."""
        now = datetime.utcnow()

        # Reset day counter if new day
        if now.date() > self.day_start:
            self.day_calls = 0
            self.day_start = now.date()

        # Check daily limit
        if self.day_calls >= self.rpd_limit:
            logger.warning(f"Hit daily limit ({self.rpd_limit}), switching to Ollama for remaining requests")
            return False  # Signal to use fallback

        # Remove calls older than 1 minute
        cutoff = now.timestamp() - RPM_WINDOW
        self.minute_calls = [t for t in self.minute_calls if t > cutoff]

        # Check per-minute limit
        if len(self.minute_calls) >= self.rpm_limit:
            sleep_time = RPM_WINDOW - (now.timestamp() - self.minute_calls[0]) + 1
            logger.info(f"Rate limit approaching, sleeping {sleep_time:.1f}s")
            time.sleep(sleep_time)
            self.minute_calls = []

        return True  # Signal OK to use Gemini

    def record_call(self):
        """Record that an API call was made."""
        self.minute_calls.append(datetime.utcnow().timestamp())
        self.day_calls += 1


def parse_llm_json(response_text: str) -> Optional[dict]:
    """
    Robustly parse JSON from LLM response.

    LLMs sometimes wrap JSON in markdown or add explanations.
    Try multiple parsing strategies.
    """
    # Strategy 1: Direct JSON parse
    try:
        return json.loads(response_text.strip())
    except json.JSONDecodeError:
        pass

    # Strategy 2: Extract from ```json ... ``` markdown blocks
    json_block_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', response_text, re.DOTALL)
    if json_block_match:
        try:
            return json.loads(json_block_match.group(1))
        except json.JSONDecodeError:
            pass

    # Strategy 3: Find first {...} JSON object
    json_obj_match = re.search(r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}', response_text, re.DOTALL)
    if json_obj_match:
        try:
            return json.loads(json_obj_match.group(0))
        except json.JSONDecodeError:
            pass

    logger.error(f"Could not parse JSON from LLM response: {response_text[:200]}")
    return None


def classify_with_gemini(text_a: str, text_b: str, section_a_id: str, section_b_id: str, model: str) -> Optional[dict]:
    """
    Classify similarity relationship using Gemini API.

    Args:
        text_a: First section text
        text_b: Second section text
        section_a_id: First section ID
        section_b_id: Second section ID
        model: Gemini model name to use

    Returns:
        Dict with classification and explanation, or None if failed
    """
    if not GEMINI_API_KEY:
        return None

    prompt = f"""You are analyzing two similar DC Code sections to classify their relationship.

SECTION A ({section_a_id}):
{text_a}

SECTION B ({section_b_id}):
{text_b}

TASK: Classify the relationship between these sections into ONE of these categories:

1. **duplicate** - Nearly identical provisions that could be consolidated
2. **superseded** - One section appears to replace or update the other
3. **related** - Cover similar topics but serve different purposes
4. **conflicting** - Similar language but contradictory requirements

RESPOND WITH VALID JSON ONLY (no markdown, no explanations):
{{
  "classification": "duplicate|superseded|related|conflicting",
  "explanation": "2-3 sentence explanation of why this classification was chosen"
}}

GUIDELINES:
- Be specific about what makes them similar or different
- Note any procedural, substantive, or temporal relationships
- For "superseded", note evidence like effective dates or explicit replacements
- For "conflicting", note specific contradictions"""

    try:
        headers = {
            "Content-Type": "application/json"
        }

        payload = {
            "contents": [{
                "parts": [{
                    "text": prompt
                }]
            }],
            "generationConfig": {
                "temperature": 0.1,  # Low temperature for consistency
                "topP": 0.95,
                "topK": 40,
                "maxOutputTokens": 500
            }
        }

        gemini_api_url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
        response = requests.post(
            f"{gemini_api_url}?key={GEMINI_API_KEY}",
            headers=headers,
            json=payload,
            timeout=30
        )

        # Check for rate limiting
        if response.status_code == 429:
            logger.warning("Gemini rate limited (429), falling back to Ollama")
            return None

        response.raise_for_status()
        data = response.json()

        # Extract text from Gemini response format
        if "candidates" in data and len(data["candidates"]) > 0:
            candidate = data["candidates"][0]
            if "content" in candidate and "parts" in candidate["content"]:
                response_text = candidate["content"]["parts"][0].get("text", "")

                # Parse JSON from response
                parsed = parse_llm_json(response_text)

                if parsed and "classification" in parsed and "explanation" in parsed:
                    return parsed
                else:
                    logger.error(f"Invalid response format from Gemini for {section_a_id}-{section_b_id}")
                    return None

        logger.error(f"Unexpected Gemini response format: {data}")
        return None

    except requests.exceptions.Timeout:
        logger.error(f"Timeout calling Gemini API for {section_a_id}-{section_b_id}")
        return None
    except requests.exceptions.RequestException as e:
        logger.error(f"Error calling Gemini API: {e}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error with Gemini: {e}")
        return None


def classify_with_ollama(text_a: str, text_b: str, section_a_id: str, section_b_id: str, model: str = OLLAMA_MODEL) -> Optional[dict]:
    """
    Classify similarity relationship using Ollama models.

    Args:
        text_a: First section text
        text_b: Second section text
        section_a_id: First section ID
        section_b_id: Second section ID
        model: Ollama model name to use

    Fallback when Gemini is rate limited or fails.
    """
    prompt = f"""You are analyzing two similar DC Code sections to classify their relationship.

SECTION A ({section_a_id}):
{text_a}

SECTION B ({section_b_id}):
{text_b}

TASK: Classify the relationship between these sections into ONE of these categories:

1. **duplicate** - Nearly identical provisions that could be consolidated
2. **superseded** - One section appears to replace or update the other
3. **related** - Cover similar topics but serve different purposes
4. **conflicting** - Similar language but contradictory requirements

RESPOND WITH VALID JSON ONLY (no markdown, no explanations):
{{
  "classification": "duplicate|superseded|related|conflicting",
  "explanation": "2-3 sentence explanation of why this classification was chosen"
}}"""

    try:
        response = requests.post(
            f"{OLLAMA_HOST}/api/generate",
            json={
                "model": model,
                "prompt": prompt,
                "stream": False
            },
            timeout=90  # Ollama can be slow
        )
        response.raise_for_status()
        data = response.json()

        response_text = data.get("response", "")
        parsed = parse_llm_json(response_text)

        if parsed and "classification" in parsed and "explanation" in parsed:
            return parsed
        else:
            logger.error(f"Invalid response from Ollama for {section_a_id}-{section_b_id}")
            return None

    except requests.exceptions.Timeout:
        logger.error(f"Timeout calling Ollama for {section_a_id}-{section_b_id}")
        return None
    except requests.exceptions.RequestException as e:
        logger.error(f"Error calling Ollama API: {e}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error with Ollama: {e}")
        return None


def classify_similarity(
    text_a: str,
    text_b: str,
    section_a_id: str,
    section_b_id: str,
    rate_limiter: RateLimiter,
    stats: dict
) -> tuple[Optional[dict], str]:
    """
    Classify similarity using Gemini models with multiple fallbacks, then Ollama.

    Tries models in order: gemini-2.5-flash -> gemini-2.5-flash-lite ->
    gemini-2.0-flash -> gemini-2.0-flash-lite -> phi3.5

    Returns:
        (classification_dict, model_used)
    """
    # Try each Gemini model in sequence if rate limit allows
    if rate_limiter.wait_if_needed():
        for model in GEMINI_MODELS:
            result = classify_with_gemini(text_a, text_b, section_a_id, section_b_id, model)
            if result:
                rate_limiter.record_call()
                logger.debug(f"Successfully used {model} for {section_a_id}-{section_b_id}")
                return result, model
            else:
                # Log the failed attempt but continue to next model
                logger.debug(f"Failed with {model}, trying next model")

    # All Gemini models failed or rate limited, fallback to Ollama
    if not stats.get('fallback_to_ollama_logged'):
        logger.info("⚠ All Gemini models failed/unavailable, falling back to Ollama phi3.5")
        stats['fallback_to_ollama_logged'] = True

    result = classify_with_ollama(text_a, text_b, section_a_id, section_b_id, OLLAMA_MODEL)
    if result:
        return result, OLLAMA_MODEL

    return None, "failed"


def load_sections(sections_file: Path) -> Dict[str, str]:
    """
    Load all sections into memory for quick lookup.

    Returns:
        Dict mapping section_id -> text_plain
    """
    logger.info(f"Loading sections from {sections_file}")
    sections = {}

    reader = NDJSONReader(str(sections_file))
    for section in reader:
        section_id = section.get("id")
        text_plain = section.get("text_plain", "")

        if section_id and text_plain:
            # Truncate text to avoid token limits
            truncated = text_plain[:MAX_TEXT_LENGTH]
            sections[section_id] = truncated

    logger.info(f"Loaded {len(sections)} sections")
    return sections


def load_checkpoint() -> dict:
    """Load checkpoint if exists."""
    if CHECKPOINT_FILE.exists():
        logger.info(f"Loading checkpoint from {CHECKPOINT_FILE}")
        with open(CHECKPOINT_FILE, 'rb') as f:
            checkpoint = pickle.load(f)
            # Add model_usage dict if it doesn't exist (backwards compatibility)
            if "model_usage" not in checkpoint:
                checkpoint["model_usage"] = {}
            return checkpoint

    return {
        "processed_pairs": set(),  # Set of (section_a, section_b) tuples
        "results": [],             # List of classification records
        "model_usage": {}          # Dict mapping model name -> call count
    }


def save_checkpoint(checkpoint: dict):
    """Save checkpoint."""
    CHECKPOINT_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(CHECKPOINT_FILE, 'wb') as f:
        pickle.dump(checkpoint, f)
    logger.debug(f"Saved checkpoint: {len(checkpoint['processed_pairs'])} pairs processed")


def main():
    parser = argparse.ArgumentParser(
        description="Classify similarity relationships using LLM analysis"
    )
    parser.add_argument(
        "--similarities",
        required=True,
        help="Input NDJSON file with similarity pairs"
    )
    parser.add_argument(
        "--sections",
        required=True,
        help="Input NDJSON file with section texts"
    )
    parser.add_argument(
        "--out",
        required=True,
        help="Output NDJSON file (classifications)"
    )

    args = parser.parse_args()

    similarities_file = Path(args.similarities)
    sections_file = Path(args.sections)
    output_file = Path(args.out)

    if not similarities_file.exists():
        logger.error(f"Similarities file not found: {similarities_file}")
        return 1

    if not sections_file.exists():
        logger.error(f"Sections file not found: {sections_file}")
        return 1

    logger.info(f"Classifying similarities from {similarities_file}")
    logger.info(f"Pipeline version: {PIPELINE_VERSION}")

    # Clear model configuration logging
    if GEMINI_API_KEY:
        logger.info(f"✓ Gemini models configured with fallback chain:")
        for i, model in enumerate(GEMINI_MODELS):
            logger.info(f"  {i+1}. {model}")
        logger.info(f"  {len(GEMINI_MODELS)+1}. {OLLAMA_MODEL} (final fallback)")
        logger.info(f"  Rate limits: Gemini {GEMINI_RPM_LIMIT} RPM, {GEMINI_RPD_LIMIT} RPD")
    else:
        logger.warning(f"✗ Gemini API key not found - will use Ollama only")
        logger.info(f"  Fallback: {OLLAMA_MODEL}")
        logger.info(f"  Set GEMINI_API_KEY environment variable to enable Gemini")

    # Load sections into memory
    sections = load_sections(sections_file)

    # Load checkpoint
    checkpoint = load_checkpoint()

    # Initialize rate limiter
    rate_limiter = RateLimiter(GEMINI_RPM_LIMIT, GEMINI_RPD_LIMIT)

    # Statistics
    pairs_processed = 0
    failed_classifications = 0
    stats = {
        'fallback_to_ollama_logged': False
    }

    # Read similarity pairs
    reader = NDJSONReader(str(similarities_file))
    pairs_to_process = []

    for sim in reader:
        section_a = sim.get("section_a")
        section_b = sim.get("section_b")
        similarity = sim.get("similarity")

        if not section_a or not section_b or similarity is None:
            continue

        pairs_to_process.append({
            "section_a": section_a,
            "section_b": section_b,
            "similarity": similarity
        })

    total_pairs = len(pairs_to_process)
    logger.info(f"Found {total_pairs} similarity pairs to classify")

    # Process pairs with progress bar
    with NDJSONWriter(str(output_file)) as writer:
        for pair in tqdm(pairs_to_process, desc="Classifying pairs", unit="pair"):
            section_a = pair["section_a"]
            section_b = pair["section_b"]
            similarity = pair["similarity"]

            pair_key = (section_a, section_b)

            # Skip if already processed
            if pair_key in checkpoint["processed_pairs"]:
                logger.debug(f"Skipping already processed pair: {section_a}-{section_b}")
                continue

            # Get section texts
            text_a = sections.get(section_a)
            text_b = sections.get(section_b)

            if not text_a or not text_b:
                logger.warning(f"Missing text for {section_a} or {section_b}, skipping")
                checkpoint["processed_pairs"].add(pair_key)
                continue

            # Classify with LLM
            result, model_used = classify_similarity(
                text_a, text_b, section_a, section_b, rate_limiter, stats
            )

            if result is None:
                failed_classifications += 1
                checkpoint["processed_pairs"].add(pair_key)
                continue

            # Track model usage
            if model_used != "failed":
                checkpoint["model_usage"][model_used] = checkpoint["model_usage"].get(model_used, 0) + 1

            # Create output record
            record = {
                "section_a": section_a,
                "section_b": section_b,
                "similarity": similarity,
                "classification": result["classification"],
                "explanation": result["explanation"],
                "model_used": model_used,
                "analyzed_at": datetime.utcnow().isoformat() + "Z",
                "metadata": {
                    "pipeline_version": PIPELINE_VERSION
                }
            }

            # Validate record
            required_fields = ["section_a", "section_b", "similarity", "classification",
                             "explanation", "model_used", "analyzed_at"]
            if not validate_record(record, required_fields):
                logger.error(f"Invalid record for {section_a}-{section_b}, skipping")
                failed_classifications += 1
                checkpoint["processed_pairs"].add(pair_key)
                continue

            # Write record
            writer.write(record)

            # Update checkpoint
            checkpoint["processed_pairs"].add(pair_key)
            checkpoint["results"].append(record)
            pairs_processed += 1

            # Save checkpoint every 10 pairs
            if pairs_processed % 10 == 0:
                save_checkpoint(checkpoint)

    # Final checkpoint save
    save_checkpoint(checkpoint)

    # Print statistics
    logger.info(f"Classification complete!")
    logger.info(f"  Total pairs classified: {pairs_processed}")
    logger.info(f"  Failed classifications: {failed_classifications}")

    # Show model usage
    logger.info(f"  Model usage:")
    for model in GEMINI_MODELS + [OLLAMA_MODEL]:
        count = checkpoint["model_usage"].get(model, 0)
        if count > 0:
            logger.info(f"    {model}: {count} calls")

    logger.info(f"  Output: {output_file}")

    # Show classification distribution
    if checkpoint["results"]:
        from collections import Counter
        classifications = [r["classification"] for r in checkpoint["results"]]
        distribution = Counter(classifications)
        logger.info(f"  Classification distribution: {dict(distribution)}")

    return 0


if __name__ == "__main__":
    exit(main())
