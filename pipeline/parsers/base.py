"""
Abstract base parser for legal code XML processing.

Defines the interface that all jurisdiction-specific parsers must implement.
"""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Dict, List, Optional

from models import Section


class BaseParser(ABC):
    """
    Abstract base class for jurisdiction-specific legal code parsers.

    Each jurisdiction (DC, California, New York, etc.) extends this class
    to implement its specific XML structure and parsing logic.

    Subclasses must implement:
    - parse_section(): Parse a single section XML file
    - parse_hierarchy(): Parse index.xml files for structure
    - extract_effective_date(): Extract effective date from history tags
    """

    def __init__(self, jurisdiction: str):
        """
        Initialize the parser.

        Args:
            jurisdiction: Jurisdiction code (e.g., "dc", "ca", "ny")
        """
        self.jurisdiction = jurisdiction.lower()

    @abstractmethod
    def parse_section(
        self, xml_path: Path, ancestors: Optional[List] = None
    ) -> Optional[Section]:
        """
        Parse a single section XML file into a Section model.

        Args:
            xml_path: Path to the section XML file
            ancestors: Optional pre-computed ancestor chain from index.xml parsing.
                      If provided, will be used instead of heuristic-based ancestor extraction.
                      If None, parser should fall back to heuristic method.

        Returns:
            Section model instance, or None if parsing fails

        Example:
            # Without pre-computed ancestors (heuristic fallback)
            section = parser.parse_section(Path("data/raw/dc-1-101.xml"))

            # With pre-computed ancestors (from Pass 1)
            section = parser.parse_section(
                Path("data/raw/dc-1-101.xml"),
                ancestors=[Ancestor(...), Ancestor(...)]
            )
        """
        pass

    @abstractmethod
    def parse_hierarchy(self, index_path: Path) -> Dict[str, any]:
        """
        Parse an index.xml file to extract hierarchical structure.

        Args:
            index_path: Path to the index.xml file

        Returns:
            Dictionary containing hierarchical structure:
            {
                "title": {"id": "...", "label": "...", "ordinal": 1},
                "chapters": [
                    {"id": "...", "label": "...", "ordinal": 1,
                     "sections": ["dc-1-101", "dc-1-102", ...]},
                    ...
                ]
            }

        Example:
            hierarchy = parser.parse_hierarchy(Path("data/raw/title-1/index.xml"))
        """
        pass

    @abstractmethod
    def extract_effective_date(self, xml_path: Path) -> Optional[str]:
        """
        Extract effective date from section XML <history> tags.

        Args:
            xml_path: Path to the section XML file

        Returns:
            Effective date string in YYYY-MM-DD format, or None if not found

        Example:
            date = parser.extract_effective_date(Path("data/raw/dc-1-101.xml"))
            # Returns: "2020-05-06" or None
        """
        pass

    def extract_text_plain(self, element) -> str:
        """
        Extract plain text from an XML element recursively.

        This is a common utility method that can be used by all parsers.
        Subclasses can override if they need jurisdiction-specific behavior.

        Args:
            element: lxml Element object

        Returns:
            Plain text string
        """
        text_parts = []

        # Get direct text
        if element.text:
            text_parts.append(element.text.strip())

        # Get text from all child elements
        for child in element:
            child_text = self.extract_text_plain(child)
            if child_text:
                text_parts.append(child_text)
            # Get tail text (text after the child element)
            if child.tail:
                text_parts.append(child.tail.strip())

        return " ".join(part for part in text_parts if part)

    def extract_text_html(self, element, namespace: Dict[str, str]) -> str:
        """
        Extract HTML-formatted text from an XML element.

        This is a common utility method that can be used by all parsers.
        Subclasses can override if they need jurisdiction-specific behavior.

        Args:
            element: lxml Element object
            namespace: XML namespace dict (e.g., {"dc": "https://..."})

        Returns:
            HTML string with <p> tags
        """
        html_parts = []

        # Get direct text
        if element.text:
            text = element.text.strip()
            if text:
                html_parts.append(f"<p>{text}</p>")

        # Process paragraphs (namespace-aware)
        # Get namespace prefix from namespace dict
        ns_prefix = list(namespace.keys())[0] if namespace else None
        if ns_prefix:
            para_xpath = f".//{ns_prefix}:para"
            for para in element.findall(para_xpath, namespace):
                para_text = self.extract_text_plain(para)
                if para_text:
                    html_parts.append(f"<p>{para_text}</p>")

        # If no paragraphs, just return all text as a single paragraph
        if not html_parts:
            all_text = self.extract_text_plain(element)
            if all_text:
                html_parts.append(f"<p>{all_text}</p>")

        return "\n".join(html_parts)

    def validate_section(self, section: Section) -> bool:
        """
        Validate that a Section model has all required fields.

        Args:
            section: Section model instance

        Returns:
            True if valid, False otherwise
        """
        try:
            # Pydantic validation happens automatically during construction
            # This method exists for additional custom validation if needed
            return True
        except Exception:
            return False
