#!/usr/bin/env python3
"""
Test script to validate pipeline models against existing NDJSON data.

This script loads existing NDJSON output files and validates them
against the new Pydantic models to ensure backward compatibility.
"""

import json
import sys
from pathlib import Path
from typing import List

from pipeline.models import (
    Section,
    CrossReference,
    Deadline,
    Amount,
    SimilarityPair,
    ReportingRequirement,
    SimilarityClassification,
)


def test_sections(filepath: Path) -> bool:
    """Test Section model against sections.ndjson."""
    print(f"\n{'='*60}")
    print(f"Testing Section model with {filepath}")
    print('='*60)

    errors = []
    success_count = 0

    with open(filepath) as f:
        for i, line in enumerate(f, 1):
            try:
                data = json.loads(line)
                section = Section(**data)
                success_count += 1
            except Exception as e:
                errors.append(f"Line {i}: {e}")
                if len(errors) <= 5:  # Show first 5 errors
                    print(f"❌ Error on line {i}: {e}")

    print(f"\n✅ Successfully validated {success_count} sections")
    if errors:
        print(f"❌ Found {len(errors)} errors")
        if len(errors) > 5:
            print(f"   (showing first 5, {len(errors) - 5} more suppressed)")
        return False
    return True


def test_refs(filepath: Path) -> bool:
    """Test CrossReference model against refs.ndjson."""
    print(f"\n{'='*60}")
    print(f"Testing CrossReference model with {filepath}")
    print('='*60)

    errors = []
    success_count = 0

    with open(filepath) as f:
        for i, line in enumerate(f, 1):
            try:
                data = json.loads(line)
                ref = CrossReference(**data)
                success_count += 1
            except Exception as e:
                errors.append(f"Line {i}: {e}")
                if len(errors) <= 5:
                    print(f"❌ Error on line {i}: {e}")

    print(f"\n✅ Successfully validated {success_count} cross-references")
    if errors:
        print(f"❌ Found {len(errors)} errors")
        return False
    return True


def test_deadlines(filepath: Path) -> bool:
    """Test Deadline model against deadlines.ndjson."""
    print(f"\n{'='*60}")
    print(f"Testing Deadline model with {filepath}")
    print('='*60)

    errors = []
    success_count = 0

    with open(filepath) as f:
        for i, line in enumerate(f, 1):
            try:
                data = json.loads(line)
                deadline = Deadline(**data)
                success_count += 1
            except Exception as e:
                errors.append(f"Line {i}: {e}")
                if len(errors) <= 5:
                    print(f"❌ Error on line {i}: {e}")

    print(f"\n✅ Successfully validated {success_count} deadlines")
    if errors:
        print(f"❌ Found {len(errors)} errors")
        return False
    return True


def test_amounts(filepath: Path) -> bool:
    """Test Amount model against amounts.ndjson."""
    print(f"\n{'='*60}")
    print(f"Testing Amount model with {filepath}")
    print('='*60)

    errors = []
    success_count = 0

    with open(filepath) as f:
        for i, line in enumerate(f, 1):
            try:
                data = json.loads(line)
                amount = Amount(**data)
                success_count += 1
            except Exception as e:
                errors.append(f"Line {i}: {e}")
                if len(errors) <= 5:
                    print(f"❌ Error on line {i}: {e}")

    print(f"\n✅ Successfully validated {success_count} amounts")
    if errors:
        print(f"❌ Found {len(errors)} errors")
        return False
    return True


def test_similarities(filepath: Path) -> bool:
    """Test SimilarityPair model against similarities.ndjson."""
    print(f"\n{'='*60}")
    print(f"Testing SimilarityPair model with {filepath}")
    print('='*60)

    errors = []
    success_count = 0

    with open(filepath) as f:
        for i, line in enumerate(f, 1):
            try:
                data = json.loads(line)
                similarity = SimilarityPair(**data)
                success_count += 1
            except Exception as e:
                errors.append(f"Line {i}: {e}")
                if len(errors) <= 5:
                    print(f"❌ Error on line {i}: {e}")

    print(f"\n✅ Successfully validated {success_count} similarity pairs")
    if errors:
        print(f"❌ Found {len(errors)} errors")
        return False
    return True


def test_reporting(filepath: Path) -> bool:
    """Test ReportingRequirement model against reporting.ndjson."""
    print(f"\n{'='*60}")
    print(f"Testing ReportingRequirement model with {filepath}")
    print('='*60)

    errors = []
    success_count = 0

    with open(filepath) as f:
        for i, line in enumerate(f, 1):
            try:
                data = json.loads(line)
                reporting = ReportingRequirement(**data)
                success_count += 1
            except Exception as e:
                errors.append(f"Line {i}: {e}")
                if len(errors) <= 5:
                    print(f"❌ Error on line {i}: {e}")

    print(f"\n✅ Successfully validated {success_count} reporting requirements")
    if errors:
        print(f"❌ Found {len(errors)} errors")
        return False
    return True


def test_similarity_classifications(filepath: Path) -> bool:
    """Test SimilarityClassification model against similarity_classifications.ndjson."""
    print(f"\n{'='*60}")
    print(f"Testing SimilarityClassification model with {filepath}")
    print('='*60)

    errors = []
    success_count = 0

    with open(filepath) as f:
        for i, line in enumerate(f, 1):
            try:
                data = json.loads(line)
                classification = SimilarityClassification(**data)
                success_count += 1
            except Exception as e:
                errors.append(f"Line {i}: {e}")
                if len(errors) <= 5:
                    print(f"❌ Error on line {i}: {e}")

    print(f"\n✅ Successfully validated {success_count} classifications")
    if errors:
        print(f"❌ Found {len(errors)} errors")
        return False
    return True


def main():
    """Run all model tests."""
    print("\n" + "="*60)
    print("TESTING PIPELINE MODELS")
    print("="*60)

    data_dir = Path("data/outputs")

    # Test files
    test_files = {
        "sections_subset.ndjson": test_sections,
        "refs_subset.ndjson": test_refs,
        "deadlines_subset.ndjson": test_deadlines,
        "amounts_subset.ndjson": test_amounts,
        "similarities_subset.ndjson": test_similarities,
        "reporting_subset.ndjson": test_reporting,
        "similarity_classifications_subset.ndjson": test_similarity_classifications,
    }

    results = {}

    for filename, test_func in test_files.items():
        filepath = data_dir / filename
        if filepath.exists():
            results[filename] = test_func(filepath)
        else:
            print(f"\n⚠️  Skipping {filename} (file not found)")
            results[filename] = None

    # Summary
    print("\n" + "="*60)
    print("SUMMARY")
    print("="*60)

    tested = sum(1 for v in results.values() if v is not None)
    passed = sum(1 for v in results.values() if v is True)
    failed = sum(1 for v in results.values() if v is False)
    skipped = sum(1 for v in results.values() if v is None)

    for filename, result in results.items():
        status = "✅ PASS" if result is True else "❌ FAIL" if result is False else "⚠️  SKIP"
        print(f"{status:12} {filename}")

    print(f"\nTested: {tested}, Passed: {passed}, Failed: {failed}, Skipped: {skipped}")

    if failed > 0:
        print("\n❌ Some tests failed!")
        sys.exit(1)
    elif passed == 0:
        print("\n⚠️  No tests run (all files skipped)")
        sys.exit(1)
    else:
        print("\n✅ All tests passed!")
        sys.exit(0)


if __name__ == "__main__":
    main()
