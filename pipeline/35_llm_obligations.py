#!/usr/bin/env python3
"""
Enhanced obligation extraction with LLM classification.

Two-stage approach:
1. Fast Filter: Regex scan for sections containing numbers, "$", or temporal keywords
2. LLM Classify: Send candidates to LLM for detailed classification

Replaces separate deadlines/amounts extraction with unified obligations.

Usage:
  python pipeline/35_llm_obligations.py \
    --in data/outputs/sections_subset.ndjson \
    --out data/outputs/obligations_enhanced_subset.ndjson
"""

import argparse
import pickle
import re
from datetime import datetime
from pathlib import Path
from typing import List
from tqdm import tqdm
from collections import Counter

from common import NDJSONReader, NDJSONWriter, setup_logging, validate_record, PIPELINE_VERSION
from llm_client import LLMClient
from models import Obligation, ObligationsList

logger = setup_logging(__name__)

CHECKPOINT_FILE = Path("data/interim/obligations_enhanced.ckpt")
MAX_TEXT_LENGTH = 2000  # Truncate text for LLM

# Regex patterns for Stage 1 filtering
OBLIGATION_PATTERNS = [
    r'\$\s*\d+',  # Dollar amounts
    r'\d+\s*(?:day|week|month|year|hour)s?',  # Temporal references
    r'within\s+\d+',  # "within X days"
    r'not\s+(?:more|less)\s+than',  # Constraints
    r'at\s+least',  # Minimums
    r'no\s+(?:more|less)\s+than',  # Limits
    r'shall\s+(?:not\s+)?(?:exceed|be\s+less\s+than)',  # Legal constraints
    r'penalty|fine|fee|charge',  # Financial penalties
    r'deadline|due\s+date',  # Explicit deadlines
]

COMBINED_PATTERN = re.compile('|'.join(OBLIGATION_PATTERNS), re.IGNORECASE)


def has_obligation_keywords(text: str) -> bool:
    """
    Stage 1: Fast regex filter for obligation indicators.

    Returns:
        True if text contains patterns suggesting obligations
    """
    return COMBINED_PATTERN.search(text) is not None


def classify_obligation(
    text: str,
    section_id: str,
    client: LLMClient
) -> List[Obligation]:
    """
    Stage 2: LLM classification of obligation type and extraction.

    Args:
        text: Section text to analyze
        section_id: Section ID for output
        client: LLMClient instance

    Returns:
        List of Obligation instances found in the text
    """
    # Truncate text if too long
    truncated_text = text[:MAX_TEXT_LENGTH]
    if len(text) > MAX_TEXT_LENGTH:
        logger.debug(f"Truncated {section_id} from {len(text)} to {MAX_TEXT_LENGTH} chars")

    prompt = f"""You are analyzing a legal code section to extract OBLIGATIONS - requirements with specific values.

SECTION TEXT:
{truncated_text}

TASK: Identify ALL obligations in this section. For each obligation found, extract:

1. **category**: One of these types:
   - "deadline": Time-based requirements (e.g., "within 30 days", "annual report")
   - "constraint": Numeric limits or conditions (e.g., "at least 5 members", "not more than 100")
   - "allocation": Budget/resource allocations (e.g., "$1 million appropriated")
   - "penalty": Fines, fees, or penalties (e.g., "$500 fine", "imprisonment up to 90 days")

2. **phrase**: Exact text phrase containing the obligation (5-100 characters)

3. **value**: Numeric value if present (e.g., 30 for "30 days", 1000000 for "$1 million")

4. **unit**: Unit of measurement if applicable (e.g., "days", "dollars", "percent", "members")

IMPORTANT:
- Phrase should be the exact wording from the text (5-100 characters)
- For dollar amounts, value should be in dollars (not cents)
- jurisdiction and section_id will be added automatically - don't include them
- If no obligations found, return empty obligations array

Response format:
{{
  "obligations": [
    {{
      "category": "deadline",
      "phrase": "within 30 days",
      "value": 30,
      "unit": "days",
      "jurisdiction": "dc",
      "section_id": "{section_id}"
    }},
    {{
      "category": "penalty",
      "phrase": "$500 fine",
      "value": 500,
      "unit": "dollars",
      "jurisdiction": "dc",
      "section_id": "{section_id}"
    }}
  ]
}}
"""

    response = client.generate(
        prompt=prompt,
        response_model=ObligationsList,
        section_id=section_id
    )

    if response and response.data.obligations:
        # Add section ID and jurisdiction to each obligation
        for obligation in response.data.obligations:
            obligation.section_id = section_id
            obligation.jurisdiction = "dc"
        return response.data.obligations

    return []


def load_checkpoint() -> dict:
    """Load checkpoint if exists."""
    if CHECKPOINT_FILE.exists():
        logger.info(f"📂 Loading checkpoint from {CHECKPOINT_FILE}")
        with open(CHECKPOINT_FILE, 'rb') as f:
            checkpoint = pickle.load(f)
            # Add model_usage dict if it doesn't exist (backwards compatibility)
            if "model_usage" not in checkpoint:
                checkpoint["model_usage"] = {}
            return checkpoint

    return {
        "processed_ids": set(),
        "results": [],
        "model_usage": {},
        "filtered_count": 0,  # Sections filtered out by regex
        "classified_count": 0,  # Sections sent to LLM
    }


def save_checkpoint(checkpoint: dict):
    """Save checkpoint."""
    CHECKPOINT_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(CHECKPOINT_FILE, 'wb') as f:
        pickle.dump(checkpoint, f)
    logger.debug(f"💾 Checkpoint saved: {len(checkpoint['processed_ids'])} sections processed")


def main():
    parser = argparse.ArgumentParser(
        description="Extract and classify obligations using two-stage LLM approach"
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
        help="Output NDJSON file (enhanced obligations)"
    )
    parser.add_argument(
        "--filter-threshold",
        type=float,
        default=1.0,
        help="Confidence threshold for regex filter (0.0-1.0, default: 1.0 = all candidates)"
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
        logger.error(f"❌ Input file not found: {input_file}")
        return 1

    logger.info(f"🔍 Extracting enhanced obligations from {input_file}")
    logger.info(f"📊 Pipeline version: {PIPELINE_VERSION}")
    logger.info(f"🤖 Using unified LLM client with Instructor validation")

    # Load checkpoint
    checkpoint = load_checkpoint()

    # Initialize LLM client
    client = LLMClient()

    # Statistics
    sections_processed = 0
    obligations_found = 0
    failed_classifications = 0
    category_counts = Counter()

    # Stage 1: Regex filtering
    logger.info(f"\n📋 Stage 1: Scanning sections for obligation keywords...")
    reader = NDJSONReader(str(input_file))
    candidates = []

    for section in tqdm(reader, desc="Scanning", unit="section"):
        section_id = section.get("id")
        text_plain = section.get("text_plain", "")

        if not section_id or not text_plain:
            continue

        # Skip if already processed
        if section_id in checkpoint["processed_ids"]:
            continue

        # Apply limit if specified
        if args.limit and len(candidates) >= args.limit:
            break

        # Regex filter
        if has_obligation_keywords(text_plain):
            candidates.append({
                "id": section_id,
                "text": text_plain
            })
        else:
            # Mark as processed (filtered out)
            checkpoint["processed_ids"].add(section_id)
            checkpoint["filtered_count"] = checkpoint.get("filtered_count", 0) + 1

    total_candidates = len(candidates)
    logger.info(f"✅ Found {total_candidates} candidate sections (filtered out {checkpoint['filtered_count']})")

    if total_candidates == 0:
        logger.warning("⚠️  No candidates found - all sections filtered out by regex")
        return 0

    # Stage 2: LLM classification
    logger.info(f"\n🤖 Stage 2: Classifying obligations with LLM...")

    with NDJSONWriter(str(output_file)) as writer:
        for section in tqdm(candidates, desc="Classifying", unit="section"):
            section_id = section["id"]

            # Classify with LLM
            obligations = classify_obligation(section["text"], section_id, client)

            if not obligations:
                # No obligations found, but mark as processed
                checkpoint["processed_ids"].add(section_id)
                checkpoint["classified_count"] = checkpoint.get("classified_count", 0) + 1
                continue

            # Write each obligation as a separate record
            for obligation in obligations:
                record = {
                    "jurisdiction": obligation.jurisdiction,
                    "section_id": obligation.section_id,
                    "category": obligation.category,
                    "phrase": obligation.phrase,
                    "value": obligation.value,
                    "unit": obligation.unit,
                }

                # Validate record
                required_fields = ["jurisdiction", "section_id", "category", "phrase"]
                if not validate_record(record, required_fields):
                    logger.error(f"❌ Invalid record for {section_id}, skipping")
                    failed_classifications += 1
                    continue

                # Write record
                writer.write(record)

                # Update statistics
                obligations_found += 1
                category_counts[obligation.category] += 1

            # Update checkpoint
            checkpoint["processed_ids"].add(section_id)
            checkpoint["classified_count"] = checkpoint.get("classified_count", 0) + 1
            sections_processed += 1

            # Save checkpoint every 5 sections
            if sections_processed % 5 == 0:
                save_checkpoint(checkpoint)

    # Final checkpoint save
    save_checkpoint(checkpoint)

    # Summary
    logger.info(f"\n✨ Extraction complete!")
    logger.info(f"📊 Statistics:")
    logger.info(f"  • Sections scanned: {checkpoint['filtered_count'] + total_candidates}")
    logger.info(f"  • Filtered by regex: {checkpoint['filtered_count']}")
    logger.info(f"  • Classified by LLM: {checkpoint['classified_count']}")
    logger.info(f"  • Total obligations found: {obligations_found}")
    logger.info(f"  • Failed classifications: {failed_classifications}")

    if obligations_found > 0:
        logger.info(f"\n📈 Obligation categories:")
        for category, count in sorted(category_counts.items(), key=lambda x: x[1], reverse=True):
            logger.info(f"  • {category}: {count}")

    logger.info(f"\n📁 Output: {output_file}")

    return 0


if __name__ == "__main__":
    exit(main())
