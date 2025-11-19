"""
CorpusParser class for orchestrating the parsing of legal code XML.

This class encapsulates the logic for the two-pass parsing process:
1. Parsing index.xml files to build the hierarchy.
2. Parsing section XML files to extract content and metadata.
"""

import logging
from pathlib import Path
from typing import List, Optional

import logging
import sys
from pathlib import Path
from typing import List, Optional

from tqdm import tqdm

# Handle imports whether run as script or module
try:
    from common import NDJSONWriter, StateManager
    from parsers import get_parser
except ImportError:
    from pipeline.common import NDJSONWriter, StateManager
    from pipeline.parsers import get_parser

logger = logging.getLogger(__name__)


class CorpusParser:
    """
    Orchestrates the parsing of legal code XML files.
    """

    def __init__(
        self,
        jurisdiction: str,
        src_dir: Path,
        out_file: Path,
        limit: Optional[int] = None,
        state_file: Optional[Path] = None,
    ):
        """
        Initialize the CorpusParser.

        Args:
            jurisdiction: Jurisdiction code (e.g., 'dc').
            src_dir: Source directory containing XML files.
            out_file: Output NDJSON file path.
            limit: Optional limit on number of files to process.
            state_file: Optional path to state file for resume capability.
        """
        self.jurisdiction = jurisdiction
        self.src_dir = src_dir
        self.out_file = out_file
        self.limit = limit
        
        # Set up state management
        if state_file:
            self.state_file = state_file
        else:
            # Default to data/interim/parse_xml.state if not provided
            self.state_file = Path("data/interim/parse_xml.state")
            
        self.state = StateManager(str(self.state_file))

        # Get jurisdiction-specific parser
        try:
            self.parser = get_parser(self.jurisdiction)
            logger.info(f"Using parser for jurisdiction: {self.jurisdiction}")
        except (ValueError, NotImplementedError) as e:
            raise ValueError(f"Failed to initialize parser: {e}")

        # Internal state
        self.hierarchy_map = {}
        self.all_structures = []

    def validate_source(self) -> List[Path]:
        """
        Validate source directory and find XML files.
        
        Returns:
            List of XML files to process.
        """
        if not self.src_dir.exists():
            raise FileNotFoundError(f"Source directory not found: {self.src_dir}")

        if not self.src_dir.is_dir():
            raise NotADirectoryError(f"Source must be a directory: {self.src_dir}")

        # Look for section XML files (not index files)
        xml_files = sorted([
            f for f in self.src_dir.rglob("*.xml")
            if f.name != "index.xml" and "index" not in f.name.lower()
        ])

        if not xml_files:
            raise FileNotFoundError(f"No XML files found in {self.src_dir}")

        if self.limit:
            xml_files = xml_files[:self.limit]
            logger.info(f"Limiting processing to {self.limit} files")

        return xml_files

    def parse_hierarchy(self):
        """
        Pass 1: Parse index.xml files to build hierarchical structure.
        """
        logger.info("Pass 1: Parsing index.xml files for hierarchical structure")

        index_files = sorted(list(self.src_dir.rglob("index.xml")))
        logger.info(f"Found {len(index_files)} index.xml files")

        self.hierarchy_map = {}
        self.all_structures = []

        for index_file in tqdm(index_files, desc="Parsing index files", unit="file"):
            hierarchy_data = self.parser.parse_hierarchy(index_file)

            # Collect structure nodes
            structures = hierarchy_data.get("structures", [])
            self.all_structures.extend(structures)

            # Merge section-to-ancestors mappings
            section_ancestors = hierarchy_data.get("section_ancestors", {})
            self.hierarchy_map.update(section_ancestors)

        logger.info(
            f"Pass 1 complete: {len(self.all_structures)} structure nodes, "
            f"{len(self.hierarchy_map)} sections mapped to ancestors"
        )

        # Write structure.ndjson output
        structure_out_file = self.out_file.parent / self.out_file.name.replace(
            "sections", "structure"
        )
        with NDJSONWriter(str(structure_out_file)) as structure_writer:
            for structure in self.all_structures:
                record = structure.model_dump(exclude_none=True)
                structure_writer.write(record)

        logger.info(f"Structure output written to: {structure_out_file}")

    def parse_sections(self, xml_files: List[Path]):
        """
        Pass 2: Parse section XML files with full ancestor information.
        """
        logger.info("Pass 2: Parsing section XML files")

        # Track statistics
        processed_count = self.state.get("processed_count", 0)
        success_count = self.state.get("success_count", 0)
        error_count = self.state.get("error_count", 0)

        # Reset state if output file doesn't exist or is empty
        # (indicates a fresh run, not a resume)
        if not self.out_file.exists() or self.out_file.stat().st_size == 0:
            logger.info("Output file missing or empty - resetting state for fresh run")
            processed_count = 0
            success_count = 0
            error_count = 0
            self.state.set("processed_count", 0)
            self.state.set("success_count", 0)
            self.state.set("error_count", 0)
            self.state.save()

        # Open output file for writing
        with NDJSONWriter(str(self.out_file)) as writer:
            # Process each XML file with progress bar
            for xml_file in tqdm(xml_files, desc="Parsing XML files", unit="file"):
                # Skip if already processed (for resume)
                if processed_count > 0 and xml_files.index(xml_file) < processed_count:
                    continue

                # Extract section ID from filename to lookup ancestors
                # Filename format: "1-101.xml" -> section_id: "dc-1-101"
                section_filename = xml_file.stem
                section_id = f"{self.jurisdiction}-{section_filename.replace('.', '-')}"

                # Lookup pre-computed ancestors from Pass 1
                ancestors = self.hierarchy_map.get(section_id)

                # Parse the section using jurisdiction-specific parser
                section = self.parser.parse_section(xml_file, ancestors=ancestors)

                if section:
                    # Convert Pydantic model to dict for NDJSON output
                    record = section.model_dump(exclude_none=True)
                    writer.write(record)
                    success_count += 1
                else:
                    error_count += 1

                processed_count += 1

                # Save state periodically
                if processed_count % 10 == 0:
                    self.state.set("processed_count", processed_count)
                    self.state.set("success_count", success_count)
                    self.state.set("error_count", error_count)
                    self.state.save()

        # Final state save
        self.state.set("processed_count", processed_count)
        self.state.set("success_count", success_count)
        self.state.set("error_count", error_count)
        self.state.save()

        logger.info(f"Processing complete!")
        logger.info(f"  Total processed: {processed_count}")
        logger.info(f"  Successful: {success_count}")
        logger.info(f"  Errors: {error_count}")
        logger.info(f"  Output: {self.out_file}")

    def run(self):
        """
        Execute the full parsing pipeline.
        """
        xml_files = self.validate_source()
        self.parse_hierarchy()
        self.parse_sections(xml_files)
