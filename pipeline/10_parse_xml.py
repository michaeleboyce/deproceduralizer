#!/usr/bin/env python3
"""
Parse DC Code XML files into sections NDJSON.

Usage:
  python pipeline/10_parse_xml.py --src data/subsets --out data/outputs/sections_subset.ndjson
  python pipeline/10_parse_xml.py --src data/raw/dc-law-xml/us/dc/council/code/titles --out data/outputs/sections.ndjson
"""

import argparse
import re
from pathlib import Path
from lxml import etree
from tqdm import tqdm

from common import (
    NDJSONWriter,
    StateManager,
    setup_logging,
    PIPELINE_VERSION,
    validate_record
)

logger = setup_logging(__name__)

# Namespace for DC Code XML
NS = {"dc": "https://code.dccouncil.us/schemas/dc-library"}


def extract_text_plain(element):
    """Extract plain text from an XML element, recursively."""
    # Get all text content, including nested elements
    text_parts = []

    # Get direct text
    if element.text:
        text_parts.append(element.text.strip())

    # Get text from all child elements
    for child in element:
        child_text = extract_text_plain(child)
        if child_text:
            text_parts.append(child_text)
        # Get tail text (text after the child element)
        if child.tail:
            text_parts.append(child.tail.strip())

    return " ".join(part for part in text_parts if part)


def extract_text_html(element):
    """Extract HTML-formatted text from an XML element."""
    # Convert XML structure to simple HTML
    html_parts = []

    # Get direct text
    if element.text:
        text = element.text.strip()
        if text:
            html_parts.append(f"<p>{text}</p>")

    # Process paragraphs
    for para in element.findall(".//dc:para", NS):
        para_text = extract_text_plain(para)
        if para_text:
            html_parts.append(f"<p>{para_text}</p>")

    # If no paragraphs, just return all text as a single paragraph
    if not html_parts:
        all_text = extract_text_plain(element)
        if all_text:
            html_parts.append(f"<p>{all_text}</p>")

    return "\n".join(html_parts)


def parse_section_xml(xml_path: Path) -> dict:
    """
    Parse a single DC Code section XML file.

    Returns:
        Dictionary with section data according to CONTRACTS.md schema
    """
    try:
        tree = etree.parse(str(xml_path))
        root = tree.getroot()

        # Extract section number (ID)
        num_elem = root.find("dc:num", NS)
        if num_elem is None or not num_elem.text:
            logger.warning(f"No <num> element in {xml_path}, skipping")
            return None

        section_num = num_elem.text.strip()

        # Build section ID (e.g., "dc-1-101" from "1-101")
        section_id = f"dc-{section_num.replace('.', '-')}"

        # Build citation (e.g., "§ 1-101")
        citation = f"§ {section_num}"

        # Extract heading
        heading_elem = root.find("dc:heading", NS)
        heading = heading_elem.text.strip() if heading_elem is not None and heading_elem.text else ""

        # Extract text content
        # Get all text elements (excluding annotations)
        text_elem = root.find("dc:text", NS)
        if text_elem is not None:
            text_plain = extract_text_plain(text_elem)
            text_html = extract_text_html(text_elem)

            # Also include paragraphs that are siblings of text
            for para in root.findall("dc:para", NS):
                para_plain = extract_text_plain(para)
                para_html = f"<p>{para_plain}</p>"
                text_plain += " " + para_plain
                text_html += "\n" + para_html
        else:
            # No explicit text element, extract from all non-annotation children
            text_plain = ""
            text_html = ""
            for child in root:
                if child.tag.endswith("para"):
                    para_plain = extract_text_plain(child)
                    text_plain += " " + para_plain
                    text_html += f"<p>{para_plain}</p>\n"

        text_plain = text_plain.strip()
        text_html = text_html.strip()

        # Determine title and chapter from section number
        # Section format is typically: TITLE-CHAPTER-SECTION
        # e.g., "1-101" = Title 1, Chapter 1, Section 101
        parts = section_num.split("-")
        if len(parts) >= 2:
            title_num = parts[0]
            chapter_num = parts[1][:1] if parts[1] else parts[0]  # First digit of second part
        else:
            title_num = parts[0] if parts else "Unknown"
            chapter_num = "Unknown"

        title_label = f"Title {title_num}"
        chapter_label = f"Chapter {chapter_num}"

        # Build ancestors array
        # For now, simplified version - in production, would parse index.xml files
        ancestors = [
            {"type": "title", "label": title_label, "id": f"dc-title-{title_num}"},
            {"type": "chapter", "label": chapter_label, "id": f"dc-{title_num}-chapter-{chapter_num}"}
        ]

        # Build the section record
        record = {
            "id": section_id,
            "citation": citation,
            "heading": heading,
            "text_plain": text_plain,
            "text_html": text_html,
            "ancestors": ancestors,
            "title_label": title_label,
            "chapter_label": chapter_label,
        }

        return record

    except etree.XMLSyntaxError as e:
        logger.error(f"XML syntax error in {xml_path}: {e}")
        return None
    except Exception as e:
        logger.error(f"Error parsing {xml_path}: {e}")
        return None


def main():
    parser = argparse.ArgumentParser(
        description="Parse DC Code XML files into sections NDJSON"
    )
    parser.add_argument(
        "--src",
        required=True,
        help="Source directory containing XML files"
    )
    parser.add_argument(
        "--out",
        required=True,
        help="Output NDJSON file path"
    )
    parser.add_argument(
        "--limit",
        type=int,
        help="Limit number of files to process (for testing)"
    )

    args = parser.parse_args()

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

    logger.info(f"Found {len(xml_files)} XML files to process")

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

            # Parse the section
            record = parse_section_xml(xml_file)

            if record:
                # Validate against schema
                required_fields = ["id", "citation", "heading", "text_plain",
                                 "text_html", "ancestors", "title_label", "chapter_label"]

                if validate_record(record, required_fields):
                    writer.write(record)
                    success_count += 1
                else:
                    logger.error(f"Invalid record from {xml_file}")
                    error_count += 1
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
