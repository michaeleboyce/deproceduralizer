#!/usr/bin/env python3
"""
Test script for LLMClient to verify it works with structured outputs.
"""

import sys
from pathlib import Path

# Add pipeline to path
sys.path.insert(0, str(Path(__file__).parent / "pipeline"))

from llm_client import LLMClient
from models import ReportingRequirement
from common import setup_logging

logger = setup_logging(__name__)

def test_reporting_requirement():
    """Test LLM client with ReportingRequirement model."""

    # Sample legal text
    test_text = """
    § 1-204.51. Annual reports by Mayor.

    The Mayor shall submit to the Council, no later than March 15 of each year,
    an annual report describing the activities and accomplishments of the
    Department of Housing and Community Development during the preceding fiscal year.

    The report shall include:
    (1) Statistical data on housing units assisted;
    (2) Financial information on program expenditures;
    (3) Performance metrics for affordable housing initiatives.
    """

    prompt = f"""You are analyzing a legal code section for SUBSTANTIVE reporting requirements.

TASK: Determine if this section requires an entity to compile and submit regular reports, data, statistics, or documentation to an oversight body.

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

SECTION TEXT:
{test_text}

Analyze this section and return the results.
"""

    logger.info("Testing LLM client with ReportingRequirement model...")

    client = LLMClient()
    response = client.generate(
        prompt=prompt,
        response_model=ReportingRequirement,
        section_id="test-1-204-51"
    )

    if response:
        logger.info(f"✓ Success! Used model: {response.model_used}")
        logger.info(f"  Has reporting: {response.data.has_reporting}")
        logger.info(f"  Summary: {response.data.reporting_summary}")
        logger.info(f"  Tags: {response.data.tags}")
        logger.info(f"  Highlights: {response.data.highlight_phrases}")
        return True
    else:
        logger.error("✗ Failed to get response from LLM")
        return False

if __name__ == "__main__":
    success = test_reporting_requirement()
    sys.exit(0 if success else 1)
