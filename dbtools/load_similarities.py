#!/usr/bin/env python3
"""
Load section similarities from NDJSON into the database.

Refactored to use BaseLoader for DRY principles.
Supports multi-jurisdiction schema.
"""

import argparse
import os
import sys
from pathlib import Path

from psycopg2.extras import execute_batch

# Import BaseLoader
from dbtools.common import BaseLoader


class SimilaritiesLoader(BaseLoader):
    """Loads section similarities from NDJSON to database with resume capability."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.updated_count = 0  # Track updates separately from inserts

    def validate_record(self, record):
        """Validate a similarity record has required fields."""
        required = ['section_a', 'section_b', 'similarity']

        for field in required:
            if field not in record:
                print(f"Warning: Skipping record missing field '{field}'", file=sys.stderr)
                return False

        return True

    def _insert_batch(self, cursor, batch):
        """Insert a batch of similarities with ON CONFLICT DO UPDATE."""
        # SQL for upsert - allows re-running with updated similarity scores
        sql = """
            INSERT INTO section_similarities (jurisdiction, section_a, section_b, similarity)
            VALUES (%(jurisdiction)s, %(section_a)s, %(section_b)s, %(similarity)s)
            ON CONFLICT (jurisdiction, section_a, section_b) DO UPDATE
              SET similarity = EXCLUDED.similarity
        """

        try:
            # Count before insert to track new vs updated
            cursor.execute(
                "SELECT COUNT(*) FROM section_similarities WHERE jurisdiction = %s",
                (self.jurisdiction,)
            )
            before_count = cursor.fetchone()[0]

            execute_batch(cursor, sql, batch)

            # Count after to determine insertions vs updates
            cursor.execute(
                "SELECT COUNT(*) FROM section_similarities WHERE jurisdiction = %s",
                (self.jurisdiction,)
            )
            after_count = cursor.fetchone()[0]

            inserted = after_count - before_count
            updated = len(batch) - inserted

            self.inserted_count += inserted
            self.updated_count += updated

        except Exception as e:
            self.error_count += len(batch)
            print(f"Error inserting batch: {e}", file=sys.stderr)
            raise


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Load section similarities from NDJSON into database"
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
    loader = SimilaritiesLoader(
        database_url=database_url,
        input_file=args.input,
        batch_size=args.batch_size,
        state_file=args.state_file,
        jurisdiction=args.jurisdiction
    )

    # Run the loader (BaseLoader handles all the complexity!)
    loader.run()

    # Print additional stats (updated count)
    if loader.updated_count > 0:
        print(f"  - Updated: {loader.updated_count}")


if __name__ == '__main__':
    main()
