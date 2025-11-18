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
from tqdm import tqdm

from common import (
    NDJSONWriter,
    StateManager,
    setup_logging,
    PIPELINE_VERSION,
)
from parsers import get_parser

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

    # Get jurisdiction-specific parser
    try:
        parser = get_parser(args.jurisdiction)
        logger.info(f"Using parser for jurisdiction: {args.jurisdiction}")
    except (ValueError, NotImplementedError) as e:
        logger.error(str(e))
        return 1

    src_dir = Path(args.src)
    out_file = Path(args.out)

    if not src_dir.exists():
        logger.error(f"Source directory not found: {src_dir}")
        return 1

    # Set up state management for resume capability
    state_file = Path("data/interim/parse_xml.state")
    state = StateManager(str(state_file))

    # Find all XML files
    if src_dir.is_dir():
        # Look for section XML files (not index files)
        xml_files = sorted([
            f for f in src_dir.rglob("*.xml")
            if f.name != "index.xml" and "index" not in f.name.lower()
        ])
    else:
        logger.error(f"Source must be a directory: {src_dir}")
        return 1

    if not xml_files:
        logger.error(f"No XML files found in {src_dir}")
        return 1

    # Apply limit if specified
    if args.limit:
        xml_files = xml_files[:args.limit]

    logger.info(f"Found {len(xml_files)} section XML files to process")

    # =============================================================================
    # PASS 1: Parse index.xml files to build hierarchical structure
    # =============================================================================
    logger.info("Pass 1: Parsing index.xml files for hierarchical structure")

    # Find all index.xml files (including in root and subdirectories)
    index_files = sorted(list(src_dir.rglob("index.xml")))
    logger.info(f"Found {len(index_files)} index.xml files")

    # Build hierarchy map: section_id -> List[Ancestor]
    hierarchy_map = {}
    all_structures = []

    for index_file in tqdm(index_files, desc="Parsing index files", unit="file"):
        hierarchy_data = parser.parse_hierarchy(index_file)

        # Collect structure nodes
        structures = hierarchy_data.get("structures", [])
        all_structures.extend(structures)

        # Merge section-to-ancestors mappings
        section_ancestors = hierarchy_data.get("section_ancestors", {})
        hierarchy_map.update(section_ancestors)

    logger.info(
        f"Pass 1 complete: {len(all_structures)} structure nodes, "
        f"{len(hierarchy_map)} sections mapped to ancestors"
    )

    # Write structure.ndjson output
    structure_out_file = out_file.parent / out_file.name.replace(
        "sections", "structure"
    )
    with NDJSONWriter(str(structure_out_file)) as structure_writer:
        for structure in all_structures:
            record = structure.model_dump(exclude_none=True)
            structure_writer.write(record)

    logger.info(f"Structure output written to: {structure_out_file}")

    # =============================================================================
    # PASS 2: Parse section XML files with full ancestor information
    # =============================================================================
    logger.info("Pass 2: Parsing section XML files")

    # Track statistics
    processed_count = state.get("processed_count", 0)
    success_count = state.get("success_count", 0)
    error_count = state.get("error_count", 0)

    # Open output file for writing
    with NDJSONWriter(str(out_file)) as writer:
        # Process each XML file with progress bar
        for xml_file in tqdm(xml_files, desc="Parsing XML files", unit="file"):
            # Skip if already processed (for resume)
            if processed_count > 0 and xml_files.index(xml_file) < processed_count:
                continue

            # Extract section ID from filename to lookup ancestors
            # Filename format: "1-101.xml" -> section_id: "dc-1-101"
            section_filename = xml_file.stem
            section_id = f"{args.jurisdiction}-{section_filename.replace('.', '-')}"

            # Lookup pre-computed ancestors from Pass 1
            ancestors = hierarchy_map.get(section_id)

            # Parse the section using jurisdiction-specific parser
            # Pass ancestors if available, otherwise parser will use heuristic
            section = parser.parse_section(xml_file, ancestors=ancestors)

            if section:
                # Convert Pydantic model to dict for NDJSON output
                record = section.model_dump(exclude_none=True)
                writer.write(record)
                success_count += 1
            else:
                error_count += 1

            processed_count += 1

            # Save state periodically (every 10 files)
            if processed_count % 10 == 0:
                state.set("processed_count", processed_count)
                state.set("success_count", success_count)
                state.set("error_count", error_count)
                state.save()

    # Final state save
    state.set("processed_count", processed_count)
    state.set("success_count", success_count)
    state.set("error_count", error_count)
    state.save()

    logger.info(f"Processing complete!")
    logger.info(f"  Total processed: {processed_count}")
    logger.info(f"  Successful: {success_count}")
    logger.info(f"  Errors: {error_count}")
    logger.info(f"  Output: {out_file}")

    return 0


if __name__ == "__main__":
    exit(main())
