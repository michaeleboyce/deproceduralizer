#!/usr/bin/env python3
"""
Load sections from NDJSON into the database.

Refactored to use BaseLoader for DRY principles.
Supports multi-jurisdiction schema.
"""

import argparse
import os
import sys
from pathlib import Path

from psycopg2.extras import execute_batch, Json

# Import BaseLoader
from dbtools.common import BaseLoader


class SectionsLoader(BaseLoader):
    """Loads sections from NDJSON to database with resume capability."""

    def validate_record(self, record):
        """Validate a section record has required fields."""
        required = ['id', 'citation', 'heading', 'text_plain', 'text_html',
                   'title_label', 'chapter_label']

        for field in required:
            if field not in record:
                print(f"Warning: Skipping record missing field '{field}'", file=sys.stderr)
                return False

        return True

    def _insert_batch(self, cursor, batch):
        """Insert a batch of sections with ON CONFLICT DO UPDATE."""
        # SQL for upsert with multi-jurisdiction support
        sql = """
            INSERT INTO sections (
                jurisdiction, id, citation, heading, text_plain, text_html,
                ancestors, title_label, chapter_label
            ) VALUES (
                %(jurisdiction)s, %(id)s, %(citation)s, %(heading)s,
                %(text_plain)s, %(text_html)s, %(ancestors)s,
                %(title_label)s, %(chapter_label)s
            )
            ON CONFLICT (jurisdiction, id) DO UPDATE SET
                citation = EXCLUDED.citation,
                heading = EXCLUDED.heading,
                text_plain = EXCLUDED.text_plain,
                text_html = EXCLUDED.text_html,
                ancestors = EXCLUDED.ancestors,
                title_label = EXCLUDED.title_label,
                chapter_label = EXCLUDED.chapter_label,
                updated_at = NOW()
        """

        # Wrap JSON fields with Json() for psycopg2
        adapted_batch = []
        for section in batch:
            adapted = section.copy()
            # Handle JSONB fields
            adapted['ancestors'] = Json(section.get('ancestors', []))
            adapted_batch.append(adapted)

        try:
            execute_batch(cursor, sql, adapted_batch)
            self.inserted_count += len(batch)
        except Exception as e:
            self.error_count += len(batch)
            print(f"Error inserting batch: {e}", file=sys.stderr)
            raise


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Load sections from NDJSON into database"
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
    loader = SectionsLoader(
        database_url=database_url,
        input_file=args.input,
        batch_size=args.batch_size,
        state_file=args.state_file,
        jurisdiction=args.jurisdiction
    )

    # Run the loader (BaseLoader handles all the complexity!)
    loader.run()


if __name__ == '__main__':
    main()
