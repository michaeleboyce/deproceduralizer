#!/usr/bin/env python3
"""
Classify similarity relationships between DC Code sections using LLM analysis.

Uses Gemini models (free tier) with fallback to Ollama phi4-mini to classify
why similar sections are related: duplicate, superseded, related, or conflicting.

Now refactored to use unified LLM client with Instructor for structured outputs.

Usage:
  python pipeline/55_similarity_classification.py \
    --similarities data/outputs/similarities_subset.ndjson \
    --sections data/outputs/sections_subset.ndjson \
    --out data/outputs/similarity_classifications_subset.ndjson
"""

import argparse
import pickle
from datetime import datetime
from pathlib import Path
from typing import Dict
from tqdm import tqdm

from common import NDJSONReader, NDJSONWriter, setup_logging, validate_record, PIPELINE_VERSION
from llm_client import LLMClient
from models import SimilarityClassification

logger = setup_logging(__name__)

CHECKPOINT_FILE = Path("data/interim/similarity_classification.ckpt")
MAX_TEXT_LENGTH = 2000  # Truncate each section text


def classify_similarity(
    text_a: str,
    text_b: str,
    section_a_id: str,
    section_b_id: str,
    similarity_score: float,
    client: LLMClient
) -> tuple[SimilarityClassification, str]:
    """
    Classify similarity relationship using unified LLM client with structured outputs.

    Args:
        text_a: First section text
        text_b: Second section text
        section_a_id: First section ID
        section_b_id: Second section ID
        similarity_score: Cosine similarity score
        client: LLMClient instance

    Returns:
        (SimilarityClassification instance, model_used) or (None, "failed")
    """
    # Truncate texts if too long
    truncated_a = text_a[:MAX_TEXT_LENGTH]
    truncated_b = text_b[:MAX_TEXT_LENGTH]

    if len(text_a) > MAX_TEXT_LENGTH:
        logger.debug(f"Truncated section A ({section_a_id}) from {len(text_a)} to {MAX_TEXT_LENGTH} chars")
    if len(text_b) > MAX_TEXT_LENGTH:
        logger.debug(f"Truncated section B ({section_b_id}) from {len(text_b)} to {MAX_TEXT_LENGTH} chars")

    # Construct prompt
    prompt = f"""You are analyzing two similar DC Code sections to classify their relationship.

SECTION A ({section_a_id}):
{truncated_a}

SECTION B ({section_b_id}):
{truncated_b}

TASK: Classify the relationship between these sections into ONE of these categories:

1. **duplicate** - Nearly identical provisions that could be consolidated
2. **superseded** - One section appears to replace or update the other
3. **related** - Cover similar topics but serve different purposes
4. **conflicting** - Similar language but contradictory requirements

GUIDELINES:
- Be specific about what makes them similar or different
- Note any procedural, substantive, or temporal relationships
- For "superseded", note evidence like effective dates or explicit replacements
- For "conflicting", note specific contradictions
- Explanation should be 2-3 sentences explaining why this classification was chosen
"""

    response = client.generate(
        prompt=prompt,
        response_model=SimilarityClassification,
        section_id=f"{section_a_id}-{section_b_id}"
    )

    if response:
        # Add required fields to the model
        response.data.jurisdiction = "dc"
        response.data.section_a = section_a_id
        response.data.section_b = section_b_id
        response.data.similarity = similarity_score
        response.data.model_used = response.model_used
        response.data.analyzed_at = datetime.utcnow().isoformat() + "Z"
        return response.data, response.model_used

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
    logger.info(f"Using unified LLM client with Instructor validation")

    # Load sections into memory
    sections = load_sections(sections_file)

    # Load checkpoint
    checkpoint = load_checkpoint()

    # Initialize LLM client
    client = LLMClient()

    # Statistics
    pairs_processed = 0
    failed_classifications = 0

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

    # Sort by similarity (descending) - process most similar pairs first
    pairs_to_process.sort(key=lambda x: x["similarity"], reverse=True)

    total_pairs = len(pairs_to_process)
    logger.info(f"Found {total_pairs} similarity pairs to classify")
    if total_pairs > 0:
        logger.info(f"Processing most similar first (range: {pairs_to_process[0]['similarity']:.3f} to {pairs_to_process[-1]['similarity']:.3f})")

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

            # Classify with LLM using structured outputs
            result, model_used = classify_similarity(
                text_a, text_b, section_a, section_b, similarity, client
            )

            if result is None:
                failed_classifications += 1
                checkpoint["processed_pairs"].add(pair_key)
                continue

            # Track model usage
            if model_used != "failed":
                checkpoint["model_usage"][model_used] = checkpoint["model_usage"].get(model_used, 0) + 1

            # Convert Pydantic model to dict for output
            record = {
                "section_a": result.section_a,
                "section_b": result.section_b,
                "similarity": result.similarity,
                "classification": result.classification,
                "explanation": result.explanation,
                "model_used": result.model_used,
                "analyzed_at": result.analyzed_at,
                "metadata": result.metadata or {"pipeline_version": PIPELINE_VERSION}
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
