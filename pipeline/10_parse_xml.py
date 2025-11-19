#!/usr/bin/env python3
"""
Parse legal code XML files into sections NDJSON.

Supports multiple jurisdictions via --jurisdiction flag.

Usage:
  python pipeline/10_parse_xml.py --jurisdiction dc --src data/subsets --out data/outputs/sections_subset.ndjson
  python pipeline/10_parse_xml.py --jurisdiction dc --src data/raw/dc-law-xml/us/dc/council/code/titles --out data/outputs/sections.ndjson
"""

import argparse
from pathlib import Path

from common import setup_logging
from corpus_parser import CorpusParser

logger = setup_logging(__name__)


def main():
    arg_parser = argparse.ArgumentParser(
        description="Parse legal code XML files into sections NDJSON"
    )
    arg_parser.add_argument(
        "--jurisdiction",
        default="dc",
        help="Jurisdiction code (dc, ca, ny, etc.). Default: dc"
    )
    arg_parser.add_argument(
        "--src",
        required=True,
        help="Source directory containing XML files"
    )
    arg_parser.add_argument(
        "--out",
        required=True,
        help="Output NDJSON file path"
    )
    arg_parser.add_argument(
        "--limit",
        type=int,
        help="Limit number of files to process (for testing)"
    )

    args = arg_parser.parse_args()

    try:
        parser = CorpusParser(
            jurisdiction=args.jurisdiction,
            src_dir=Path(args.src),
            out_file=Path(args.out),
            limit=args.limit
        )
        parser.run()
        return 0
    except Exception as e:
        logger.error(f"Pipeline failed: {e}")
        return 1


if __name__ == "__main__":
    exit(main())
