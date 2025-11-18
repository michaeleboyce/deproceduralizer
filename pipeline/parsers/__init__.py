"""
Parser module for multi-jurisdiction legal code XML processing.

This module provides abstract base classes and jurisdiction-specific parsers
for processing legal code XML files into structured data.

Usage:
    from parsers import get_parser

    parser = get_parser("dc")
    section = parser.parse_section(xml_path)
"""

from typing import Optional

from .base import BaseParser


def get_parser(jurisdiction: str) -> BaseParser:
    """
    Factory function to get the appropriate parser for a jurisdiction.

    Args:
        jurisdiction: Jurisdiction code (e.g., "dc", "ca", "ny")

    Returns:
        Parser instance for the specified jurisdiction

    Raises:
        ValueError: If jurisdiction is not supported
    """
    jurisdiction = jurisdiction.lower()

    if jurisdiction == "dc":
        from .dc import DCParser
        return DCParser()
    elif jurisdiction == "ca":
        raise NotImplementedError("California parser not yet implemented")
    elif jurisdiction == "ny":
        raise NotImplementedError("New York parser not yet implemented")
    else:
        raise ValueError(
            f"Unsupported jurisdiction: {jurisdiction}. "
            f"Supported: dc (California and New York coming soon)"
        )


__all__ = ["get_parser", "BaseParser"]
