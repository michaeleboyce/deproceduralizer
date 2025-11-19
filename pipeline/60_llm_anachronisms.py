#!/usr/bin/env python3
"""
Deep anachronism analysis for flagged DC Code sections.

Analyzes sections flagged as potentially containing anachronistic language
by the obligations and reporting pipelines. Performs comprehensive detection
across 18 indicator categories.

Usage:
  python pipeline/60_llm_anachronisms.py \
    --sections data/outputs/sections_subset.ndjson \
    --obligations data/outputs/obligations_enhanced_subset.ndjson \
    --reporting data/outputs/reporting_subset.ndjson \
    --out data/outputs/anachronisms_subset.ndjson
"""

import argparse
import os
import pickle
from datetime import datetime
from pathlib import Path
from typing import Set
from tqdm import tqdm
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Lock

from common import NDJSONReader, NDJSONWriter, setup_logging, validate_record, PIPELINE_VERSION
from llm_factory import create_llm_client, add_cascade_argument
from models import AnachronismAnalysis

logger = setup_logging(__name__)

# Get number of workers from environment (default to 1 for serial execution)
WORKERS = int(os.getenv("PIPELINE_WORKERS", "1"))

CHECKPOINT_FILE = Path("data/interim/anachronisms.ckpt")
MAX_TEXT_LENGTH = 3000  # Truncate text to avoid token limits


def collect_flagged_sections(
    obligations_file: Path,
    reporting_file: Path
) -> Set[str]:
    """
    Collect section IDs flagged as potentially anachronistic.

    Args:
        obligations_file: Path to obligations NDJSON file
        reporting_file: Path to reporting NDJSON file

    Returns:
        Set of section IDs flagged for anachronism analysis
    """
    flagged_sections = set()

    # Read obligations file
    if obligations_file and obligations_file.exists():
        logger.info(f"📂 Reading obligations from {obligations_file}")
        reader = NDJSONReader(str(obligations_file))
        for record in reader:
            if record.get("potential_anachronism", False):
                section_id = record.get("section_id")
                if section_id:
                    flagged_sections.add(section_id)

    # Read reporting file
    if reporting_file and reporting_file.exists():
        logger.info(f"📂 Reading reporting from {reporting_file}")
        reader = NDJSONReader(str(reporting_file))
        for record in reader:
            if record.get("potential_anachronism", False):
                section_id = record.get("id")
                if section_id:
                    flagged_sections.add(section_id)

    return flagged_sections


def analyze_anachronisms(
    text: str,
    section_id: str,
    client: LLMClient
) -> tuple[AnachronismAnalysis, str]:
    """
    Deep anachronism analysis using LLM with comprehensive indicator detection.

    Args:
        text: Section text to analyze
        section_id: Section ID for logging and output
        client: LLMClient instance

    Returns:
        (AnachronismAnalysis instance, model_used) or (None, "failed")
    """
    # Truncate text if too long
    truncated_text = text[:MAX_TEXT_LENGTH]
    if len(text) > MAX_TEXT_LENGTH:
        logger.debug(f"Truncated {section_id} from {len(text)} to {MAX_TEXT_LENGTH} chars")

    prompt = f"""You are a legal analyst identifying ANACHRONISTIC language in legal code sections.

SECTION TEXT:
{truncated_text}

TASK: Identify ALL anachronistic indicators in this section across the following categories:

**CRITICAL SEVERITY** (Unconstitutional/Discriminatory):
1. **jim_crow**: Racial classifications, segregation references, discriminatory terminology
   - Examples: "colored", "negro", "separate but equal", "mongolian race"

2. **outdated_social_structures**: Discriminatory family/social law
   - Examples: "illegitimate child", "bastard", "coverture", "paterfamilias"

3. **obsolete_legal_terms**: Offensive disability/mental health terms
   - Examples: "lunatic", "insane person", "idiot", "feeble-minded", "leper"

**HIGH SEVERITY** (Defunct Entities/Structures):
4. **defunct_agency**: References to abolished government agencies
   - Examples: "Immigration and Naturalization Service", "Atomic Energy Commission"

5. **outdated_education**: Segregated or discriminatory educational institutions
   - Examples: "colored school", "negro school", "separate schools"

**MEDIUM SEVERITY** (Outdated Terms/Technology):
6. **obsolete_technology**: Communication, recording, or data storage technology
   - Examples: "telegram", "telegraph", "typewriter", "carbon copy", "punch card"

7. **gendered_titles**: Gender-specific professional titles
   - Examples: "fireman", "policeman", "mailman", "chairman", "foreman"

8. **outdated_professions**: Historical occupations no longer practiced
   - Examples: "lamplighter", "iceman", "elevator operator", "buggy driver"

9. **outdated_medical_terms**: Obsolete disease/medical terminology
   - Examples: "consumption" (tuberculosis), "dropsy" (edema), "venereal disease"

10. **obsolete_transportation**: Historical transportation methods
    - Examples: "horse and buggy", "hitching post", "trolley car", "pneumatic tube"

11. **obsolete_military**: Cold War era civil defense, historical military terms
    - Examples: "civil defense shelter", "fallout shelter", "militia muster"

12. **prohibition_era**: Prohibition-related alcohol regulation
    - Examples: "intoxicating liquor", "speakeasy", "bootlegger", "dry county"

13. **obsolete_religious**: Religious-based regulation (blue laws)
    - Examples: "sabbath laws", "Sunday closing laws", "Lord's Day", "blasphemy"

**LOW SEVERITY** (Minor Updates Needed):
14. **archaic_measurements**: Historical measurement units
    - Examples: "rod", "perch", "furlong", "chain", "bushel", "hogshead"

15. **age_based**: Very old dates or extremely low dollar amounts
    - Examples: "before 1900", "$5 fine", "$10 penalty"

16. **environmental_agricultural**: Pre-EPA environmental terms, obsolete farming
    - Examples: "smoke abatement", "miasma", "bounty on wolves"

17. **commercial_business**: Obsolete commercial practices
    - Examples: "peddler", "hawker", "itinerant merchant", "warehouse receipts"

18. **obsolete_economic**: Historical currency or economic systems
    - Examples: "mills" (1/10 cent), "gold coin", "poll tax"

FOR EACH INDICATOR FOUND:
- **category**: One of the 18 categories above
- **severity**: CRITICAL, HIGH, MEDIUM, or LOW (based on category)
- **matched_phrases**: Array of exact phrases from the text (1-10 phrases)
- **modern_equivalent**: Suggested replacement (if applicable)
- **recommendation**: One of:
  - "REPEAL" - Unconstitutional or harmful (mostly CRITICAL severity)
  - "UPDATE" - Replace outdated terms (HIGH/MEDIUM severity)
  - "REVIEW" - Requires legal analysis (context-dependent)
  - "PRESERVE" - Historical reference only (rare)
- **explanation**: Why this is anachronistic and what it means (2-3 sentences)

OVERALL ANALYSIS:
- **has_anachronism**: true if ANY indicators found, false if none
- **overall_severity**: Highest severity among all indicators (CRITICAL > HIGH > MEDIUM > LOW)
- **summary**: Brief overview of all anachronistic content found (2-3 sentences)
- **requires_immediate_review**: true if ANY CRITICAL severity indicators found

IMPORTANT:
- Be thorough but precise - only flag genuinely anachronistic language
- matched_phrases should be exact quotes from the text
- If no anachronisms found, return has_anachronism=false with empty indicators array
- jurisdiction and section_id will be added automatically
"""

    response = client.generate(
        prompt=prompt,
        response_model=AnachronismAnalysis,
        section_id=section_id
    )

    if response:
        # Add section ID and metadata
        response.data.section_id = section_id
        response.data.jurisdiction = "dc"
        response.data.model_used = response.model_used
        response.data.analyzed_at = datetime.utcnow().isoformat() + "Z"
        return response.data, response.model_used

    return None, "failed"


def load_checkpoint() -> dict:
    """Load checkpoint if exists."""
    if CHECKPOINT_FILE.exists():
        logger.info(f"📂 Loading checkpoint from {CHECKPOINT_FILE}")
        with open(CHECKPOINT_FILE, 'rb') as f:
            checkpoint = pickle.load(f)
            if "model_usage" not in checkpoint:
                checkpoint["model_usage"] = {}
            return checkpoint

    return {
        "processed_ids": set(),
        "model_usage": {}
    }


def save_checkpoint(checkpoint: dict):
    """Save checkpoint."""
    CHECKPOINT_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(CHECKPOINT_FILE, 'wb') as f:
        pickle.dump(checkpoint, f)
    logger.debug(f"💾 Checkpoint saved: {len(checkpoint['processed_ids'])} sections processed")


def process_section(section_id: str, text: str, client: LLMClient) -> tuple[dict | None, str]:
    """
    Process a single section and return the result record.

    Args:
        section_id: Section ID
        text: Section text
        client: LLMClient instance

    Returns:
        (record_dict or None, model_used)
    """
    # Analyze with LLM
    analysis, model_used = analyze_anachronisms(text, section_id, client)

    if analysis is None:
        return None, "failed"

    # Convert to dict for output
    record = {
        "jurisdiction": analysis.jurisdiction,
        "section_id": analysis.section_id,
        "has_anachronism": analysis.has_anachronism,
        "overall_severity": analysis.overall_severity,
        "indicators": [
            {
                "category": ind.category,
                "severity": ind.severity,
                "matched_phrases": ind.matched_phrases,
                "modern_equivalent": ind.modern_equivalent,
                "recommendation": ind.recommendation,
                "explanation": ind.explanation
            }
            for ind in analysis.indicators
        ],
        "summary": analysis.summary,
        "requires_immediate_review": analysis.requires_immediate_review,
        "model_used": analysis.model_used,
        "analyzed_at": analysis.analyzed_at
    }

    return record, model_used


def main():
    parser = argparse.ArgumentParser(
        description="Deep anachronism analysis for flagged sections"
    )
    parser.add_argument(
        "--sections",
        required=True,
        help="Input NDJSON file (all sections)"
    )
    parser.add_argument(
        "--obligations",
        help="Obligations NDJSON file (for flagged sections)"
    )
    parser.add_argument(
        "--reporting",
        help="Reporting NDJSON file (for flagged sections)"
    )
    parser.add_argument(
        "--out",
        required=True,
        help="Output NDJSON file (anachronism analysis)"
    )
    parser.add_argument(
        "--limit",
        type=int,
        help="Limit number of sections to process (for testing)"
    )

    # Add cascade strategy argument using factory helper
    add_cascade_argument(parser)

    args = parser.parse_args()

    sections_file = Path(args.sections)
    obligations_file = Path(args.obligations) if args.obligations else None
    reporting_file = Path(args.reporting) if args.reporting else None
    output_file = Path(args.out)

    if not sections_file.exists():
        logger.error(f"❌ Sections file not found: {sections_file}")
        return 1

    logger.info(f"🔍 Deep anachronism analysis")
    logger.info(f"📊 Pipeline version: {PIPELINE_VERSION}")

    # Collect flagged sections
    logger.info(f"\n📋 Collecting flagged sections...")
    flagged_sections = collect_flagged_sections(obligations_file, reporting_file)
    logger.info(f"✅ Found {len(flagged_sections)} sections flagged for anachronism analysis")

    if len(flagged_sections) == 0:
        logger.warning("⚠️  No sections flagged - nothing to analyze")
        return 0

    # Load sections text
    logger.info(f"\n📂 Loading section text from {sections_file}")
    sections_text = {}
    reader = NDJSONReader(str(sections_file))
    for section in reader:
        section_id = section.get("id")
        text_plain = section.get("text_plain", "")
        if section_id and section_id in flagged_sections:
            sections_text[section_id] = text_plain

    logger.info(f"✅ Loaded {len(sections_text)} flagged section texts")

    # Load checkpoint
    checkpoint = load_checkpoint()

    # Initialize LLM client using factory (supports both rate_limited and error_driven strategies)
    client = create_llm_client(strategy=args.cascade_strategy)

    # Statistics
    sections_processed = 0
    sections_with_anachronisms = 0
    failed_analyses = 0
    severity_counts = Counter()
    category_counts = Counter()

    # Process sections
    logger.info(f"Using {WORKERS} worker(s) for parallel processing")

    sections_to_process = [(section_id, text) for section_id, text in sections_text.items() if section_id not in checkpoint["processed_ids"]]
    if args.limit:
        sections_to_process = sections_to_process[:args.limit]

    logger.info(f"{len(sections_to_process)} sections remaining to process")

    # Thread-safe checkpoint updates
    checkpoint_lock = Lock()

    with NDJSONWriter(str(output_file)) as writer:
        if WORKERS == 1:
            # Serial execution (original behavior)
            for section_id, text in tqdm(sections_to_process, desc="Analyzing", unit="section"):
                record, model_used = process_section(section_id, text, client)

                if record is None:
                    failed_analyses += 1
                    with checkpoint_lock:
                        checkpoint["processed_ids"].add(section_id)
                    continue

                # Track model usage
                if model_used != "failed":
                    with checkpoint_lock:
                        checkpoint["model_usage"][model_used] = checkpoint["model_usage"].get(model_used, 0) + 1

                # Write record
                writer.write(record)

                # Update statistics
                with checkpoint_lock:
                    checkpoint["processed_ids"].add(section_id)
                sections_processed += 1

                if record["has_anachronism"]:
                    sections_with_anachronisms += 1
                    severity_counts[record["overall_severity"]] += 1
                    for indicator in record["indicators"]:
                        category_counts[indicator["category"]] += 1

                    # Log critical findings
                    if record["overall_severity"] == "CRITICAL":
                        RED = '\033[91m'
                        YELLOW = '\033[93m'
                        RESET = '\033[0m'
                        logger.warning(f"\n{RED}⚠️  CRITICAL ANACHRONISM FOUND:{RESET}")
                        logger.warning(f"  {YELLOW}Section:{RESET} {section_id}")
                        logger.warning(f"  {YELLOW}Summary:{RESET} {record['summary']}")

                # Save checkpoint every 5 sections
                if sections_processed % 5 == 0:
                    with checkpoint_lock:
                        save_checkpoint(checkpoint)
        else:
            # Parallel execution with ThreadPoolExecutor
            with ThreadPoolExecutor(max_workers=WORKERS) as executor:
                # Submit all tasks
                future_to_section = {
                    executor.submit(process_section, section_id, text, client): section_id
                    for section_id, text in sections_to_process
                }

                # Process completed tasks with progress bar
                for future in tqdm(as_completed(future_to_section), total=len(sections_to_process), desc="Analyzing", unit="section"):
                    section_id = future_to_section[future]

                    try:
                        record, model_used = future.result()

                        if record is None:
                            failed_analyses += 1
                            with checkpoint_lock:
                                checkpoint["processed_ids"].add(section_id)
                            continue

                        # Track model usage
                        if model_used != "failed":
                            with checkpoint_lock:
                                checkpoint["model_usage"][model_used] = checkpoint["model_usage"].get(model_used, 0) + 1

                        # Write record
                        writer.write(record)

                        # Update statistics
                        with checkpoint_lock:
                            checkpoint["processed_ids"].add(section_id)
                        sections_processed += 1

                        if record["has_anachronism"]:
                            with checkpoint_lock:
                                sections_with_anachronisms += 1
                                severity_counts[record["overall_severity"]] += 1
                                for indicator in record["indicators"]:
                                    category_counts[indicator["category"]] += 1

                            # Log critical findings
                            if record["overall_severity"] == "CRITICAL":
                                RED = '\033[91m'
                                YELLOW = '\033[93m'
                                RESET = '\033[0m'
                                logger.warning(f"\n{RED}⚠️  CRITICAL ANACHRONISM FOUND:{RESET}")
                                logger.warning(f"  {YELLOW}Section:{RESET} {section_id}")
                                logger.warning(f"  {YELLOW}Summary:{RESET} {record['summary']}")

                        # Save checkpoint every 5 sections
                        if sections_processed % 5 == 0:
                            with checkpoint_lock:
                                save_checkpoint(checkpoint)

                    except Exception as e:
                        logger.error(f"Error processing {section_id}: {e}")
                        failed_analyses += 1
                        with checkpoint_lock:
                            checkpoint["processed_ids"].add(section_id)

    # Final checkpoint save
    save_checkpoint(checkpoint)

    # Summary
    anachronism_percentage = (sections_with_anachronisms / sections_processed * 100) if sections_processed > 0 else 0

    logger.info(f"\n✨ Analysis complete!")
    logger.info(f"📊 Statistics:")
    logger.info(f"  • Total sections analyzed: {sections_processed}")
    logger.info(f"  • Sections with anachronisms: {sections_with_anachronisms} ({anachronism_percentage:.1f}%)")
    logger.info(f"  • Failed analyses: {failed_analyses}")

    if sections_with_anachronisms > 0:
        logger.info(f"\n📈 Severity breakdown:")
        for severity in ["CRITICAL", "HIGH", "MEDIUM", "LOW"]:
            count = severity_counts.get(severity, 0)
            if count > 0:
                logger.info(f"    {severity}: {count}")

        logger.info(f"\n📂 Top 10 anachronism categories:")
        for category, count in category_counts.most_common(10):
            logger.info(f"    {category}: {count}")

    # Show model usage
    logger.info(f"\n🤖 Model usage:")
    for model, count in sorted(checkpoint["model_usage"].items()):
        logger.info(f"    {model}: {count} calls")

    logger.info(f"\n💾 Output written to {output_file}")

    return 0


if __name__ == "__main__":
    exit(main())
