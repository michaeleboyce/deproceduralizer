#!/usr/bin/env python3
"""
Load section deadlines and dollar amounts from NDJSON into the database.

Refactored to use BaseLoader for DRY principles.
Supports multi-jurisdiction schema.
"""

import argparse
import os
import sys
from pathlib import Path
from typing import Optional

from psycopg2.extras import execute_batch

# Import BaseLoader
from dbtools.common import BaseLoader


class DeadlinesLoader(BaseLoader):
    """Loads deadlines from NDJSON to database with resume capability."""

    def validate_record(self, record):
        """Validate a deadline record has required fields."""
        required = ['section_id', 'phrase', 'days', 'kind']

        for field in required:
            if field not in record:
                print(f"Warning: Skipping deadline record missing field '{field}'", file=sys.stderr)
                return False

        return True

    def _insert_batch(self, cursor, batch):
        """Insert a batch of deadlines."""
        sql = """
            INSERT INTO section_deadlines (jurisdiction, section_id, phrase, days, kind)
            VALUES (%(jurisdiction)s, %(section_id)s, %(phrase)s, %(days)s, %(kind)s)
        """

        try:
            execute_batch(cursor, sql, batch)
            self.inserted_count += len(batch)
        except Exception as e:
            self.error_count += len(batch)
            print(f"Error inserting deadlines batch: {e}", file=sys.stderr)
            raise


class AmountsLoader(BaseLoader):
    """Loads dollar amounts from NDJSON to database with resume capability."""

    def validate_record(self, record):
        """Validate an amount record has required fields."""
        required = ['section_id', 'phrase', 'amount_cents']

        for field in required:
            if field not in record:
                print(f"Warning: Skipping amount record missing field '{field}'", file=sys.stderr)
                return False

        return True

    def _insert_batch(self, cursor, batch):
        """Insert a batch of dollar amounts."""
        sql = """
            INSERT INTO section_amounts (jurisdiction, section_id, phrase, amount_cents)
            VALUES (%(jurisdiction)s, %(section_id)s, %(phrase)s, %(amount_cents)s)
        """

        try:
            execute_batch(cursor, sql, batch)
            self.inserted_count += len(batch)
        except Exception as e:
            self.error_count += len(batch)
            print(f"Error inserting amounts batch: {e}", file=sys.stderr)
            raise


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Load section deadlines and dollar amounts from NDJSON into database"
    )
    parser.add_argument(
        '--deadlines',
        type=Path,
        help='Path to deadlines NDJSON file'
    )
    parser.add_argument(
        '--amounts',
        type=Path,
        help='Path to amounts NDJSON file'
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
        '--deadlines-state',
        type=Path,
        help='Path to deadlines state file (default: deadlines_file.state)'
    )
    parser.add_argument(
        '--amounts-state',
        type=Path,
        help='Path to amounts state file (default: amounts_file.state)'
    )

    args = parser.parse_args()

    # Require at least one file
    if not args.deadlines and not args.amounts:
        print("Error: At least one of --deadlines or --amounts must be provided", file=sys.stderr)
        sys.exit(1)

    # Get database URL from environment
    database_url = os.getenv('DATABASE_URL')
    if not database_url:
        print("Error: DATABASE_URL environment variable not set", file=sys.stderr)
        sys.exit(1)

    # Verify input files exist
    if args.deadlines and not args.deadlines.exists():
        print(f"Error: Deadlines file not found: {args.deadlines}", file=sys.stderr)
        sys.exit(1)
    if args.amounts and not args.amounts.exists():
        print(f"Error: Amounts file not found: {args.amounts}", file=sys.stderr)
        sys.exit(1)

    # Track combined statistics
    total_inserted = 0
    total_errors = 0

    print("=" * 60)
    print("Obligations Loader (Deadlines & Amounts)")
    print("=" * 60)

    # Load deadlines if provided
    if args.deadlines:
        print(f"\n📅 Loading deadlines from {args.deadlines}")
        loader = DeadlinesLoader(
            database_url=database_url,
            input_file=args.deadlines,
            batch_size=args.batch_size,
            state_file=args.deadlines_state,
            jurisdiction=args.jurisdiction
        )
        loader.run()
        total_inserted += loader.inserted_count
        total_errors += loader.error_count

    # Load amounts if provided
    if args.amounts:
        print(f"\n💰 Loading amounts from {args.amounts}")
        loader = AmountsLoader(
            database_url=database_url,
            input_file=args.amounts,
            batch_size=args.batch_size,
            state_file=args.amounts_state,
            jurisdiction=args.jurisdiction
        )
        loader.run()
        total_inserted += loader.inserted_count
        total_errors += loader.error_count

    # Print combined summary
    print("\n" + "=" * 60)
    print("✓ Load Complete")
    print("=" * 60)
    print(f"Total inserted: {total_inserted}")
    print(f"Total errors:   {total_errors}")
    print("=" * 60)


if __name__ == '__main__':
    main()
