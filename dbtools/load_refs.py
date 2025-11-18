#!/usr/bin/env python3
"""
Load section cross-references from NDJSON into the database.

Refactored to use BaseLoader for DRY principles.
Supports multi-jurisdiction schema.
"""

import argparse
import os
import sys
from pathlib import Path

import psycopg2
from psycopg2.extras import execute_batch

# Import BaseLoader
from dbtools.common import BaseLoader


class RefsLoader(BaseLoader):
    """Loads cross-references from NDJSON to database with resume capability."""

    def validate_record(self, record):
        """Validate a reference record has required fields."""
        required = ['from_id', 'to_id', 'raw_cite']

        for field in required:
            if field not in record:
                print(f"Warning: Skipping record missing field '{field}'", file=sys.stderr)
                return False

        return True

    def _insert_batch(self, cursor, batch):
        """Insert a batch of cross-references with ON CONFLICT DO NOTHING."""
        # SQL for insert with multi-jurisdiction support
        sql = """
            INSERT INTO section_refs (jurisdiction, from_id, to_id, raw_cite)
            VALUES (%(jurisdiction)s, %(from_id)s, %(to_id)s, %(raw_cite)s)
            ON CONFLICT (jurisdiction, from_id, to_id, raw_cite) DO NOTHING
        """

        try:
            # Count before insert to track actual insertions
            cursor.execute(
                "SELECT COUNT(*) FROM section_refs WHERE jurisdiction = %s",
                (self.jurisdiction,)
            )
            before_count = cursor.fetchone()[0]

            execute_batch(cursor, sql, batch)

            # Count after to determine how many were actually inserted
            cursor.execute(
                "SELECT COUNT(*) FROM section_refs WHERE jurisdiction = %s",
                (self.jurisdiction,)
            )
            after_count = cursor.fetchone()[0]

            inserted = after_count - before_count
            skipped = len(batch) - inserted

            self.inserted_count += inserted
            self.skipped_count += skipped

        except psycopg2.IntegrityError as e:
            # Foreign key violations (section doesn't exist)
            self.error_count += len(batch)
            print(f"FK constraint error in batch: {e}", file=sys.stderr)
            # Don't raise - continue with next batch
        except Exception as e:
            self.error_count += len(batch)
            print(f"Error inserting batch: {e}", file=sys.stderr)
            raise


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Load section cross-references from NDJSON into database"
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
    loader = RefsLoader(
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
