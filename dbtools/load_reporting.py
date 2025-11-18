#!/usr/bin/env python3
"""
Load section reporting requirements from NDJSON into the database.

Refactored to use BaseLoader for DRY principles.
Supports multi-jurisdiction schema.

Features:
- Multi-table operations (4 tables: sections, global_tags, section_tags, highlights)
- Batch processing with transaction integrity
- JSON array expansion for tags and highlights
"""

import argparse
import os
import sys
from pathlib import Path
from typing import List, Dict, Any

from psycopg2.extras import execute_batch, Json

# Import BaseLoader
from dbtools.common import BaseLoader


class ReportingLoader(BaseLoader):
    """Loads reporting metadata from NDJSON to database (4 tables) with resume capability."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Custom statistics for this complex multi-table loader
        self.sections_updated = 0
        self.tags_created = 0
        self.section_tags_created = 0
        self.highlights_created = 0

    def validate_record(self, record):
        """Validate a reporting record has required fields."""
        required = ['id', 'has_reporting', 'reporting_summary', 'tags', 'highlight_phrases']

        for field in required:
            if field not in record:
                print(f"Warning: Skipping record missing field '{field}'", file=sys.stderr)
                return False

        return True

    def _insert_batch(self, cursor, batch: List[Dict[str, Any]]):
        """Process a batch across all 4 tables in a single transaction."""
        try:
            # 1. Update sections
            self._update_sections(cursor, batch)

            # 2. Insert unique tags into global_tags
            self._insert_global_tags(cursor, batch)

            # 3. Insert section-tag relationships
            self._insert_section_tags(cursor, batch)

            # 4. Insert highlight phrases
            self._insert_highlights(cursor, batch)

        except Exception as e:
            self.error_count += len(batch)
            print(f"Error processing batch: {e}", file=sys.stderr)
            raise

    def _update_sections(self, cursor, batch: List[Dict[str, Any]]):
        """Update sections with reporting metadata."""
        # Prepare data for update
        update_data = []
        for report in batch:
            update_data.append({
                'jurisdiction': self.jurisdiction,
                'id': report['id'],
                'has_reporting': report['has_reporting'],
                'reporting_summary': report['reporting_summary'],
                'tags': Json(report['tags'])  # Convert list to jsonb
            })

        # SQL for updating sections
        sql = """
            UPDATE sections SET
              has_reporting = %(has_reporting)s,
              reporting_summary = %(reporting_summary)s,
              reporting_tags = %(tags)s,
              updated_at = now()
            WHERE jurisdiction = %(jurisdiction)s AND id = %(id)s
        """

        execute_batch(cursor, sql, update_data)
        self.sections_updated += len(batch)

    def _insert_global_tags(self, cursor, batch: List[Dict[str, Any]]):
        """Insert unique tags into global_tags."""
        # Collect all unique tags from batch
        all_tags = set()
        for report in batch:
            for tag in report['tags']:
                all_tags.add(tag)

        if not all_tags:
            return

        # Prepare tag data
        tag_data = [{'tag': tag} for tag in all_tags]

        # SQL for inserting tags (idempotent)
        sql = """
            INSERT INTO global_tags (tag)
            VALUES (%(tag)s)
            ON CONFLICT (tag) DO NOTHING
        """

        # Count before insert to track new tags
        cursor.execute("SELECT COUNT(*) FROM global_tags")
        before_count = cursor.fetchone()[0]

        execute_batch(cursor, sql, tag_data)

        # Count after to determine new tags
        cursor.execute("SELECT COUNT(*) FROM global_tags")
        after_count = cursor.fetchone()[0]

        self.tags_created += (after_count - before_count)

    def _insert_section_tags(self, cursor, batch: List[Dict[str, Any]]):
        """Insert section-tag relationships into section_tags."""
        # Expand: each section with N tags → N rows
        section_tag_data = []
        for report in batch:
            section_id = report['id']
            for tag in report['tags']:
                section_tag_data.append({
                    'jurisdiction': self.jurisdiction,
                    'section_id': section_id,
                    'tag': tag
                })

        if not section_tag_data:
            return

        # SQL for inserting section-tag pairs
        sql = """
            INSERT INTO section_tags (jurisdiction, section_id, tag)
            VALUES (%(jurisdiction)s, %(section_id)s, %(tag)s)
            ON CONFLICT (jurisdiction, section_id, tag) DO NOTHING
        """

        # Count before insert
        cursor.execute(
            "SELECT COUNT(*) FROM section_tags WHERE jurisdiction = %s",
            (self.jurisdiction,)
        )
        before_count = cursor.fetchone()[0]

        execute_batch(cursor, sql, section_tag_data)

        # Count after to determine new pairs
        cursor.execute(
            "SELECT COUNT(*) FROM section_tags WHERE jurisdiction = %s",
            (self.jurisdiction,)
        )
        after_count = cursor.fetchone()[0]

        self.section_tags_created += (after_count - before_count)

    def _insert_highlights(self, cursor, batch: List[Dict[str, Any]]):
        """Insert highlight phrases into section_highlights."""
        # Expand: each section with M phrases → M rows
        highlight_data = []
        for report in batch:
            section_id = report['id']
            for phrase in report['highlight_phrases']:
                highlight_data.append({
                    'jurisdiction': self.jurisdiction,
                    'section_id': section_id,
                    'phrase': phrase
                })

        if not highlight_data:
            return

        # SQL for inserting highlights
        sql = """
            INSERT INTO section_highlights (jurisdiction, section_id, phrase)
            VALUES (%(jurisdiction)s, %(section_id)s, %(phrase)s)
        """

        execute_batch(cursor, sql, highlight_data)
        self.highlights_created += len(highlight_data)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Load section reporting metadata from NDJSON into database"
    )
    parser.add_argument(
        '--input',
        type=Path,
        required=True,
        help='Path to input NDJSON file'
    )
    parser.add_argument(
        '--batch-size',
        type=int,
        default=int(os.getenv('LOADER_BATCH_SIZE', '500')),
        help='Number of rows per batch (default: 500)'
    )
    parser.add_argument(
        '--jurisdiction',
        type=str,
        default='dc',
        help='Jurisdiction code (default: dc)'
    )
    parser.add_argument(
        '--state-file',
        type=Path,
        help='Path to state file (default: input_file.state)'
    )

    args = parser.parse_args()

    # Get database URL from environment
    database_url = os.getenv('DATABASE_URL')
    if not database_url:
        print("Error: DATABASE_URL environment variable not set", file=sys.stderr)
        sys.exit(1)

    # Verify input file exists
    if not args.input.exists():
        print(f"Error: Input file not found: {args.input}", file=sys.stderr)
        sys.exit(1)

    # Create loader and run
    loader = ReportingLoader(
        database_url=database_url,
        input_file=args.input,
        batch_size=args.batch_size,
        state_file=args.state_file,
        jurisdiction=args.jurisdiction
    )

    # Run the loader (BaseLoader handles all the complexity!)
    loader.run()

    # Print detailed statistics for this multi-table loader
    print(f"  - Sections updated: {loader.sections_updated}")
    print(f"  - Unique tags created: {loader.tags_created}")
    print(f"  - Section-tag pairs: {loader.section_tags_created}")
    print(f"  - Highlight phrases: {loader.highlights_created}")


if __name__ == '__main__':
    main()
