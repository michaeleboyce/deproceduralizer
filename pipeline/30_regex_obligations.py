#!/usr/bin/env python3
"""
Extract obligations (deadlines and dollar amounts) from DC Code sections.

Finds time-based obligations like "within 30 days" and financial amounts like "$1,000".

Usage:
  python pipeline/30_regex_obligations.py \
    --in data/outputs/sections_subset.ndjson \
    --deadlines data/outputs/deadlines_subset.ndjson \
    --amounts data/outputs/amounts_subset.ndjson
"""

import argparse
import re
from pathlib import Path
from tqdm import tqdm

from common import (
    NDJSONReader,
    NDJSONWriter,
    StateManager,
    setup_logging,
    validate_record
)

logger = setup_logging(__name__)

# Deadline patterns: (pattern, kind)
DEADLINE_PATTERNS = [
    # "within 30 days"
    (r'within\s+(\d+)\s+days?', 'deadline'),

    # "no later than 60 days"
    (r'no\s+later\s+than\s+(\d+)\s+days?', 'deadline'),

    # "30-day notice"
    (r'(\d+)-day\s+notice', 'notice_period'),

    # "within 90 business days"
    (r'within\s+(\d+)\s+business\s+days?', 'business_deadline'),

    # "at least 15 days before"
    (r'at\s+least\s+(\d+)\s+days?\s+before', 'advance_notice'),

    # "not more than 45 days"
    (r'not\s+more\s+than\s+(\d+)\s+days?', 'deadline'),

    # "within X calendar days"
    (r'within\s+(\d+)\s+calendar\s+days?', 'calendar_deadline'),
]

# Dollar amount patterns
AMOUNT_PATTERNS = [
    # $1,000 or $1,000.00 or $1,000,000.00
    r'\$\s*(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)',

    # $50 or $50.00 (simple amounts)
    r'\$\s*(\d+(?:\.\d{2})?)',
]


def parse_amount(amount_str: str) -> int:
    """
    Convert dollar string to cents.

    Examples:
      "$1,000" -> 100000
      "$50.00" -> 5000
      "$1,000,000" -> 100000000
    """
    # Remove $ and commas
    clean = amount_str.replace('$', '').replace(',', '').strip()

    # Convert to float then to cents
    try:
        dollars = float(clean)
        cents = int(dollars * 100)
        return cents
    except ValueError:
        logger.error(f"Could not parse amount: {amount_str}")
        return 0


def get_context(text: str, match_start: int, match_end: int, context_chars: int = 50) -> str:
    """
    Extract surrounding context for a regex match.

    Args:
        text: Full text
        match_start: Match start position
        match_end: Match end position
        context_chars: Characters of context on each side

    Returns:
        Text snippet with context
    """
    start = max(0, match_start - context_chars)
    end = min(len(text), match_end + context_chars)

    snippet = text[start:end].strip()

    # Clean up whitespace
    snippet = re.sub(r'\s+', ' ', snippet)

    return snippet


def extract_deadlines(text: str, section_id: str) -> list[dict]:
    """
    Extract deadline obligations from section text.

    Returns:
        List of deadline records
    """
    deadlines = []
    seen_deadlines = set()  # Avoid duplicates

    for pattern, kind in DEADLINE_PATTERNS:
        for match in re.finditer(pattern, text, re.IGNORECASE):
            days = int(match.group(1))

            # Validate reasonable range (1-365 days)
            if days < 1 or days > 365:
                continue

            # Get context phrase
            phrase = get_context(text, match.start(), match.end())

            # Create unique key to avoid duplicates
            deadline_key = (section_id, days, kind, phrase[:50])
            if deadline_key in seen_deadlines:
                continue

            deadlines.append({
                "section_id": section_id,
                "phrase": phrase,
                "days": days,
                "kind": kind
            })
            seen_deadlines.add(deadline_key)

    return deadlines


def extract_amounts(text: str, section_id: str) -> list[dict]:
    """
    Extract dollar amounts from section text.

    Returns:
        List of amount records
    """
    amounts = []
    seen_amounts = set()  # Avoid duplicates

    for pattern in AMOUNT_PATTERNS:
        for match in re.finditer(pattern, text):
            amount_str = match.group(0)
            amount_cents = parse_amount(amount_str)

            # Skip invalid or zero amounts
            if amount_cents <= 0:
                continue

            # Get context phrase
            phrase = get_context(text, match.start(), match.end())

            # Create unique key to avoid duplicates
            amount_key = (section_id, amount_cents, phrase[:50])
            if amount_key in seen_amounts:
                continue

            amounts.append({
                "section_id": section_id,
                "phrase": phrase,
                "amount_cents": amount_cents
            })
            seen_amounts.add(amount_key)

    return amounts


def main():
    parser = argparse.ArgumentParser(
        description="Extract obligations (deadlines and amounts) from DC Code sections"
    )
    parser.add_argument(
        "--in",
        dest="input_file",
        required=True,
        help="Input NDJSON file (sections)"
    )
    parser.add_argument(
        "--deadlines",
        required=True,
        help="Output NDJSON file for deadlines"
    )
    parser.add_argument(
        "--amounts",
        required=True,
        help="Output NDJSON file for dollar amounts"
    )

    args = parser.parse_args()

    input_file = Path(args.input_file)
    deadlines_file = Path(args.deadlines)
    amounts_file = Path(args.amounts)

    if not input_file.exists():
        logger.error(f"Input file not found: {input_file}")
        return 1

    # Set up state management
    state_file = Path("data/interim/obligations.state")
    state = StateManager(str(state_file))

    # Statistics
    sections_processed = 0
    total_deadlines = 0
    total_amounts = 0
    sections_with_deadlines = 0
    sections_with_amounts = 0

    logger.info(f"Extracting obligations from {input_file}")

    # Count total sections for progress bar
    with open(input_file, 'r') as f:
        total_sections = sum(1 for _ in f)

    # Process sections
    reader = NDJSONReader(str(input_file), state_manager=state)

    with NDJSONWriter(str(deadlines_file)) as deadlines_writer, \
         NDJSONWriter(str(amounts_file)) as amounts_writer:

        for section in tqdm(reader, total=total_sections, desc="Extracting obligations", unit="section"):
            section_id = section.get("id")
            text_plain = section.get("text_plain", "")

            if not section_id or not text_plain:
                logger.warning(f"Section missing id or text_plain, skipping")
                continue

            # Extract deadlines
            deadlines = extract_deadlines(text_plain, section_id)
            if deadlines:
                sections_with_deadlines += 1
                total_deadlines += len(deadlines)

                for deadline in deadlines:
                    required_fields = ["section_id", "phrase", "days", "kind"]
                    if validate_record(deadline, required_fields):
                        deadlines_writer.write(deadline)
                    else:
                        logger.error(f"Invalid deadline record: {deadline}")

            # Extract amounts
            amounts = extract_amounts(text_plain, section_id)
            if amounts:
                sections_with_amounts += 1
                total_amounts += len(amounts)

                for amount in amounts:
                    required_fields = ["section_id", "phrase", "amount_cents"]
                    if validate_record(amount, required_fields):
                        amounts_writer.write(amount)
                    else:
                        logger.error(f"Invalid amount record: {amount}")

            sections_processed += 1

            # Save state periodically
            if sections_processed % 10 == 0:
                state.set("sections_processed", sections_processed)
                state.save()

    # Final state save
    state.set("sections_processed", sections_processed)
    state.set("total_deadlines", total_deadlines)
    state.set("total_amounts", total_amounts)
    state.save()

    logger.info(f"Extraction complete!")
    logger.info(f"  Sections processed: {sections_processed}")
    logger.info(f"  Deadlines:")
    logger.info(f"    Sections with deadlines: {sections_with_deadlines}")
    logger.info(f"    Total deadlines: {total_deadlines}")
    logger.info(f"  Amounts:")
    logger.info(f"    Sections with amounts: {sections_with_amounts}")
    logger.info(f"    Total amounts: {total_amounts}")
    logger.info(f"  Output files:")
    logger.info(f"    Deadlines: {deadlines_file}")
    logger.info(f"    Amounts: {amounts_file}")

    return 0


if __name__ == "__main__":
    exit(main())
