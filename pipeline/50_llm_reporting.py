#!/usr/bin/env python3
"""
Detect reporting requirements in DC Code sections using LLM analysis.

Uses Ollama's phi3.5 model to analyze each section and identify whether it
contains reporting, disclosure, or documentation requirements.

Usage:
  python pipeline/50_llm_reporting.py \
    --in data/outputs/sections_subset.ndjson \
    --out data/outputs/reporting_subset.ndjson
"""

import argparse
import json
import pickle
import re
import requests
from datetime import datetime
from pathlib import Path
from typing import Optional
from tqdm import tqdm
from collections import Counter

from common import NDJSONReader, NDJSONWriter, setup_logging, validate_record, PIPELINE_VERSION

logger = setup_logging(__name__)

OLLAMA_HOST = "http://localhost:11434"
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


def get_llm_analysis(text: str, section_id: str, model: str = "phi3.5") -> Optional[dict]:
    """
    Analyze section text for reporting requirements using LLM.

    Args:
        text: Section text to analyze
        section_id: Section ID (for logging)
        model: Ollama model name

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
        # Call Ollama generate API
        response = requests.post(
            f"{OLLAMA_HOST}/api/generate",
            json={
                "model": model,
                "prompt": prompt,
                "stream": False
            },
            timeout=60  # LLM generation can be slow
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
        logger.error(f"Unexpected error analyzing {section_id}: {e}")
        return None


def load_checkpoint() -> dict:
    """Load checkpoint if exists."""
    if CHECKPOINT_FILE.exists():
        logger.info(f"Loading checkpoint from {CHECKPOINT_FILE}")
        with open(CHECKPOINT_FILE, 'rb') as f:
            return pickle.load(f)

    return {
        "processed_ids": set(),  # Set of processed section IDs
        "results": []            # List of reporting records
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
    parser.add_argument(
        "--model",
        default="phi3.5",
        help="Ollama model to use for analysis (default: phi3.5)"
    )

    args = parser.parse_args()

    input_file = Path(args.input_file)
    output_file = Path(args.out)

    if not input_file.exists():
        logger.error(f"Input file not found: {input_file}")
        return 1

    logger.info(f"Detecting reporting requirements in {input_file}")
    logger.info(f"Using model: {args.model}")
    logger.info(f"Pipeline version: {PIPELINE_VERSION}")

    # Load checkpoint
    checkpoint = load_checkpoint()

    # Statistics
    sections_processed = 0
    sections_with_reporting = 0
    failed_analyses = 0
    all_tags = []

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
            analysis = get_llm_analysis(section["text"], section_id, model=args.model)

            if analysis is None:
                failed_analyses += 1
                # Mark as processed even if failed (to avoid retrying forever)
                checkpoint["processed_ids"].add(section_id)
                continue

            # Create output record
            record = {
                "id": section_id,
                "has_reporting": analysis["has_reporting_requirement"],
                "reporting_summary": analysis["reporting_summary"],
                "tags": analysis["tags"],
                "highlight_phrases": analysis["highlight_phrases"],
                "metadata": {
                    "model": args.model,
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
    logger.info(f"  Most common tags: {tag_counts.most_common(10)}")
    logger.info(f"  Output: {output_file}")

    return 0


if __name__ == "__main__":
    exit(main())
