#!/usr/bin/env python3
"""
Detect reporting requirements in DC Code sections using LLM analysis.

Uses Gemini 2.5 Flash (free tier) with fallback to Ollama phi3.5 to analyze
each section and identify whether it contains reporting, disclosure, or
documentation requirements.

Usage:
  python pipeline/50_llm_reporting.py \
    --in data/outputs/sections_subset.ndjson \
    --out data/outputs/reporting_subset.ndjson
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
from typing import Optional
from tqdm import tqdm
from collections import Counter

from common import NDJSONReader, NDJSONWriter, setup_logging, validate_record, PIPELINE_VERSION

logger = setup_logging(__name__)

# API Configuration
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_MODEL = "gemini-2.5-flash"
GEMINI_API_URL = f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent"

OLLAMA_HOST = "http://localhost:11434"
OLLAMA_MODEL = "phi3.5"

# Rate limiting for Gemini free tier
GEMINI_RPM_LIMIT = 15  # requests per minute
GEMINI_RPD_LIMIT = 1500  # requests per day
RPM_WINDOW = 60  # seconds

CHECKPOINT_FILE = Path("data/interim/reporting.ckpt")
MAX_TEXT_LENGTH = 3000  # Truncate text to avoid token limits


def parse_llm_json(response_text: str) -> Optional[dict]:
    """
    Robustly parse JSON from LLM response.

    LLMs sometimes wrap JSON in markdown or add explanations.
    Try multiple parsing strategies.

    Args:
        response_text: Raw text response from LLM

    Returns:
        Parsed dict or None if parsing fails
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


def get_llm_analysis_gemini(text: str, section_id: str) -> Optional[dict]:
    """
    Analyze section text for reporting requirements using Gemini API.

    Args:
        text: Section text to analyze
        section_id: Section ID (for logging)

    Returns:
        Dict with analysis results or None if failed
    """
    if not GEMINI_API_KEY:
        return None

    # Truncate text if too long
    truncated_text = text[:MAX_TEXT_LENGTH]
    if len(text) > MAX_TEXT_LENGTH:
        logger.debug(f"Truncated {section_id} from {len(text)} to {MAX_TEXT_LENGTH} chars")

    # Construct prompt
    prompt = f"""You are analyzing a legal code section for SUBSTANTIVE reporting requirements.

TASK: Determine if this section requires an entity to compile and submit regular reports, data, statistics, or documentation to an oversight body.

WHAT COUNTS AS REPORTING (set has_reporting_requirement=true):
- Regular/periodic reports (annual, quarterly, monthly reports)
- Submission of compiled data, statistics, or performance metrics
- Financial reporting or audits
- Documentation submitted to Council, Mayor, or oversight agencies
- Maintaining and publishing records or registries

WHAT DOES NOT COUNT (set has_reporting_requirement=false):
- Simple one-time notifications ("shall notify")
- Procedural notices ("provide written notice")
- Basic communication requirements
- Posting of signs or public notices
- Authority to remove/appoint without reporting element

SECTION TEXT:
{truncated_text}

RESPOND WITH VALID JSON ONLY (no markdown, no explanations):
{{
  "has_reporting_requirement": true or false,
  "reporting_summary": "1-2 sentence description" or "",
  "tags": ["tag1", "tag2"] or [],
  "highlight_phrases": ["exact phrase from text"] or []
}}

GUIDELINES:
- tags: Use lowercase, focus on WHO reports (mayor, director, agency, board) and WHEN (annual, quarterly, monthly)
- highlight_phrases: Extract 2-5 key phrases that indicate substantive reporting (e.g., "shall submit a report", "publish statistics", "maintain records")
- Keep reporting_summary concise and specific about WHAT is reported and TO WHOM
"""

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

        response = requests.post(
            f"{GEMINI_API_URL}?key={GEMINI_API_KEY}",
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

                if parsed is None:
                    logger.error(f"Failed to parse JSON for {section_id}")
                    return None

                # Validate required fields
                required_fields = ["has_reporting_requirement", "reporting_summary", "tags", "highlight_phrases"]
                for field in required_fields:
                    if field not in parsed:
                        logger.error(f"Missing field '{field}' in response for {section_id}")
                        return None

                return parsed

        logger.error(f"Unexpected Gemini response format for {section_id}")
        return None

    except requests.exceptions.Timeout:
        logger.error(f"Timeout calling Gemini API for {section_id}")
        return None
    except requests.exceptions.RequestException as e:
        logger.error(f"Error calling Gemini API for {section_id}: {e}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error with Gemini for {section_id}: {e}")
        return None


def get_llm_analysis_ollama(text: str, section_id: str) -> Optional[dict]:
    """
    Analyze section text for reporting requirements using Ollama phi3.5.

    Fallback when Gemini is rate limited or fails.

    Args:
        text: Section text to analyze
        section_id: Section ID (for logging)

    Returns:
        Dict with analysis results or None if failed
    """
    # Truncate text if too long
    truncated_text = text[:MAX_TEXT_LENGTH]
    if len(text) > MAX_TEXT_LENGTH:
        logger.debug(f"Truncated {section_id} from {len(text)} to {MAX_TEXT_LENGTH} chars")

    # Construct prompt
    prompt = f"""You are analyzing a legal code section for SUBSTANTIVE reporting requirements.

TASK: Determine if this section requires an entity to compile and submit regular reports, data, statistics, or documentation to an oversight body.

WHAT COUNTS AS REPORTING (set has_reporting_requirement=true):
- Regular/periodic reports (annual, quarterly, monthly reports)
- Submission of compiled data, statistics, or performance metrics
- Financial reporting or audits
- Documentation submitted to Council, Mayor, or oversight agencies
- Maintaining and publishing records or registries

WHAT DOES NOT COUNT (set has_reporting_requirement=false):
- Simple one-time notifications ("shall notify")
- Procedural notices ("provide written notice")
- Basic communication requirements
- Posting of signs or public notices
- Authority to remove/appoint without reporting element

SECTION TEXT:
{truncated_text}

RESPOND WITH VALID JSON ONLY (no markdown, no explanations):
{{
  "has_reporting_requirement": true or false,
  "reporting_summary": "1-2 sentence description" or "",
  "tags": ["tag1", "tag2"] or [],
  "highlight_phrases": ["exact phrase from text"] or []
}}

GUIDELINES:
- tags: Use lowercase, focus on WHO reports (mayor, director, agency, board) and WHEN (annual, quarterly, monthly)
- highlight_phrases: Extract 2-5 key phrases that indicate substantive reporting (e.g., "shall submit a report", "publish statistics", "maintain records")
- Keep reporting_summary concise and specific about WHAT is reported and TO WHOM
"""

    try:
        response = requests.post(
            f"{OLLAMA_HOST}/api/generate",
            json={
                "model": OLLAMA_MODEL,
                "prompt": prompt,
                "stream": False
            },
            timeout=90  # Ollama can be slow
        )
        response.raise_for_status()
        data = response.json()

        # Extract response text
        response_text = data.get("response", "")

        # Parse JSON from response
        parsed = parse_llm_json(response_text)

        if parsed is None:
            logger.error(f"Failed to parse JSON for {section_id}")
            return None

        # Validate required fields
        required_fields = ["has_reporting_requirement", "reporting_summary", "tags", "highlight_phrases"]
        for field in required_fields:
            if field not in parsed:
                logger.error(f"Missing field '{field}' in response for {section_id}")
                return None

        return parsed

    except requests.exceptions.Timeout:
        logger.error(f"Timeout calling Ollama for {section_id}")
        return None
    except requests.exceptions.RequestException as e:
        logger.error(f"Error calling Ollama API for {section_id}: {e}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error with Ollama for {section_id}: {e}")
        return None


def get_llm_analysis(text: str, section_id: str, rate_limiter: RateLimiter, stats: dict) -> tuple[Optional[dict], str]:
    """
    Analyze section using Gemini with Ollama fallback.

    Args:
        text: Section text to analyze
        section_id: Section ID (for logging)
        rate_limiter: Rate limiter for Gemini API
        stats: Statistics dict for tracking fallback

    Returns:
        (analysis_dict, model_used)
    """
    # Try Gemini first if rate limit allows
    if rate_limiter.wait_if_needed():
        result = get_llm_analysis_gemini(text, section_id)
        if result:
            rate_limiter.record_call()
            return result, GEMINI_MODEL

    # Fallback to Ollama
    if not stats.get('fallback_logged'):
        logger.info("⚠ Falling back to Ollama (Gemini unavailable/rate limited)")
        stats['fallback_logged'] = True

    result = get_llm_analysis_ollama(text, section_id)
    if result:
        return result, OLLAMA_MODEL

    return None, "failed"


def load_checkpoint() -> dict:
    """Load checkpoint if exists."""
    if CHECKPOINT_FILE.exists():
        logger.info(f"Loading checkpoint from {CHECKPOINT_FILE}")
        with open(CHECKPOINT_FILE, 'rb') as f:
            checkpoint = pickle.load(f)
            # Add new fields if they don't exist (for backwards compatibility)
            if "gemini_calls" not in checkpoint:
                checkpoint["gemini_calls"] = 0
            if "ollama_calls" not in checkpoint:
                checkpoint["ollama_calls"] = 0
            return checkpoint

    return {
        "processed_ids": set(),  # Set of processed section IDs
        "results": [],           # List of reporting records
        "gemini_calls": 0,       # Number of Gemini API calls
        "ollama_calls": 0        # Number of Ollama API calls
    }


def save_checkpoint(checkpoint: dict):
    """Save checkpoint."""
    CHECKPOINT_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(CHECKPOINT_FILE, 'wb') as f:
        pickle.dump(checkpoint, f)
    logger.debug(f"Saved checkpoint: {len(checkpoint['processed_ids'])} sections processed")


def main():
    parser = argparse.ArgumentParser(
        description="Detect reporting requirements using LLM analysis"
    )
    parser.add_argument(
        "--in",
        dest="input_file",
        required=True,
        help="Input NDJSON file (sections)"
    )
    parser.add_argument(
        "--out",
        required=True,
        help="Output NDJSON file (reporting analysis)"
    )
    parser.add_argument(
        "--limit",
        type=int,
        help="Limit number of sections to process (for testing)"
    )

    args = parser.parse_args()

    input_file = Path(args.input_file)
    output_file = Path(args.out)

    if not input_file.exists():
        logger.error(f"Input file not found: {input_file}")
        return 1

    logger.info(f"Detecting reporting requirements in {input_file}")
    logger.info(f"Pipeline version: {PIPELINE_VERSION}")

    # Clear model configuration logging
    if GEMINI_API_KEY:
        logger.info(f"✓ Gemini 2.5 Flash configured (primary)")
        logger.info(f"  Rate limits: {GEMINI_RPM_LIMIT} RPM, {GEMINI_RPD_LIMIT} RPD")
        logger.info(f"✓ Ollama {OLLAMA_MODEL} configured (fallback)")
    else:
        logger.warning(f"✗ Gemini API key not found - will use Ollama {OLLAMA_MODEL} only")
        logger.info(f"  Set GEMINI_API_KEY environment variable to enable Gemini")

    # Load checkpoint
    checkpoint = load_checkpoint()

    # Initialize rate limiter
    rate_limiter = RateLimiter(GEMINI_RPM_LIMIT, GEMINI_RPD_LIMIT)

    # Statistics
    sections_processed = 0
    sections_with_reporting = 0
    failed_analyses = 0
    all_tags = []
    stats = {'fallback_logged': False}  # Track if we've logged fallback message

    # Read sections
    reader = NDJSONReader(str(input_file))
    sections_to_process = []

    for section in reader:
        section_id = section.get("id")
        text_plain = section.get("text_plain", "")

        if not section_id or not text_plain:
            continue

        sections_to_process.append({
            "id": section_id,
            "text": text_plain
        })

        # Apply limit if specified
        if args.limit and len(sections_to_process) >= args.limit:
            break

    total_sections = len(sections_to_process)
    logger.info(f"Found {total_sections} sections to analyze")

    # Process sections with progress bar
    with NDJSONWriter(str(output_file)) as writer:
        for section in tqdm(sections_to_process, desc="Analyzing sections", unit="section"):
            section_id = section["id"]

            # Skip if already processed
            if section_id in checkpoint["processed_ids"]:
                logger.debug(f"Skipping already processed section: {section_id}")
                continue

            # Analyze with LLM
            analysis, model_used = get_llm_analysis(section["text"], section_id, rate_limiter, stats)

            if analysis is None:
                failed_analyses += 1
                # Mark as processed even if failed (to avoid retrying forever)
                checkpoint["processed_ids"].add(section_id)
                continue

            # Track model usage
            if model_used == GEMINI_MODEL:
                checkpoint["gemini_calls"] += 1
            elif model_used == OLLAMA_MODEL:
                checkpoint["ollama_calls"] += 1

            # Create output record
            record = {
                "id": section_id,
                "has_reporting": analysis["has_reporting_requirement"],
                "reporting_summary": analysis["reporting_summary"],
                "tags": analysis["tags"],
                "highlight_phrases": analysis["highlight_phrases"],
                "metadata": {
                    "model": model_used,
                    "pipeline_version": PIPELINE_VERSION,
                    "analyzed_at": datetime.utcnow().isoformat() + "Z"
                }
            }

            # Validate record
            required_fields = ["id", "has_reporting", "reporting_summary", "tags", "highlight_phrases", "metadata"]
            if not validate_record(record, required_fields):
                logger.error(f"Invalid record for {section_id}, skipping")
                failed_analyses += 1
                checkpoint["processed_ids"].add(section_id)
                continue

            # Write record
            writer.write(record)

            # Update statistics
            checkpoint["processed_ids"].add(section_id)
            checkpoint["results"].append(record)
            sections_processed += 1

            if record["has_reporting"]:
                sections_with_reporting += 1
                all_tags.extend(record["tags"])

            # Save checkpoint every 5 sections
            if sections_processed % 5 == 0:
                save_checkpoint(checkpoint)

    # Final checkpoint save
    save_checkpoint(checkpoint)

    # Calculate statistics
    reporting_percentage = (sections_with_reporting / sections_processed * 100) if sections_processed > 0 else 0
    tag_counts = Counter(all_tags)

    logger.info(f"Analysis complete!")
    logger.info(f"  Total sections analyzed: {sections_processed}")
    logger.info(f"  Sections with reporting requirements: {sections_with_reporting} ({reporting_percentage:.1f}%)")
    logger.info(f"  Failed analyses: {failed_analyses}")
    logger.info(f"  Gemini API calls: {checkpoint['gemini_calls']}")
    logger.info(f"  Ollama API calls: {checkpoint['ollama_calls']}")
    logger.info(f"  Most common tags: {tag_counts.most_common(10)}")
    logger.info(f"  Output: {output_file}")

    return 0


if __name__ == "__main__":
    exit(main())
