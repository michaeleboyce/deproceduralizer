#!/usr/bin/env python3
"""
Extract cross-references between DC Code sections.

Finds citations like "§ 1-101" or "section 1-101" in section text
and creates cross-reference records.

Usage:
  python pipeline/20_crossrefs.py --in data/outputs/sections_subset.ndjson --out data/outputs/refs_subset.ndjson
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

# Citation patterns to detect
CITATION_PATTERNS = [
    # § 1-101 or § 1-101.01
    (r'§\s*(\d+[-\.]\d+(?:[-\.]\d+)?)', 'section'),

    # section 1-101
    (r'\bsection\s+(\d+[-\.]\d+(?:[-\.]\d+)?)', 'section'),

    # §§ 1-101 to 1-105 (range - we'll extract both ends)
    (r'§§\s*(\d+[-\.]\d+)\s+(?:to|through)\s+(\d+[-\.]\d+)', 'range'),
]


def normalize_section_number(section_num: str) -> str:
    """
    Convert section number to ID format.

    Examples:
      "1-101" -> "dc-1-101"
      "1-101.01" -> "dc-1-101-01"
    """
    # Replace dots with dashes
    normalized = section_num.replace('.', '-')
    return f"dc-{normalized}"


def extract_citations(text: str, from_section_id: str) -> list[dict]:
    """
    Extract all citations from section text.

    Returns:
        List of cross-reference records
    """
    refs = []
    seen_pairs = set()  # Track unique (from, to) pairs to avoid duplicates

    for pattern, cite_type in CITATION_PATTERNS:
        for match in re.finditer(pattern, text, re.IGNORECASE):
            if cite_type == 'range':
                # Handle range citations (e.g., "§§ 1-101 to 1-105")
                start_num = match.group(1)
                end_num = match.group(2)

                # Add both endpoints as separate citations
                for section_num in [start_num, end_num]:
                    to_section_id = normalize_section_number(section_num)
                    raw_cite = match.group(0)

                    # Avoid duplicate pairs
                    pair_key = (from_section_id, to_section_id)
                    if pair_key not in seen_pairs:
                        refs.append({
                            "from_id": from_section_id,
                            "to_id": to_section_id,
                            "raw_cite": raw_cite
                        })
                        seen_pairs.add(pair_key)
            else:
                # Single section citation
                section_num = match.group(1)
                to_section_id = normalize_section_number(section_num)
                raw_cite = match.group(0)

                # Avoid self-references and duplicates
                if to_section_id != from_section_id:
                    pair_key = (from_section_id, to_section_id)
                    if pair_key not in seen_pairs:
                        refs.append({
                            "from_id": from_section_id,
                            "to_id": to_section_id,
                            "raw_cite": raw_cite
                        })
                        seen_pairs.add(pair_key)

    return refs


def main():
    parser = argparse.ArgumentParser(
        description="Extract cross-references between DC Code sections"
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
        help="Output NDJSON file (cross-references)"
    )

    args = parser.parse_args()

    input_file = Path(args.input_file)
    output_file = Path(args.out)

    if not input_file.exists():
        logger.error(f"Input file not found: {input_file}")
        return 1

    # Set up state management
    state_file = Path("data/interim/crossrefs.state")
    state = StateManager(str(state_file))

    # Statistics
    sections_processed = 0
    total_refs = 0
    sections_with_refs = 0

    logger.info(f"Extracting cross-references from {input_file}")

    # Count total sections for progress bar
    with open(input_file, 'r') as f:
        total_sections = sum(1 for _ in f)

    # Process sections
    reader = NDJSONReader(str(input_file), state_manager=state)

    with NDJSONWriter(str(output_file)) as writer:
        for section in tqdm(reader, total=total_sections, desc="Extracting citations", unit="section"):
            section_id = section.get("id")
            text_plain = section.get("text_plain", "")

            if not section_id or not text_plain:
                logger.warning(f"Section missing id or text_plain, skipping")
                continue

            # Extract citations from this section
            citations = extract_citations(text_plain, section_id)

            if citations:
                sections_with_refs += 1
                total_refs += len(citations)

                # Write each citation as a separate record
                for citation in citations:
                    # Validate
                    required_fields = ["from_id", "to_id", "raw_cite"]
                    if validate_record(citation, required_fields):
                        writer.write(citation)
                    else:
                        logger.error(f"Invalid citation record: {citation}")

            sections_processed += 1

            # Save state periodically
            if sections_processed % 10 == 0:
                state.set("sections_processed", sections_processed)
                state.save()

    # Final state save
    state.set("sections_processed", sections_processed)
    state.set("total_refs", total_refs)
    state.save()

    logger.info(f"Extraction complete!")
    logger.info(f"  Sections processed: {sections_processed}")
    logger.info(f"  Sections with citations: {sections_with_refs}")
    logger.info(f"  Total cross-references: {total_refs}")
    logger.info(f"  Average citations per section: {total_refs / sections_processed if sections_processed > 0 else 0:.2f}")
    logger.info(f"  Output: {output_file}")

    return 0


if __name__ == "__main__":
    exit(main())
