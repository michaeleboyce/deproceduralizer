#!/usr/bin/env python3
"""
Stage 00: Section Deduplication Preprocessor

Detects near-duplicate sections using MinHash and creates a canonical mapping.
This reduces redundant LLM API calls in downstream stages (35, 50, 55, 60).

Output:
  - data/interim/section_deduplication_map.pkl: {section_id -> canonical_section_id}
  - data/interim/dedup_stats.json: Statistics about duplicate groups
"""

import sys
import json
import pickle
import hashlib
from pathlib import Path
from collections import defaultdict
from typing import Dict, List, Set
from datasketch import MinHash, MinHashLSH

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from common import (
    setup_logging,
    log_stage_header,
    load_sections_ndjson,
    save_json,
)

logger = setup_logging(__name__)


# MinHash parameters for near-duplicate detection
NUM_PERM = 128  # Number of permutations (higher = more accurate but slower)
SIMILARITY_THRESHOLD = 0.95  # 95% similarity to consider as duplicates

# Text truncation limits matching downstream stages
TRUNCATION_LIMITS = {
    "obligations": 2000,  # Stage 35
    "reporting": 3000,    # Stage 50
    "similarity": 2000,   # Stage 55 (per section in pair)
}

OUTPUT_MAP = Path("data/interim/section_deduplication_map.pkl")
OUTPUT_STATS = Path("data/interim/dedup_stats.json")


def tokenize_text(text: str) -> List[str]:
    """
    Tokenize text into words for MinHash.
    Simple whitespace-based tokenization with lowercasing.
    """
    return text.lower().split()


def create_minhash(text: str, num_perm: int = NUM_PERM) -> MinHash:
    """Create MinHash signature for given text."""
    minhash = MinHash(num_perm=num_perm)
    tokens = tokenize_text(text)
    for token in tokens:
        minhash.update(token.encode("utf-8"))
    return minhash


def detect_duplicates_for_limit(
    sections: List[dict],
    truncation_limit: int,
    threshold: float = SIMILARITY_THRESHOLD
) -> Dict[str, str]:
    """
    Detect near-duplicate sections using MinHash LSH.

    Args:
        sections: List of section dicts with 'id' and 'text_plain'
        truncation_limit: Character limit to truncate text (matches pipeline stages)
        threshold: Similarity threshold (0.0-1.0)

    Returns:
        Dict mapping section_id -> canonical_section_id for duplicates
    """
    logger.info(f"Detecting duplicates with {truncation_limit} char limit, threshold={threshold}")

    # Create LSH index (fresh for each truncation limit)
    lsh = MinHashLSH(threshold=threshold, num_perm=NUM_PERM)

    # Build MinHash signatures
    minhashes = {}
    for section in sections:
        section_id = section["id"]
        text = section["text_plain"][:truncation_limit]  # Match pipeline truncation

        # Skip very short sections
        if len(text.strip()) < 50:
            continue

        minhash = create_minhash(text)
        minhashes[section_id] = minhash
        # Use check_duplication=False to allow re-insertion across different limits
        lsh.insert(section_id, minhash, check_duplication=False)

    # Find duplicate groups
    duplicate_groups: List[Set[str]] = []
    processed = set()

    for section_id, minhash in minhashes.items():
        if section_id in processed:
            continue

        # Query LSH for similar sections
        similar = lsh.query(minhash)

        if len(similar) > 1:
            # Found a duplicate group
            duplicate_groups.append(set(similar))
            processed.update(similar)

    logger.info(f"Found {len(duplicate_groups)} duplicate groups")

    # Create canonical mapping (alphabetically first ID in each group)
    dedup_map = {}
    for group in duplicate_groups:
        canonical = sorted(group)[0]  # Pick first alphabetically as canonical
        for section_id in group:
            if section_id != canonical:
                dedup_map[section_id] = canonical

    return dedup_map


def merge_dedup_maps(maps: List[Dict[str, str]]) -> Dict[str, str]:
    """
    Merge multiple dedup maps (from different truncation limits).
    If a section appears in multiple maps, use the most conservative (shortest limit) mapping.
    """
    merged = {}

    # Process in order of truncation limit (shortest first)
    for dedup_map in maps:
        for section_id, canonical_id in dedup_map.items():
            if section_id not in merged:
                merged[section_id] = canonical_id

    return merged


def generate_stats(
    sections: List[dict],
    dedup_map: Dict[str, str],
    per_limit_maps: Dict[str, Dict[str, str]]
) -> dict:
    """Generate statistics about deduplication."""
    total_sections = len(sections)
    duplicate_sections = len(dedup_map)

    # Count canonical groups
    canonical_to_duplicates = defaultdict(list)
    for section_id, canonical_id in dedup_map.items():
        canonical_to_duplicates[canonical_id].append(section_id)

    num_groups = len(canonical_to_duplicates)

    # Group size distribution
    group_sizes = [len(dups) + 1 for dups in canonical_to_duplicates.values()]  # +1 for canonical
    max_group_size = max(group_sizes) if group_sizes else 0
    avg_group_size = sum(group_sizes) / len(group_sizes) if group_sizes else 0

    # Per-limit stats
    per_limit_stats = {}
    for limit_name, limit_map in per_limit_maps.items():
        per_limit_stats[limit_name] = {
            "duplicates_found": len(limit_map),
            "groups": len(set(limit_map.values())),
        }

    stats = {
        "total_sections": total_sections,
        "duplicate_sections": duplicate_sections,
        "unique_canonical_sections": total_sections - duplicate_sections,
        "deduplication_ratio": f"{(duplicate_sections / total_sections * 100):.1f}%",
        "duplicate_groups": num_groups,
        "max_group_size": max_group_size,
        "avg_group_size": f"{avg_group_size:.1f}",
        "estimated_llm_call_reduction": f"{(duplicate_sections / total_sections * 100):.1f}%",
        "per_truncation_limit": per_limit_stats,
        "parameters": {
            "num_perm": NUM_PERM,
            "similarity_threshold": SIMILARITY_THRESHOLD,
            "truncation_limits": TRUNCATION_LIMITS,
        },
    }

    return stats


def main():
    log_stage_header("00", "Section Deduplication Preprocessor")

    # Load all sections
    logger.info("Loading sections...")
    sections_file = None
    for candidate in ["data/outputs/sections_subset.ndjson", "data/outputs/sections_full.ndjson"]:
        if Path(candidate).exists():
            sections_file = candidate
            break

    if not sections_file:
        logger.error("No sections file found")
        sys.exit(1)

    sections = load_sections_ndjson(sections_file)
    logger.info(f"Loaded {len(sections)} sections from {sections_file}")

    # Detect duplicates at different truncation limits
    per_limit_maps = {}
    for limit_name, truncation_limit in sorted(TRUNCATION_LIMITS.items(), key=lambda x: x[1]):
        logger.info(f"\nDetecting duplicates for {limit_name} (limit={truncation_limit})...")
        dedup_map = detect_duplicates_for_limit(sections, truncation_limit, SIMILARITY_THRESHOLD)
        per_limit_maps[limit_name] = dedup_map
        logger.info(f"  Found {len(dedup_map)} duplicate mappings")

    # Merge maps (most conservative wins)
    logger.info("\nMerging deduplication maps...")
    final_map = merge_dedup_maps([per_limit_maps[name] for name in sorted(TRUNCATION_LIMITS.keys())])
    logger.info(f"Final deduplication map: {len(final_map)} mappings")

    # Generate statistics
    stats = generate_stats(sections, final_map, per_limit_maps)

    # Save dedup map
    OUTPUT_MAP.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_MAP, "wb") as f:
        pickle.dump(final_map, f)
    logger.info(f"\nSaved deduplication map to {OUTPUT_MAP}")

    # Save stats
    save_json(stats, OUTPUT_STATS)
    logger.info(f"Saved statistics to {OUTPUT_STATS}")

    # Print summary
    logger.info("\n" + "="*60)
    logger.info("DEDUPLICATION SUMMARY")
    logger.info("="*60)
    logger.info(f"Total sections: {stats['total_sections']}")
    logger.info(f"Duplicate sections: {stats['duplicate_sections']}")
    logger.info(f"Unique canonical sections: {stats['unique_canonical_sections']}")
    logger.info(f"Deduplication ratio: {stats['deduplication_ratio']}")
    logger.info(f"Duplicate groups: {stats['duplicate_groups']}")
    logger.info(f"Largest group size: {stats['max_group_size']}")
    logger.info(f"Average group size: {stats['avg_group_size']}")
    logger.info(f"Estimated LLM call reduction: {stats['estimated_llm_call_reduction']}")
    logger.info("="*60)


if __name__ == "__main__":
    main()
