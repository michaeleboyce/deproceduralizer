#!/usr/bin/env python3
"""
Cross-encoder semantic filter for reporting requirements detection.

Uses NLI-trained cross-encoder to pre-filter sections before LLM analysis,
reducing LLM API calls by 40-60%.

Two-stage approach:
1. Cross-encoder semantic filtering (this script) → candidates
2. LLM detailed classification (50_llm_reporting.py) → final reports

Usage:
  python pipeline/45_cross_encoder_reporting_filter.py \
    --in data/outputs/sections_small.ndjson \
    --out data/outputs/reporting_candidates_small.ndjson
"""

import argparse
import pickle
from pathlib import Path
from typing import List, Tuple
from tqdm import tqdm
from sentence_transformers import CrossEncoder

from common import NDJSONReader, NDJSONWriter, setup_logging, PIPELINE_VERSION

logger = setup_logging(__name__)

# Cross-encoder model for semantic similarity
MODEL_NAME = "cross-encoder/nli-deberta-v3-base"

# Conservative threshold - favor false positives over false negatives
# Sections scoring >= this threshold will be sent to LLM
CONFIDENCE_THRESHOLD = 0.2

# Reporting requirement indicators for semantic matching
REPORTING_INDICATORS = [
    "This section requires submitting reports to government agencies",
    "This section mandates annual or periodic reporting requirements",
    "This section specifies agencies must file reports with the Council",
    "This section describes quarterly or monthly reporting obligations",
    "This section requires public disclosure and transparency reports",
]

CHECKPOINT_FILE = Path("data/interim/cross_encoder_reporting_filter.ckpt")


def load_checkpoint() -> dict:
    """Load checkpoint if exists."""
    if CHECKPOINT_FILE.exists():
        logger.info(f"📂 Loading checkpoint from {CHECKPOINT_FILE}")
        with open(CHECKPOINT_FILE, 'rb') as f:
            return pickle.load(f)

    return {
        "processed_ids": set(),
        "candidate_ids": [],
        "filtered_count": 0,
        "passed_count": 0,
    }


def save_checkpoint(checkpoint: dict):
    """Save checkpoint."""
    CHECKPOINT_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(CHECKPOINT_FILE, 'wb') as f:
        pickle.dump(checkpoint, f)
    logger.debug(f"💾 Checkpoint saved: {len(checkpoint['processed_ids'])} sections processed")


def score_section(
    cross_encoder: CrossEncoder,
    text: str,
    indicators: List[str],
) -> float:
    """
    Score a section against reporting indicators using cross-encoder.

    Args:
        cross_encoder: Loaded CrossEncoder model
        text: Section text to score
        indicators: List of reporting requirement indicators

    Returns:
        Maximum score across all indicators (0-1 range)
    """
    # Create pairs: (text, indicator) for each indicator
    pairs = [(text[:512], indicator) for indicator in indicators]

    # Get scores from cross-encoder (returns logits, normalized to 0-1)
    scores = cross_encoder.predict(pairs, convert_to_numpy=True)

    # Return max score across all indicators
    return float(max(scores))


def filter_candidates(
    input_file: Path,
    output_file: Path,
    checkpoint: dict,
    threshold: float = CONFIDENCE_THRESHOLD,
    limit: int = None,
) -> Tuple[int, int]:
    """
    Filter sections using cross-encoder semantic matching.

    Args:
        input_file: Input NDJSON file with sections
        output_file: Output NDJSON file for candidates
        checkpoint: Checkpoint dict
        threshold: Confidence threshold for filtering
        limit: Optional limit on number of sections to process

    Returns:
        Tuple of (sections_filtered, sections_passed)
    """
    logger.info(f"🔍 Loading cross-encoder model: {MODEL_NAME}")
    logger.info("   (This will download ~420MB on first run)")
    cross_encoder = CrossEncoder(MODEL_NAME)

    sections_filtered = 0
    sections_passed = 0
    sections_processed = 0

    reader = NDJSONReader(str(input_file))

    with NDJSONWriter(str(output_file)) as writer:
        for section in tqdm(reader, desc="Filtering", unit="section"):
            section_id = section.get("id")
            text_plain = section.get("text_plain", "")

            if not section_id or not text_plain:
                continue

            # Skip if already processed
            if section_id in checkpoint["processed_ids"]:
                continue

            # Apply limit if specified
            if limit and sections_processed >= limit:
                break

            # Score section against reporting indicators
            score = score_section(cross_encoder, text_plain, REPORTING_INDICATORS)

            if score >= threshold:
                # Pass through to LLM stage
                writer.write({
                    "id": section_id,
                    "text": text_plain,
                    "cross_encoder_score": score,
                })
                sections_passed += 1
                checkpoint["passed_count"] += 1
                checkpoint["candidate_ids"].append(section_id)
            else:
                # Filter out (no LLM call needed)
                sections_filtered += 1
                checkpoint["filtered_count"] += 1

            # Mark as processed
            checkpoint["processed_ids"].add(section_id)
            sections_processed += 1

            # Save checkpoint every 50 sections
            if sections_processed % 50 == 0:
                save_checkpoint(checkpoint)

    return sections_filtered, sections_passed


def main():
    parser = argparse.ArgumentParser(
        description="Filter sections for reporting requirements using cross-encoder"
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
        help="Output NDJSON file (reporting candidates)"
    )
    parser.add_argument(
        "--threshold",
        type=float,
        default=CONFIDENCE_THRESHOLD,
        help=f"Confidence threshold for filtering (default: {CONFIDENCE_THRESHOLD})"
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

    logger.info(f"🔍 Filtering reporting candidates from {input_file}")
    logger.info(f"📊 Pipeline version: {PIPELINE_VERSION}")
    logger.info(f"🎯 Confidence threshold: {args.threshold}")
    logger.info(f"🤖 Model: {MODEL_NAME}")

    # Load checkpoint
    checkpoint = load_checkpoint()

    # Filter candidates
    sections_filtered, sections_passed = filter_candidates(
        input_file,
        output_file,
        checkpoint,
        threshold=args.threshold,
        limit=args.limit,
    )

    # Final checkpoint save
    save_checkpoint(checkpoint)

    # Calculate statistics
    total_processed = len(checkpoint["processed_ids"])
    pass_rate = (sections_passed / total_processed * 100) if total_processed > 0 else 0
    llm_savings = (sections_filtered / total_processed * 100) if total_processed > 0 else 0

    # Summary
    logger.info(f"\n✨ Filtering complete!")
    logger.info(f"📊 Statistics:")
    logger.info(f"  • Total sections processed: {total_processed}")
    logger.info(f"  • Candidates passed to LLM: {sections_passed} ({pass_rate:.1f}%)")
    logger.info(f"  • Sections filtered out: {sections_filtered} ({llm_savings:.1f}%)")
    logger.info(f"  • Estimated LLM savings: {llm_savings:.1f}% reduction in API calls")
    logger.info(f"\n📁 Output: {output_file}")

    return 0


if __name__ == "__main__":
    exit(main())
