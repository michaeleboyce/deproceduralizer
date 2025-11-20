#!/usr/bin/env python3
"""
Pahlka implementation analysis for DC Code sections.

Analyzes sections for implementation complexity and alignment with Jennifer Pahlka's
"recoding government" principles from "Recoding America".

Identifies patterns that create implementation burdens, process bloat, or separation
between policy and delivery.

Usage:
  python pipeline/70_llm_pahlka_implementation.py \
    --sections data/outputs/sections_1000.ndjson \
    --obligations data/outputs/obligations_enhanced_1000.ndjson \
    --reporting data/outputs/reporting_1000.ndjson \
    --out data/outputs/pahlka_implementation_1000.ndjson
"""

import argparse
import os
import pickle
import signal
import sys
from datetime import datetime
from pathlib import Path
from typing import Set
from tqdm import tqdm
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Lock

from common import NDJSONReader, NDJSONWriter, setup_logging, validate_record, PIPELINE_VERSION
from llm_factory import create_llm_client, add_cascade_argument
from models import PahlkaImplementationAnalysis

logger = setup_logging(__name__)

# Global flag for graceful shutdown
_shutdown_requested = False


def signal_handler(signum, frame):
    """Handle shutdown signals - exit immediately after saving checkpoint."""
    global _shutdown_requested
    if _shutdown_requested:
        # Second Ctrl+C - force exit immediately
        logger.error("Force quit requested, exiting without saving...")
        sys.exit(1)

    logger.warning(f"\nReceived interrupt signal, saving checkpoint and exiting...")
    _shutdown_requested = True

# Get number of workers from environment (default to 1 for serial execution)
WORKERS = int(os.getenv("PIPELINE_WORKERS", "1"))

CHECKPOINT_FILE = Path("data/interim/pahlka_implementation.ckpt")
MAX_TEXT_LENGTH = 3000  # Truncate text to avoid token limits

# Lightweight keyword scan for implementation-related sections
IMPLEMENTATION_KEYWORDS = [
    # Process/procedure keywords
    "implement", "establish", "adopt", "promulgate", "procedure", "process",
    "requirements", "ensure", "compliance", "adopt regulations",
    # Administrative burden indicators
    "notarized", "notary", "certified", "original document", "in person",
    "appear", "wet signature", "sworn", "affidavit", "attestation",
    # Technology keywords
    "system", "portal", "website", "electronic", "digital", "online",
    "pdf", "format", "technology", "database", "platform",
    # Compliance/oversight
    "audit", "report", "certify", "verify", "inspector general",
    "comptroller", "oversight", "deviation",
    # Cross-references (complexity)
    "section", "subsection", "title", "chapter", "U.S.C.",
]


def collect_flagged_sections(
    obligations_file: Path,
    reporting_file: Path
) -> Set[str]:
    """
    Collect section IDs flagged for implementation analysis.

    Analyzes sections with:
    - Reporting requirements (likely to have implementation language)
    - Obligations (deadlines, constraints, allocations)

    Args:
        obligations_file: Path to obligations NDJSON file
        reporting_file: Path to reporting NDJSON file

    Returns:
        Set of section IDs to analyze
    """
    flagged_sections = set()

    # Collect from obligations (sections with deadlines/amounts/constraints)
    logger.info("Collecting sections from obligations file...")
    if obligations_file.exists():
        reader = NDJSONReader(str(obligations_file))
        for record in reader:
            section_id = record.get("section_id")
            if section_id:
                flagged_sections.add(section_id)

    # Collect from reporting (sections with reporting requirements)
    logger.info("Collecting sections from reporting file...")
    if reporting_file.exists():
        reader = NDJSONReader(str(reporting_file))
        for record in reader:
            section_id = record.get("section_id")
            has_reporting = record.get("has_reporting", False)
            if section_id and has_reporting:
                flagged_sections.add(section_id)

    logger.info(f"Collected {len(flagged_sections)} flagged sections")
    return flagged_sections


def has_implementation_keywords(text: str) -> bool:
    """Quick keyword scan for implementation-related language."""
    text_lower = text.lower()
    return any(keyword in text_lower for keyword in IMPLEMENTATION_KEYWORDS)


def load_checkpoint() -> dict:
    """Load checkpoint data if it exists."""
    if CHECKPOINT_FILE.exists():
        try:
            with open(CHECKPOINT_FILE, 'rb') as f:
                return pickle.load(f)
        except Exception as e:
            logger.warning(f"Failed to load checkpoint: {e}; starting fresh")
    return {
        'processed_ids': set(),
        'version': PIPELINE_VERSION
    }


def save_checkpoint(checkpoint: dict):
    """Save checkpoint data."""
    CHECKPOINT_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(CHECKPOINT_FILE, 'wb') as f:
        pickle.dump(checkpoint, f)
    logger.debug(f"Saved checkpoint: {len(checkpoint['processed_ids'])} processed")


def build_analysis_prompt(section_text: str, citation: str, heading: str) -> str:
    """
    Build comprehensive Pahlka implementation analysis prompt with pattern library examples.
    """
    return f"""Analyze this DC Code section for implementation complexity using Jennifer Pahlka's framework from "Recoding America".

SECTION INFO:
Citation: {citation}
Heading: {heading}

SECTION TEXT:
{section_text}

---

ANALYSIS FRAMEWORK - 12 CATEGORIES:

1. COMPLEXITY_POLICY_DEBT - Cross-reference spaghetti, accreted conditions
   RED FLAG EXAMPLE: "meets criteria in section 202(b)(3)(A)(ii); satisfies 26 U.S.C. 3304(a)(1)(B)"
   BETTER: "household income is below 150% of federal poverty level"
   DETECT: Multiple section references, USC citations, subsection chains, "in addition to all other requirements"

2. OPTIONS_BECOME_REQUIREMENTS - Suggestion lists become checklists
   RED FLAG EXAMPLE: "may include...all controls identified in NIST Special Publication 800-53"
   BETTER: "shall adopt controls proportionate to data sensitivity...not required to adopt every listed control"
   DETECT: "may include...all", undifferentiated factor lists, exhaustive option menus

3. POLICY_IMPLEMENTATION_SEPARATION - Waterfall, vendor lock-in
   RED FLAG EXAMPLE: "shall establish through contracts with private entities...shall not directly develop or operate"
   BETTER: "shall designate accountable official responsible for how service works...may use contractors but retain ability to change"
   DETECT: Vendor mandates, waterfall language, separation of design/operations

4. OVERWROUGHT_LEGALESE - Dense definitions that make forms impossible
   RED FLAG EXAMPLE: "gross unearned income as defined in subsection (k)(2)(B)...per Internal Revenue Code §152"
   BETTER: "ask in plain language about money from work and other sources like Social Security, pensions"
   DETECT: Tax code references, nested definitions, legalese that can't be translated to plain forms

5. CASCADE_OF_RIGIDITY - Conflicting absolute goals
   RED FLAG EXAMPLE: "shall maximize access AND minimize improper payments AND ensure uniform administration AND promote personal responsibility AND avoid any potential misuse"
   BETTER: "main goals: (1) people who qualify can get benefits, (2) limit serious abuse. Balance: don't reduce access unless preventing larger harm"
   DETECT: Multiple unprioritized absolute goals, "comply with all applicable", "ensure", "maximize", "minimize" without trade-offs

6. MANDATED_STEPS_NOT_OUTCOMES - Procedure-heavy vs outcome-focused
   RED FLAG EXAMPLE: "require Form X-100 in PDF format...upload all documents in PDF...issue decision within 90 days of receipt of completed Form X-100"
   BETTER: "decide 90% of complete applications within 10 days...may change forms and formats to improve use"
   DETECT: Hard-coded forms/formats, specific tech requirements (PDF, portals, CMS), step checklists instead of metrics

7. ADMINISTRATIVE_BURDENS - Friction: notaries, wet signatures, in-person
   RED FLAG EXAMPLE: "certified birth certificate...notarized affidavit...appear in person every 3 months...original documents...satisfied within 7 days failing which application shall be denied"
   BETTER: "accept any reasonable proof...use existing government records...recertify by mail/online/phone...30 days to respond...multiple contact attempts before denial"
   DETECT: "notarized", "certified", "original", "in person", "wet signature", "appear", "sworn", recurring appearances, unrealistic deadlines, denial by default

8. NO_FEEDBACK_LOOPS - One-shot design, no iteration
   RED FLAG EXAMPLE: "program authorized for 10 years...Comptroller General shall submit report after 9 years"
   BETTER: "Secretary may run pilots to simplify forms...track completion rates and time to decision...if trial helps people get benefits without major errors, extend nationwide...regularly ask frontline staff which rules cause problems"
   DETECT: No pilot authority, no iteration language, one final report, no user testing, no field feedback mechanisms

9. PROCESS_WORSHIP_OVERSIGHT - Compliance-only audits
   RED FLAG EXAMPLE: "Inspector General shall audit compliance with each requirement...report any deviations however minor...any employee authorizing deviation may be subject to disciplinary action"
   BETTER: "IG shall examine whether program reaches qualifying people AND whether rules are reasonable...when agency departs from procedures, consider whether change helped people get benefits or solved documented problem"
   DETECT: Audit "all requirements", punish "any deviation", no outcome focus, blame-oriented language

10. ZERO_RISK_LANGUAGE - Impossible absolutes
    RED FLAG EXAMPLE: "shall take all necessary measures to ensure that no improper payments occur...ensure that no unauthorized access ever occurs"
    BETTER: "use reasonable steps to reduce errors and abuse, recognizing eliminating every small error would keep qualifying people from help...manage security so serious breaches are unlikely and systems remain available"
    DETECT: "ensure no X occurs", "never", "all necessary measures", "zero", absolutes that ignore trade-offs

11. FROZEN_TECHNOLOGY - Hard-coded architectures, formats, platforms
    RED FLAG EXAMPLE: "create website at www.benefits2025.gov using commercial CMS and enterprise service bus architecture...provide downloadable PDF forms...optimized for desktop web browsers"
    BETTER: "provide online service on .gov domain that allows people to see eligibility, apply, check status...usable on mobile devices...Secretary may change underlying technology"
    DETECT: Named systems/architectures (ESB, specific CMS), hard-coded formats (PDF only), specific URLs, browser requirements, vendor names

12. IMPLEMENTATION_OPPORTUNITY - POSITIVE patterns
    GOOD EXAMPLES:
    - "decide 90% of applications within 10 days" (concrete delivery metric)
    - "Secretary shall design forms so most people can complete on mobile phone" (burden reduction)
    - "Secretary may test simpler ways and keep versions that help qualifying people" (iteration authority)
    - "every 5 years review rules and recommend which can be removed because they add steps without improving results" (cleanup)
    - "identify groups where qualifying people aren't getting benefits and propose changes to close gaps" (outcome focus)
    DETECT: Plain language mandates, concrete metrics, burden reduction, pilot authority, outcome focus, regular cleanup

---

For each issue found, provide:
- category: [one of the 12 categories above]
- complexity: HIGH | MEDIUM | LOW
  * HIGH = Major implementation barrier or serious burden on public
  * MEDIUM = Moderate complexity or friction
  * LOW = Minor issue or opportunity for improvement
- matched_phrases: [1-20 exact quotes from section text that demonstrate the issue]
- implementation_approach: [how to implement this better, or what approach is needed]
- effort_estimate: [rough estimate of implementation difficulty/timeline, optional]
- explanation: [why this creates implementation burden or opportunity, 20-1000 chars]

Overall assessment:
- has_implementation_issues: true if section has ANY category 1-11 issues (false if only category 12 or no issues)
- overall_complexity: HIGH | MEDIUM | LOW (based on highest individual complexity, null if no issues)
- summary: [2-3 sentences about main implementation concerns or opportunities]
- requires_technical_review: true if section needs architects/engineers to design implementation approach

Return VALID JSON matching the PahlkaImplementationAnalysis schema.
"""


def analyze_section_implementation(
    llm_client,
    section: dict,
    stats: dict,
    stats_lock: Lock
) -> dict:
    """
    Analyze a single section for implementation complexity.

    Args:
        llm_client: LLM client for analysis
        section: Section record with id, text_plain, citation, heading
        stats: Shared statistics dict
        stats_lock: Thread lock for stats updates

    Returns:
        Analysis record dict
    """
    section_id = section["id"]
    section_text = section.get("text_plain", "")[:MAX_TEXT_LENGTH]
    citation = section.get("citation", "Unknown")
    heading = section.get("heading", "")

    try:
        # Build prompt
        prompt = build_analysis_prompt(section_text, citation, heading)

        # Call LLM
        response = llm_client.generate(
            prompt=prompt,
            response_model=PahlkaImplementationAnalysis,
            section_id=section_id
        )

        if response and response.data:
            analysis = response.data

            # Set section_id, model_used, and timestamp
            analysis.section_id = section_id
            analysis.model_used = response.model_used
            analysis.analyzed_at = datetime.utcnow().isoformat() + "Z"

            # Convert to dict for NDJSON
            record = analysis.model_dump()

            # Update stats
            with stats_lock:
                stats['analyzed_count'] += 1
                if record['has_implementation_issues']:
                    stats['issues_found'] += 1
                if record['overall_complexity']:
                    stats['complexity_levels'][record['overall_complexity']] += 1
                if record['requires_technical_review']:
                    stats['technical_review_needed'] += 1
                for indicator in record.get('indicators', []):
                    stats['categories'][indicator['category']] += 1

            return record

        else:
            logger.warning(f"No response from LLM for section {section_id}")
            with stats_lock:
                stats['failed_count'] += 1
            return None

    except Exception as e:
        logger.error(f"Error analyzing section {section_id}: {e}")
        with stats_lock:
            stats['failed_count'] += 1
        return None


def main():
    # Register signal handlers for graceful shutdown
    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)

    parser = argparse.ArgumentParser(
        description="Analyze DC Code sections for implementation complexity (Pahlka framework)"
    )
    parser.add_argument(
        "--sections",
        required=True,
        help="Path to sections NDJSON file"
    )
    parser.add_argument(
        "--obligations",
        required=True,
        help="Path to obligations NDJSON file"
    )
    parser.add_argument(
        "--reporting",
        required=True,
        help="Path to reporting NDJSON file"
    )
    parser.add_argument(
        "--out",
        required=True,
        help="Output path for Pahlka implementation analysis NDJSON"
    )
    parser.add_argument(
        "--limit",
        type=int,
        help="Limit number of sections to analyze (for testing)"
    )
    add_cascade_argument(parser)

    args = parser.parse_args()

    sections_file = Path(args.sections)
    obligations_file = Path(args.obligations)
    reporting_file = Path(args.reporting)
    output_file = Path(args.out)

    logger.info("=" * 70)
    logger.info("PAHLKA IMPLEMENTATION ANALYSIS")
    logger.info("=" * 70)
    logger.info(f"Sections file: {sections_file}")
    logger.info(f"Obligations file: {obligations_file}")
    logger.info(f"Reporting file: {reporting_file}")
    logger.info(f"Output file: {output_file}")
    logger.info(f"Workers: {WORKERS}")
    if args.limit:
        logger.info(f"Limit: {args.limit} sections")
    logger.info("")

    # Validate input files
    if not sections_file.exists():
        logger.error(f"Sections file not found: {sections_file}")
        return 1

    # Collect flagged sections
    flagged_sections = collect_flagged_sections(obligations_file, reporting_file)

    # Load sections
    logger.info("Loading sections...")
    reader = NDJSONReader(str(sections_file))
    sections_to_analyze = []

    for section in reader:
        section_id = section.get("id")
        if not section_id:
            continue

        # Filter: flagged sections OR keyword matches
        if section_id in flagged_sections or has_implementation_keywords(section.get("text_plain", "")):
            sections_to_analyze.append(section)

        if args.limit and len(sections_to_analyze) >= args.limit:
            break

    total_sections = len(sections_to_analyze)
    logger.info(f"Sections to analyze: {total_sections}")

    if total_sections == 0:
        logger.warning("No sections to analyze!")
        return 1

    # Load checkpoint
    checkpoint = load_checkpoint()

    # Filter out already processed
    sections_to_process = [
        s for s in sections_to_analyze
        if s["id"] not in checkpoint['processed_ids']
    ]

    logger.info(f"Already processed: {total_sections - len(sections_to_process)}")
    logger.info(f"Remaining to process: {len(sections_to_process)}")

    if len(sections_to_process) == 0:
        logger.info("All sections already processed!")
        return 0

    # Initialize LLM client
    llm_client = create_llm_client(strategy=args.cascade_strategy)

    # Initialize writer
    output_file.parent.mkdir(parents=True, exist_ok=True)

    # Statistics
    stats = {
        'analyzed_count': 0,
        'failed_count': 0,
        'issues_found': 0,
        'technical_review_needed': 0,
        'complexity_levels': Counter(),
        'categories': Counter()
    }
    stats_lock = Lock()

    # Process sections
    logger.info("")
    logger.info("Analyzing sections...")

    with NDJSONWriter(str(output_file)) as writer:
        if WORKERS > 1:
            # Parallel processing
            logger.info(f"Using {WORKERS} workers (parallel)")
            executor = None
            try:
                executor = ThreadPoolExecutor(max_workers=WORKERS)
                futures = {
                    executor.submit(analyze_section_implementation, llm_client, section, stats, stats_lock): section
                    for section in sections_to_process
                }

                with tqdm(total=len(sections_to_process), desc="Analyzing", unit="section") as pbar:
                    for future in as_completed(futures):
                        # Check for shutdown signal - exit immediately
                        if _shutdown_requested:
                            # Cancel remaining futures
                            for f in futures:
                                f.cancel()
                            # Save checkpoint before exiting
                            save_checkpoint(checkpoint)
                            logger.info("Checkpoint saved. Exiting now.")
                            # Properly shutdown executor
                            if executor:
                                executor.shutdown(wait=False, cancel_futures=True)
                            sys.exit(130)  # Exit immediately

                        section = futures[future]
                        try:
                            record = future.result()
                            if record:
                                writer.write(record)
                                checkpoint['processed_ids'].add(section["id"])

                                # Save checkpoint every 10 sections
                                if len(checkpoint['processed_ids']) % 10 == 0:
                                    save_checkpoint(checkpoint)

                        except Exception as e:
                            logger.error(f"Error processing section {section['id']}: {e}")
                            stats['failed_count'] += 1

                        pbar.update(1)
                        pbar.set_postfix({
                            'analyzed': stats['analyzed_count'],
                            'issues': stats['issues_found'],
                            'failed': stats['failed_count']
                        })
            finally:
                # Ensure proper cleanup of thread pool
                if executor:
                    executor.shutdown(wait=True, cancel_futures=True)

        else:
            # Serial processing
            logger.info("Using 1 worker (serial)")
            with tqdm(total=len(sections_to_process), desc="Analyzing", unit="section") as pbar:
                for section in sections_to_process:
                    # Check for shutdown signal - exit immediately
                    if _shutdown_requested:
                        save_checkpoint(checkpoint)
                        logger.info("Checkpoint saved. Exiting now.")
                        sys.exit(130)  # Exit immediately

                    record = analyze_section_implementation(llm_client, section, stats, stats_lock)
                    if record:
                        writer.write(record)
                        checkpoint['processed_ids'].add(section["id"])

                        # Save checkpoint every 10 sections
                        if len(checkpoint['processed_ids']) % 10 == 0:
                            save_checkpoint(checkpoint)

                    pbar.update(1)
                    pbar.set_postfix({
                        'analyzed': stats['analyzed_count'],
                        'issues': stats['issues_found'],
                        'failed': stats['failed_count']
                    })

        # Final checkpoint save
        save_checkpoint(checkpoint)

        # Print statistics
        logger.info("")
        logger.info("=" * 70)
        logger.info("PAHLKA IMPLEMENTATION ANALYSIS - COMPLETE")
        logger.info("=" * 70)
        logger.info(f"Sections analyzed: {stats['analyzed_count']}")
        logger.info(f"Sections with issues: {stats['issues_found']}")
        logger.info(f"Failed analyses: {stats['failed_count']}")
        logger.info(f"Require technical review: {stats['technical_review_needed']}")
        logger.info("")

        if stats['complexity_levels']:
            logger.info("Complexity Distribution:")
            for level, count in stats['complexity_levels'].most_common():
                percentage = (count / stats['analyzed_count'] * 100) if stats['analyzed_count'] > 0 else 0
                logger.info(f"  {level}: {count} ({percentage:.1f}%)")
            logger.info("")

        if stats['categories']:
            logger.info("Top Categories Found:")
            for category, count in stats['categories'].most_common(10):
                logger.info(f"  {category}: {count}")
            logger.info("")

        # Print LLM stats
        logger.info(llm_client.get_stats_summary())

        logger.info("")
        logger.info(f"Output written to: {output_file}")
        logger.info("=" * 70)

    return 0


if __name__ == "__main__":
    exit(main())
