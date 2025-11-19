"""
Test script for CorpusParser class.
"""

import shutil
import sys
import tempfile
import unittest
from pathlib import Path

# Add pipeline directory to path so internal imports work
sys.path.append(str(Path(__file__).parent / "pipeline"))

from pipeline.corpus_parser import CorpusParser


class TestCorpusParser(unittest.TestCase):
    def setUp(self):
        # Create a temporary directory
        self.test_dir = Path(tempfile.mkdtemp())
        self.src_dir = self.test_dir / "src"
        self.out_dir = self.test_dir / "out"
        self.src_dir.mkdir()
        self.out_dir.mkdir()
        
        # Create dummy XML files
        (self.src_dir / "index.xml").touch()
        (self.src_dir / "1-101.xml").touch()

    def tearDown(self):
        # Remove the temporary directory
        shutil.rmtree(self.test_dir)

    def test_initialization(self):
        """Test that CorpusParser initializes correctly."""
        out_file = self.out_dir / "sections.ndjson"
        parser = CorpusParser(
            jurisdiction="dc",
            src_dir=self.src_dir,
            out_file=out_file
        )
        self.assertEqual(parser.jurisdiction, "dc")
        self.assertEqual(parser.src_dir, self.src_dir)
        self.assertEqual(parser.out_file, out_file)

    def test_validate_source_success(self):
        """Test source validation with valid files."""
        out_file = self.out_dir / "sections.ndjson"
        parser = CorpusParser(
            jurisdiction="dc",
            src_dir=self.src_dir,
            out_file=out_file
        )
        xml_files = parser.validate_source()
        self.assertEqual(len(xml_files), 1)
        self.assertEqual(xml_files[0].name, "1-101.xml")

    def test_validate_source_no_dir(self):
        """Test source validation with missing directory."""
        out_file = self.out_dir / "sections.ndjson"
        parser = CorpusParser(
            jurisdiction="dc",
            src_dir=self.test_dir / "nonexistent",
            out_file=out_file
        )
        with self.assertRaises(FileNotFoundError):
            parser.validate_source()

    def test_validate_source_no_files(self):
        """Test source validation with empty directory."""
        empty_dir = self.test_dir / "empty"
        empty_dir.mkdir()
        out_file = self.out_dir / "sections.ndjson"
        parser = CorpusParser(
            jurisdiction="dc",
            src_dir=empty_dir,
            out_file=out_file
        )
        with self.assertRaises(FileNotFoundError):
            parser.validate_source()


if __name__ == "__main__":
    unittest.main()
