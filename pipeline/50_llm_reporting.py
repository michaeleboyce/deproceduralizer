#!/usr/bin/env python3
"""
Detect reporting requirements in DC Code sections using LLM analysis.

Uses Gemini models (free tier) with fallback to Ollama phi4-mini to analyze
each section and identify whether it contains reporting, disclosure, or
documentation requirements.

Now refactored to use unified LLM client with Instructor for structured outputs.

Usage:
  python pipeline/50_llm_reporting.py \
    --in data/outputs/sections_subset.ndjson \
    --out data/outputs/reporting_subset.ndjson
"""

import argparse
import os
import pickle
from datetime import datetime
from pathlib import Path
from tqdm import tqdm
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Lock

from common import NDJSONReader, NDJSONWriter, setup_logging, validate_record, PIPELINE_VERSION
from llm_client import LLMClient
from models import ReportingRequirement

logger = setup_logging(__name__)

# Get number of workers from environment (default to 1 for serial execution)
WORKERS = int(os.getenv("PIPELINE_WORKERS", "1"))

CHECKPOINT_FILE = Path("data/interim/reporting.ckpt")
MAX_TEXT_LENGTH = 3000  # Truncate text to avoid token limits


def get_llm_analysis(text: str, section_id: str, client: LLMClient) -> tuple[ReportingRequirement, str]:
    """
    Analyze section using unified LLM client with structured outputs.

    Args:
        text: Section text to analyze
        section_id: Section ID for logging and output
        client: LLMClient instance

    Returns:
        (ReportingRequirement instance, model_used) or (None, "failed")
    """
    # Truncate text if too long
    truncated_text = text[:MAX_TEXT_LENGTH]
    if len(text) > MAX_TEXT_LENGTH:
        logger.debug(f"Truncated {section_id} from {len(text)} to {MAX_TEXT_LENGTH} chars")

    # Construct prompt
    prompt = f"""You are analyzing a legal code section for SUBSTANTIVE reporting requirements.

TASK: Determine if this section requires an entity to compile and submit regular reports, data, statistics, or documentation to an oversight body.

IMPORTANT: Only flag as has_reporting=true when you are CERTAIN the text describes a substantive reporting requirement. When uncertain or ambiguous, default to has_reporting=false. Be conservative in your assessment.

WHAT COUNTS AS REPORTING (set has_reporting=true):
- Regular/periodic reports (annual, quarterly, monthly reports)
- Submission of compiled data, statistics, or performance metrics
- Financial reporting or audits
- Documentation submitted to Council, Mayor, or oversight agencies
- Maintaining and publishing records or registries

WHAT DOES NOT COUNT (set has_reporting=false):
- Simple one-time notifications ("shall notify")
- Procedural notices ("provide written notice")
- Basic communication requirements
- Posting of signs or public notices
- Authority to remove/appoint without reporting element
- Ambiguous or unclear text that might suggest reporting but doesn't explicitly require it

SECTION TEXT:
{truncated_text}

GUIDELINES:
- Only flag has_reporting=true when the text CLEARLY and EXPLICITLY requires substantive reporting
- reporting_text: Extract the EXACT full text from the section that describes the reporting requirement. Include complete sentences that contain the requirement, not just fragments. Copy the text verbatim from the section.
- reporting_summary: Keep concise (1-2 sentences) and specific about WHAT is reported and TO WHOM
- tags: Use lowercase, focus on WHO reports (mayor, director, agency, board) and WHEN (annual, quarterly, monthly)
- highlight_phrases: Extract 2-5 key phrases that indicate substantive reporting (e.g., "shall submit a report", "publish statistics", "maintain records")
- When in doubt, err on the side of has_reporting=false

ANACHRONISM CHECK:
Also determine if this section contains any ANACHRONISTIC language that suggests the law may be outdated:
- Obsolete technology (telegram, typewriter, fax, etc.)
- Outdated terminology (fireman, mailman, colored, etc.)
- Historical discriminatory language (Jim Crow era terms)
- Defunct agencies or institutions
- Archaic measurements or units
- Gendered professional titles (policeman, chairman, etc.)
- Very old dollar amounts suggesting no inflation updates (e.g., "$5 fine")

Set **potential_anachronism** to true if ANY of these indicators are present, false otherwise.
"""

    response = client.generate(
        prompt=prompt,
        response_model=ReportingRequirement,
        section_id=section_id
    )

    if response:
        # Add section ID and metadata to the model
        response.data.id = section_id
        response.data.jurisdiction = "dc"
        response.data.metadata = {
            "model": response.model_used,
            "pipeline_version": PIPELINE_VERSION,
            "analyzed_at": datetime.utcnow().isoformat() + "Z"
        }
        return response.data, response.model_used

    return None, "failed"


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
        "processed_ids": set(),  # Set of processed section IDs
        "results": [],           # List of reporting records
        "model_usage": {}        # Dict mapping model name -> call count
    }


def save_checkpoint(checkpoint: dict):
    """Save checkpoint."""
    CHECKPOINT_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(CHECKPOINT_FILE, 'wb') as f:
        pickle.dump(checkpoint, f)
    logger.debug(f"Saved checkpoint: {len(checkpoint['processed_ids'])} sections processed")


def process_section(section: dict, client: LLMClient) -> tuple[dict | None, str, list]:
    """
    Process a single section and return the result.

    Args:
        section: Dict with "id" and "text" keys
        client: LLMClient instance

    Returns:
        (record_dict or None, model_used, tags_list)
    """
    section_id = section["id"]

    # Analyze with LLM using structured outputs
    analysis, model_used = get_llm_analysis(section["text"], section_id, client)

    if analysis is None:
        return None, "failed", []

    # Convert Pydantic model to dict for output
    record = {
        "id": analysis.id,
        "has_reporting": analysis.has_reporting,
        "reporting_summary": analysis.reporting_summary,
        "reporting_text": analysis.reporting_text,
        "tags": analysis.tags,
        "highlight_phrases": analysis.highlight_phrases,
        "potential_anachronism": analysis.potential_anachronism,
        "metadata": analysis.metadata
    }

    # Validate record
    required_fields = ["id", "has_reporting", "reporting_summary", "reporting_text", "tags", "highlight_phrases", "potential_anachronism", "metadata"]
    if not validate_record(record, required_fields):
        logger.error(f"Invalid record for {section_id}, skipping")
        return None, "failed", []

    # Return record, model used, and tags
    tags = record["tags"] if record["has_reporting"] else []
    return record, model_used, tags


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
        "--cascade-strategy",
        dest="cascade_strategy",
        choices=["simple", "extended"],
        default="extended",
        help="LLM cascade strategy: 'simple' (Gemini→Ollama) or 'extended' (Gemini→Groq→Ollama). Defaults to 'extended'."
    )

    args = parser.parse_args()

    input_file = Path(args.input_file)
    output_file = Path(args.out)

    if not input_file.exists():
        logger.error(f"Input file not found: {input_file}")
        return 1

    logger.info(f"Detecting reporting requirements in {input_file}")
    logger.info(f"Pipeline version: {PIPELINE_VERSION}")

    # Load checkpoint
    checkpoint = load_checkpoint()

    # Initialize LLM client with extended cascade strategy for reporting detection
    client = LLMClient(cascade_strategy=args.cascade_strategy)

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
    logger.info(f"Using {WORKERS} worker(s) for parallel processing")

    # Filter out already processed sections
    sections_to_process = [s for s in sections_to_process if s["id"] not in checkpoint["processed_ids"]]
    logger.info(f"{len(sections_to_process)} sections remaining to process")

    # Thread-safe checkpoint updates
    checkpoint_lock = Lock()

    # Process sections with progress bar
    with NDJSONWriter(str(output_file)) as writer:
        if WORKERS == 1:
            # Serial execution (original behavior)
            for section in tqdm(sections_to_process, desc="Analyzing sections", unit="section"):
                record, model_used, tags = process_section(section, client)

                if record is None:
                    failed_analyses += 1
                    with checkpoint_lock:
                        checkpoint["processed_ids"].add(section["id"])
                    continue

                # Track model usage
                if model_used != "failed":
                    with checkpoint_lock:
                        checkpoint["model_usage"][model_used] = checkpoint["model_usage"].get(model_used, 0) + 1

                # Write record
                writer.write(record)

                # Update statistics
                with checkpoint_lock:
                    checkpoint["processed_ids"].add(section["id"])
                    checkpoint["results"].append(record)
                sections_processed += 1

                if record["has_reporting"]:
                    sections_with_reporting += 1
                    all_tags.extend(tags)

                    # Log sample to console with colors
                    GREEN = '\033[92m'
                    CYAN = '\033[96m'
                    RESET = '\033[0m'
                    logger.info(f"\n{GREEN}📋 REPORTING REQUIREMENT FOUND:{RESET}")
                    logger.info(f"  {CYAN}Section:{RESET} {section['id']}")
                    logger.info(f"  {CYAN}Summary:{RESET} {record['reporting_summary']}")
                    logger.info(f"  {CYAN}Tags:{RESET} {', '.join(record['tags']) if record['tags'] else 'none'}")
                    logger.info(f"  {CYAN}Key Phrases:{RESET} {'; '.join(record['highlight_phrases'][:3]) if record['highlight_phrases'] else 'none'}")

                # Save checkpoint every 5 sections
                if sections_processed % 5 == 0:
                    with checkpoint_lock:
                        save_checkpoint(checkpoint)
        else:
            # Parallel execution with ThreadPoolExecutor
            with ThreadPoolExecutor(max_workers=WORKERS) as executor:
                # Submit all tasks
                future_to_section = {
                    executor.submit(process_section, section, client): section
                    for section in sections_to_process
                }

                # Process completed tasks with progress bar
                for future in tqdm(as_completed(future_to_section), total=len(sections_to_process), desc="Analyzing sections", unit="section"):
                    section = future_to_section[future]
                    section_id = section["id"]

                    try:
                        record, model_used, tags = future.result()

                        if record is None:
                            failed_analyses += 1
                            with checkpoint_lock:
                                checkpoint["processed_ids"].add(section_id)
                            continue

                        # Track model usage
                        if model_used != "failed":
                            with checkpoint_lock:
                                checkpoint["model_usage"][model_used] = checkpoint["model_usage"].get(model_used, 0) + 1

                        # Write record (writer is thread-safe)
                        writer.write(record)

                        # Update statistics
                        with checkpoint_lock:
                            checkpoint["processed_ids"].add(section_id)
                            checkpoint["results"].append(record)
                        sections_processed += 1

                        if record["has_reporting"]:
                            sections_with_reporting += 1
                            all_tags.extend(tags)

                            # Log sample to console with colors
                            GREEN = '\033[92m'
                            CYAN = '\033[96m'
                            RESET = '\033[0m'
                            logger.info(f"\n{GREEN}📋 REPORTING REQUIREMENT FOUND:{RESET}")
                            logger.info(f"  {CYAN}Section:{RESET} {section_id}")
                            logger.info(f"  {CYAN}Summary:{RESET} {record['reporting_summary']}")
                            logger.info(f"  {CYAN}Tags:{RESET} {', '.join(record['tags']) if record['tags'] else 'none'}")
                            logger.info(f"  {CYAN}Key Phrases:{RESET} {'; '.join(record['highlight_phrases'][:3]) if record['highlight_phrases'] else 'none'}")

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

    # Calculate statistics
    reporting_percentage = (sections_with_reporting / sections_processed * 100) if sections_processed > 0 else 0
    tag_counts = Counter(all_tags)

    logger.info(f"Analysis complete!")
    logger.info(f"  Total sections analyzed: {sections_processed}")
    logger.info(f"  Sections with reporting requirements: {sections_with_reporting} ({reporting_percentage:.1f}%)")
    logger.info(f"  Failed analyses: {failed_analyses}")

    # Show model usage
    logger.info(f"  Model usage:")
    for model, count in sorted(checkpoint["model_usage"].items()):
        logger.info(f"    {model}: {count} calls")

    logger.info(f"  Most common tags: {tag_counts.most_common(10)}")
    logger.info(f"  Output: {output_file}")

    # Print detailed LLM usage statistics
    stats_summary = client.get_stats_summary()
    print(stats_summary)

    return 0


if __name__ == "__main__":
    exit(main())
