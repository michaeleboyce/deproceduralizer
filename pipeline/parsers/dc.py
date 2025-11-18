"""
DC Code XML parser implementation.

Parses DC Council legal code XML files using the DC-specific schema.
"""

import logging
import re
from pathlib import Path
from typing import Dict, List, Optional

from lxml import etree

from models import Ancestor, Section
from parsers.base import BaseParser

logger = logging.getLogger(__name__)

# Namespace for DC Code XML
NS = {"dc": "https://code.dccouncil.us/schemas/dc-library"}


class DCParser(BaseParser):
    """
    Parser for District of Columbia Code XML files.

    The DC Code uses a specific XML schema from the DC Council.
    XML files contain <num>, <heading>, <text>, <para>, and <history> elements.
    """

    def __init__(self):
        """Initialize DC Code parser."""
        super().__init__(jurisdiction="dc")

    def parse_section(
        self, xml_path: Path, ancestors: Optional[List[Ancestor]] = None
    ) -> Optional[Section]:
        """
        Parse a single DC Code section XML file.

        Args:
            xml_path: Path to the section XML file
            ancestors: Optional pre-computed ancestor chain from index.xml.
                      If provided, these will be used instead of heuristic extraction.

        Returns:
            Section model instance, or None if parsing fails
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
            heading = (
                heading_elem.text.strip()
                if heading_elem is not None and heading_elem.text
                else ""
            )

            # Extract text content
            text_elem = root.find("dc:text", NS)
            if text_elem is not None:
                text_plain = self.extract_text_plain(text_elem)
                text_html = self.extract_text_html(text_elem, NS)

                # Also include paragraphs that are siblings of text
                for para in root.findall("dc:para", NS):
                    para_plain = self.extract_text_plain(para)
                    para_html = f"<p>{para_plain}</p>"
                    text_plain += " " + para_plain
                    text_html += "\n" + para_html
            else:
                # No explicit text element, extract from all non-annotation children
                text_plain = ""
                text_html = ""
                for child in root:
                    if child.tag.endswith("para"):
                        para_plain = self.extract_text_plain(child)
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
                # First digit of second part
                chapter_num = parts[1][:1] if parts[1] else parts[0]
            else:
                title_num = parts[0] if parts else "Unknown"
                chapter_num = "Unknown"

            title_label = f"Title {title_num}"
            chapter_label = f"Chapter {chapter_num}"

            # Build ancestors array
            if ancestors is not None:
                # Use pre-computed ancestors from Pass 1 (index.xml parsing)
                section_ancestors = ancestors
            else:
                # Fall back to heuristic method (for backwards compatibility)
                section_ancestors = [
                    Ancestor(
                        type="title",
                        label=title_label,
                        id=f"dc-title-{title_num}",
                    ),
                    Ancestor(
                        type="chapter",
                        label=chapter_label,
                        id=f"dc-{title_num}-chapter-{chapter_num}",
                    ),
                ]

            # Extract effective date (if available)
            effective_date = self.extract_effective_date(xml_path)

            # Build the Section model
            section = Section(
                jurisdiction=self.jurisdiction,
                id=section_id,
                citation=citation,
                heading=heading,
                text_plain=text_plain,
                text_html=text_html,
                ancestors=section_ancestors,
                title_label=title_label,
                chapter_label=chapter_label,
                effective_date=effective_date,
            )

            return section

        except etree.XMLSyntaxError as e:
            logger.error(f"XML syntax error in {xml_path}: {e}")
            return None
        except Exception as e:
            logger.error(f"Error parsing {xml_path}: {e}")
            return None

    def parse_hierarchy(self, index_path: Path) -> Dict[str, any]:
        """
        Parse a DC Code index.xml file to extract hierarchical structure.

        Recursively walks <container> elements in index.xml to build:
        1. StructureNode records for each hierarchical level
        2. Section ID to ancestors mapping

        Args:
            index_path: Path to the index.xml file

        Returns:
            Dictionary with:
            {
                "structures": [StructureNode, ...],  # All nodes in hierarchy
                "section_ancestors": {  # section_id -> List[Ancestor]
                    "dc-1-101": [Ancestor(...), ...],
                    ...
                }
            }
        """
        from models import StructureNode, Ancestor

        try:
            tree = etree.parse(str(index_path))
            root = tree.getroot()

            structures = []
            section_ancestors = {}

            def walk_container(
                container_elem,
                parent_id: Optional[str] = None,
                parent_path: str = "",
                ancestor_stack: List[Ancestor] = None,
                ordinal: int = 1,
            ):
                """Recursively walk container elements building hierarchy."""
                if ancestor_stack is None:
                    ancestor_stack = []

                # Extract container metadata
                prefix_elem = container_elem.find("dc:prefix", NS)
                num_elem = container_elem.find("dc:num", NS)
                heading_elem = container_elem.find("dc:heading", NS)

                if prefix_elem is None or num_elem is None:
                    # Not a proper container, skip
                    return

                level = prefix_elem.text.strip().lower()
                num = num_elem.text.strip()
                heading = (
                    heading_elem.text.strip() if heading_elem is not None else ""
                )

                # Generate hierarchical ID
                # Normalize Roman numerals and special characters for IDs
                num_normalized = num.lower().replace(" ", "-")

                if parent_path:
                    node_id = f"{parent_path}-{level}-{num_normalized}"
                else:
                    # Top level (title)
                    node_id = f"{self.jurisdiction}-{level}-{num_normalized}"

                # Create label
                label = f"{prefix_elem.text.strip()} {num}"

                # Create StructureNode
                structure_node = StructureNode(
                    jurisdiction=self.jurisdiction,
                    id=node_id,
                    parent_id=parent_id,
                    level=level,
                    label=label,
                    heading=heading,
                    ordinal=ordinal,
                )
                structures.append(structure_node)

                # Create Ancestor for this node
                current_ancestor = Ancestor(
                    type=level,
                    label=label,
                    id=node_id,
                )

                # Build new ancestor stack
                new_ancestor_stack = ancestor_stack + [current_ancestor]

                # Find child containers and sections
                child_ordinal = 1
                for child in container_elem:
                    if child.tag == f"{{{NS['dc']}}}container":
                        # Recursive call for nested container
                        walk_container(
                            child,
                            parent_id=node_id,
                            parent_path=node_id,
                            ancestor_stack=new_ancestor_stack,
                            ordinal=child_ordinal,
                        )
                        child_ordinal += 1
                    elif child.tag == "{http://www.w3.org/2001/XInclude}include":
                        # Section reference - extract section ID from href
                        href = child.get("href")
                        if href:
                            # href format: "./sections/1-101.xml"
                            section_filename = Path(href).stem  # "1-101"
                            section_id = f"{self.jurisdiction}-{section_filename.replace('.', '-')}"

                            # Map this section to its ancestor chain
                            section_ancestors[section_id] = new_ancestor_stack.copy()

            # Start walking from root container
            if root.tag == f"{{{NS['dc']}}}container":
                walk_container(root)
            else:
                # Root might contain container as child
                for container in root.findall("dc:container", NS):
                    walk_container(container)

            return {
                "structures": structures,
                "section_ancestors": section_ancestors,
            }

        except etree.XMLSyntaxError as e:
            logger.error(f"XML syntax error in {index_path}: {e}")
            return {"structures": [], "section_ancestors": {}}
        except Exception as e:
            logger.error(f"Error parsing hierarchy from {index_path}: {e}")
            return {"structures": [], "section_ancestors": {}}

    def extract_effective_date(self, xml_path: Path) -> Optional[str]:
        """
        Extract effective date from DC Code section XML <history> tags.

        The DC Code includes <history> tags with <effective> elements.

        Args:
            xml_path: Path to the section XML file

        Returns:
            Effective date string in YYYY-MM-DD format, or None if not found
        """
        try:
            tree = etree.parse(str(xml_path))
            root = tree.getroot()

            # Look for <history> -> <effective> element
            history_elem = root.find("dc:meta/dc:history", NS)
            if history_elem is not None:
                effective_elem = history_elem.find("dc:effective", NS)
                if effective_elem is not None and effective_elem.text:
                    # DC Code format: "YYYY-MM-DD" or "MM/DD/YYYY"
                    date_text = effective_elem.text.strip()

                    # Try YYYY-MM-DD format first
                    if re.match(r"^\d{4}-\d{2}-\d{2}$", date_text):
                        return date_text

                    # Try MM/DD/YYYY format
                    match = re.match(r"^(\d{1,2})/(\d{1,2})/(\d{4})$", date_text)
                    if match:
                        month, day, year = match.groups()
                        return f"{year}-{month.zfill(2)}-{day.zfill(2)}"

            # Alternative: Look for <history> attribute
            history_elem = root.find("dc:annotations/dc:annotation[@type='History']", NS)
            if history_elem is not None and history_elem.text:
                # Extract date from text like "Apr. 9, 1997, D.C. Law 11-255"
                # This is complex and may require more sophisticated parsing
                pass

            return None

        except Exception as e:
            logger.debug(f"Could not extract effective date from {xml_path}: {e}")
            return None
