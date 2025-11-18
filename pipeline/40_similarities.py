#!/usr/bin/env python3
"""
Compute semantic similarity between DC Code sections using embeddings.

Uses Ollama's nomic-embed-text model to generate embeddings, then FAISS
to compute cosine similarity between all section pairs.

Usage:
  python pipeline/40_similarities.py \
    --in data/outputs/sections_subset.ndjson \
    --out data/outputs/similarities_subset.ndjson \
    --top-k 10 \
    --min-similarity 0.7
"""

import argparse
import json
import pickle
import requests
import numpy as np
import faiss
from pathlib import Path
from tqdm import tqdm

from common import NDJSONReader, NDJSONWriter, setup_logging

logger = setup_logging(__name__)

OLLAMA_HOST = "http://localhost:11434"
CHECKPOINT_FILE = Path("data/interim/similarities.ckpt")


def get_embedding(text: str, model: str = "nomic-embed-text") -> np.ndarray:
    """
    Get embedding vector from Ollama.

    Args:
        text: Text to embed
        model: Ollama model name

    Returns:
        Embedding vector as numpy array
    """
    try:
        response = requests.post(
            f"{OLLAMA_HOST}/api/embeddings",
            json={
                "model": model,
                "prompt": text
            },
            timeout=30
        )
        response.raise_for_status()
        data = response.json()

        embedding = np.array(data["embedding"], dtype=np.float32)
        return embedding

    except requests.exceptions.RequestException as e:
        logger.error(f"Error calling Ollama API: {e}")
        raise
    except (KeyError, ValueError) as e:
        logger.error(f"Error parsing Ollama response: {e}")
        raise


def load_checkpoint() -> dict:
    """Load checkpoint if exists."""
    if CHECKPOINT_FILE.exists():
        logger.info(f"Loading checkpoint from {CHECKPOINT_FILE}")
        with open(CHECKPOINT_FILE, 'rb') as f:
            return pickle.load(f)

    return {
        "embeddings": [],      # List of (section_id, embedding) tuples
        "processed_ids": set(), # Set of processed section IDs
        "section_data": []     # List of (section_id, citation, heading) tuples
    }


def save_checkpoint(checkpoint: dict):
    """Save checkpoint."""
    CHECKPOINT_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(CHECKPOINT_FILE, 'wb') as f:
        pickle.dump(checkpoint, f)
    logger.debug(f"Saved checkpoint: {len(checkpoint['embeddings'])} embeddings")


def main():
    parser = argparse.ArgumentParser(
        description="Compute semantic similarity between DC Code sections"
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
        help="Output NDJSON file (similarities)"
    )
    parser.add_argument(
        "--top-k",
        type=int,
        default=10,
        help="Number of similar sections to find per section"
    )
    parser.add_argument(
        "--min-similarity",
        type=float,
        default=0.7,
        help="Minimum similarity threshold (0.0 to 1.0)"
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

    logger.info(f"Computing similarities for sections in {input_file}")
    logger.info(f"Parameters: top_k={args.top_k}, min_similarity={args.min_similarity}")

    # Load checkpoint
    checkpoint = load_checkpoint()

    # Step 1: Generate embeddings for all sections
    logger.info("Step 1: Generating embeddings...")

    reader = NDJSONReader(str(input_file))
    sections_to_process = []

    for section in reader:
        section_id = section.get("id")
        text_plain = section.get("text_plain", "")
        citation = section.get("citation", "")
        heading = section.get("heading", "")

        if not section_id or not text_plain:
            continue

        sections_to_process.append({
            "id": section_id,
            "text": text_plain,
            "citation": citation,
            "heading": heading
        })

        # Apply limit if specified
        if args.limit and len(sections_to_process) >= args.limit:
            break

    total_sections = len(sections_to_process)
    logger.info(f"Found {total_sections} sections to process")

    # Generate embeddings with progress bar
    for section in tqdm(sections_to_process, desc="Generating embeddings", unit="section"):
        section_id = section["id"]

        # Skip if already processed
        if section_id in checkpoint["processed_ids"]:
            continue

        try:
            # Get embedding from Ollama
            embedding = get_embedding(section["text"])

            # Store embedding and metadata
            checkpoint["embeddings"].append((section_id, embedding))
            checkpoint["section_data"].append((section_id, section["citation"], section["heading"]))
            checkpoint["processed_ids"].add(section_id)

            # Save checkpoint every 10 sections
            if len(checkpoint["embeddings"]) % 10 == 0:
                save_checkpoint(checkpoint)

        except Exception as e:
            logger.error(f"Failed to get embedding for {section_id}: {e}")
            continue

    # Final checkpoint save
    save_checkpoint(checkpoint)

    logger.info(f"Generated {len(checkpoint['embeddings'])} embeddings")

    if len(checkpoint["embeddings"]) == 0:
        logger.error("No embeddings generated, cannot compute similarities")
        return 1

    # Step 2: Build FAISS index and compute similarities
    logger.info("Step 2: Computing similarities with FAISS...")

    # Extract embeddings and IDs
    section_ids = [item[0] for item in checkpoint["embeddings"]]
    embeddings_list = [item[1] for item in checkpoint["embeddings"]]

    # Convert to numpy matrix
    embeddings_matrix = np.vstack(embeddings_list).astype('float32')
    logger.info(f"Embeddings matrix shape: {embeddings_matrix.shape}")

    # Normalize for cosine similarity
    faiss.normalize_L2(embeddings_matrix)

    # Build FAISS index (Inner Product = cosine similarity after normalization)
    dimension = embeddings_matrix.shape[1]
    index = faiss.IndexFlatIP(dimension)
    index.add(embeddings_matrix)

    # Search for similar sections
    k = min(args.top_k + 1, len(section_ids))  # +1 to account for self-match
    similarities, indices = index.search(embeddings_matrix, k)

    logger.info(f"Computed similarities for {len(section_ids)} sections")

    # Step 3: Write similarity pairs to NDJSON
    logger.info("Step 3: Writing similarity pairs...")

    pairs_written = 0
    pairs_filtered = 0

    with NDJSONWriter(str(output_file)) as writer:
        for i, section_id_a in enumerate(section_ids):
            # Get top-k similar sections for this section
            for j in range(k):
                neighbor_idx = indices[i][j]
                similarity_score = float(similarities[i][j])

                section_id_b = section_ids[neighbor_idx]

                # Skip self-matches
                if section_id_a == section_id_b:
                    continue

                # Filter by minimum similarity
                if similarity_score < args.min_similarity:
                    pairs_filtered += 1
                    continue

                # Ensure alphabetical ordering to avoid duplicates
                # Only write if section_a < section_b
                if section_id_a < section_id_b:
                    record = {
                        "section_a": section_id_a,
                        "section_b": section_id_b,
                        "similarity": similarity_score
                    }
                    writer.write(record)
                    pairs_written += 1

    logger.info(f"Similarity computation complete!")
    logger.info(f"  Total pairs written: {pairs_written}")
    logger.info(f"  Pairs filtered (below threshold): {pairs_filtered}")
    logger.info(f"  Average pairs per section: {pairs_written / len(section_ids):.2f}")
    logger.info(f"  Output: {output_file}")

    return 0


if __name__ == "__main__":
    exit(main())
