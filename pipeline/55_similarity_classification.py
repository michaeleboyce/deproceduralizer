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
from typing import Dict, Optional
from tqdm import tqdm

import torch
from sentence_transformers import CrossEncoder

from common import NDJSONReader, NDJSONWriter, setup_logging, validate_record, PIPELINE_VERSION
from llm_client import LLMClient
from models import SimilarityClassification

logger = setup_logging(__name__)

CHECKPOINT_FILE = Path("data/interim/similarity_classification.ckpt")
MAX_TEXT_LENGTH = 2000  # Truncate each section text

# Initialize cross-encoder for triage (Model Cascading optimization)
# Load once at module level to avoid repeated loading
DEVICE = "mps" if torch.backends.mps.is_available() else "cpu"
logger.info(f"🚀 Initializing cross-encoder on {DEVICE} for triage...")
try:
    TRIAGE_MODEL = CrossEncoder('cross-encoder/nli-deberta-v3-xsmall', device=DEVICE)
    logger.info("✅ Cross-encoder loaded successfully")
except Exception as e:
    logger.warning(f"⚠️  Failed to load cross-encoder: {e}. Triage will be disabled.")
    TRIAGE_MODEL = None


def get_triage_classification(text_a: str, text_b: str) -> Optional[Dict[str, any]]:
    """
    Fast logical triage using NLI cross-encoder model.

    Uses Natural Language Inference to classify the relationship:
    - entailment: text_a implies text_b (potential duplicate/redundant)
    - contradiction: text_a contradicts text_b (potential conflict)
    - neutral: texts are related but neither implies nor contradicts (likely just related)

    Args:
        text_a: First section text
        text_b: Second section text

    Returns:
        Dict with keys:
            - label: str ('entailment', 'contradiction', 'neutral')
            - score: float (confidence 0.0 to 1.0)
        Returns None if triage model is unavailable.
    """
    if TRIAGE_MODEL is None:
        return None

    try:
        # Predict scores for [Contradiction, Entailment, Neutral]
        # Model returns array of 3 scores, one for each class
        scores = TRIAGE_MODEL.predict([(text_a, text_b)])[0]

        # Labels mapping for 'cross-encoder/nli-deberta-v3-xsmall'
        # Index 0: Contradiction, 1: Entailment, 2: Neutral
        labels = ["contradiction", "entailment", "neutral"]
        argmax_idx = scores.argmax()

        return {
            "label": labels[argmax_idx],
            "score": float(scores[argmax_idx])
        }
    except Exception as e:
        logger.error(f"Error during triage classification: {e}")
        return None


def classify_similarity(
    text_a: str,
    text_b: str,
    section_a_id: str,
    section_b_id: str,
    similarity_score: float,
    client: LLMClient,
    triage_context: Optional[Dict[str, any]] = None
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
        triage_context: Optional dict from cross-encoder triage with keys:
            - label: str ('entailment', 'contradiction', 'neutral')
            - score: float (confidence 0.0 to 1.0)

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

    # Map technical NLI labels to legal terms for the prompt
    hint = ""
    if triage_context:
        if triage_context["label"] == "entailment":
            hint = "\n⚠️  NOTE: A logic analysis suggests these sections may be DUPLICATES or REDUNDANT (one implies the other).\nPlease verify and provide a detailed classification.\n"
        elif triage_context["label"] == "contradiction":
            hint = "\n⚠️  NOTE: A logic analysis suggests these sections may be CONFLICTING (contradictory requirements).\nPlease verify and identify specific contradictions.\n"

    # Construct prompt
    prompt = f"""You are analyzing two similar DC Code sections to classify their relationship.
{hint}

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

        # Add cross-encoder triage metadata if available
        if triage_context:
            response.data.cross_encoder_label = triage_context["label"]
            response.data.cross_encoder_score = triage_context["score"]

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
    parser.add_argument(
        "--cascade-strategy",
        dest="cascade_strategy",
        choices=["simple", "extended"],
        default="extended",
        help="LLM cascade strategy: 'simple' (Gemini→Ollama) or 'extended' (Gemini→Groq→Ollama). Defaults to 'extended'."
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

    # Load sections into memory
    sections = load_sections(sections_file)

    # Load checkpoint
    checkpoint = load_checkpoint()

    # Initialize LLM client with extended cascade strategy for similarity classification
    client = LLMClient(cascade_strategy=args.cascade_strategy)

    # Statistics
    pairs_processed = 0
    failed_classifications = 0
    triage_skipped = 0  # Count of pairs that skipped LLM via triage
    triage_graduated = 0  # Count of pairs graduated to LLM

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

            # STEP 1: FAST PASS - Cross-Encoder Triage (Model Cascading)
            triage = get_triage_classification(text_a, text_b)

            # STEP 2: FILTER - If neutral (just "related") with high confidence, skip LLM
            if triage and triage["label"] == "neutral" and triage["score"] > 0.5:
                logger.debug(f"Triage: {section_a}-{section_b} → neutral ({triage['score']:.2f}), skipping LLM")

                # Create "related" classification automatically
                record = {
                    "section_a": section_a,
                    "section_b": section_b,
                    "similarity": similarity,
                    "classification": "related",
                    "explanation": f"Automated logic check deemed these sections related but not conflicting (Confidence: {triage['score']:.2f}). No duplicate, superseded, or conflicting relationship detected.",
                    "model_used": "cross-encoder-xsmall",
                    "analyzed_at": datetime.utcnow().isoformat() + "Z",
                    "cross_encoder_label": triage["label"],
                    "cross_encoder_score": triage["score"]
                }

                writer.write(record)
                checkpoint["processed_pairs"].add(pair_key)
                pairs_processed += 1
                triage_skipped += 1

                # Save checkpoint every 10 pairs
                if pairs_processed % 10 == 0:
                    save_checkpoint(checkpoint)

                continue  # <--- PERFORMANCE WIN: Skip expensive LLM call

            # STEP 3: GRADUATE - Entailment/Contradiction flagged → send to LLM for verification
            if triage and triage["label"] in ["entailment", "contradiction"]:
                logger.debug(f"Triage: {section_a}-{section_b} → {triage['label']} ({triage['score']:.2f}), graduating to LLM")
                triage_graduated += 1

            # Classify with LLM using structured outputs (with triage context if available)
            result, model_used = classify_similarity(
                text_a, text_b, section_a, section_b, similarity, client,
                triage_context=triage
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

            # Add cross-encoder triage metadata if available
            if result.cross_encoder_label:
                record["cross_encoder_label"] = result.cross_encoder_label
            if result.cross_encoder_score is not None:
                record["cross_encoder_score"] = result.cross_encoder_score

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

            # Log sample to console every 10th pair with colors
            if pairs_processed % 10 == 0:
                BLUE = '\033[94m'
                CYAN = '\033[96m'
                YELLOW = '\033[93m'
                RESET = '\033[0m'
                logger.info(f"\n{BLUE}🔗 SIMILARITY CLASSIFICATION SAMPLE:{RESET}")
                logger.info(f"  {CYAN}Pair:{RESET} {section_a} ↔ {section_b}")
                logger.info(f"  {CYAN}Similarity:{RESET} {similarity:.3f}")
                logger.info(f"  {CYAN}Classification:{RESET} {YELLOW}{record['classification']}{RESET}")
                logger.info(f"  {CYAN}Explanation:{RESET} {record['explanation'][:150]}..." if len(record['explanation']) > 150 else f"  {CYAN}Explanation:{RESET} {record['explanation']}")
                logger.info(f"  {CYAN}Model:{RESET} {model_used}")

            # Save checkpoint every 10 pairs
            if pairs_processed % 10 == 0:
                save_checkpoint(checkpoint)

    # Final checkpoint save
    save_checkpoint(checkpoint)

    # Print statistics
    logger.info(f"Classification complete!")
    logger.info(f"  Total pairs classified: {pairs_processed}")
    logger.info(f"  Failed classifications: {failed_classifications}")

    # Show triage performance (Model Cascading stats)
    if TRIAGE_MODEL:
        triage_total = triage_skipped + triage_graduated
        if triage_total > 0:
            skip_rate = (triage_skipped / triage_total) * 100
            logger.info(f"")
            logger.info(f"  🚀 Cross-Encoder Triage Performance:")
            logger.info(f"    Pairs filtered (neutral → related): {triage_skipped}")
            logger.info(f"    Pairs graduated (conflict/duplicate → LLM): {triage_graduated}")
            logger.info(f"    Skip rate: {skip_rate:.1f}% (LLM calls avoided)")

    # Show model usage
    logger.info(f"")
    logger.info(f"  Model usage:")
    if checkpoint["model_usage"]:
        for model, count in sorted(checkpoint["model_usage"].items(), key=lambda x: x[1], reverse=True):
            logger.info(f"    {model}: {count} calls")
    if triage_skipped > 0:
        logger.info(f"    cross-encoder-xsmall: {triage_skipped} auto-classifications")

    logger.info(f"")
    logger.info(f"  Output: {output_file}")

    # Show classification distribution
    if checkpoint["results"]:
        from collections import Counter
        classifications = [r["classification"] for r in checkpoint["results"]]
        distribution = Counter(classifications)
        logger.info(f"  Classification distribution: {dict(distribution)}")

    # Print detailed LLM usage statistics
    stats_summary = client.get_stats_summary()
    print(stats_summary)

    return 0


if __name__ == "__main__":
    exit(main())
