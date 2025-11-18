#!/usr/bin/env python3
"""
Load enhanced obligations from NDJSON into the database.

Loads obligations extracted by LLM with categories, values, and units.
Supports multi-jurisdiction schema with resume capability.
"""

import argparse
import os
import sys
from pathlib import Path

from psycopg2.extras import execute_batch

# Import BaseLoader
from dbtools.common import BaseLoader


class ObligationsLoader(BaseLoader):
    """Loads enhanced obligations from NDJSON to database with resume capability."""

    def validate_record(self, record):
        """Validate an obligation record has required fields."""
        required = ['section_id', 'category', 'phrase']

        for field in required:
            if field not in record:
                print(f"Warning: Skipping obligation record missing field '{field}'", file=sys.stderr)
                return False

        return True

    def _insert_batch(self, cursor, batch):
        """Insert a batch of obligations."""
        sql = """
            INSERT INTO obligations (jurisdiction, section_id, category, phrase, value, unit, confidence)
            VALUES (%(jurisdiction)s, %(section_id)s, %(category)s, %(phrase)s, %(value)s, %(unit)s, %(confidence)s)
        """

        # Prepare batch with optional fields
        prepared_batch = []
        for record in batch:
            prepared_record = {
                'jurisdiction': record['jurisdiction'],
                'section_id': record['section_id'],
                'category': record['category'],
                'phrase': record['phrase'],
                'value': record.get('value'),  # Optional
                'unit': record.get('unit'),    # Optional
                'confidence': record.get('confidence', 0.9)  # Default confidence
            }
            prepared_batch.append(prepared_record)

        try:
            execute_batch(cursor, sql, prepared_batch)
            self.inserted_count += len(prepared_batch)
        except Exception as e:
            self.error_count += len(prepared_batch)
            print(f"Error inserting obligations batch: {e}", file=sys.stderr)
            raise


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Load enhanced obligations from NDJSON into database"
    )
    parser.add_argument(
        '--input',
        type=Path,
        required=True,
        help='Path to obligations NDJSON file'
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
        '--state',
        type=Path,
        help='Path to state file for resume capability (default: input_file.state)'
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

    print("=" * 60)
    print("Enhanced Obligations Loader")
    print("=" * 60)
    print(f"\n📊 Loading obligations from {args.input}")

    # Create and run loader
    loader = ObligationsLoader(
        database_url=database_url,
        input_file=args.input,
        batch_size=args.batch_size,
        state_file=args.state,
        jurisdiction=args.jurisdiction
    )
    loader.run()

    # Print summary
    print("\n" + "=" * 60)
    print("✓ Load Complete")
    print("=" * 60)
    print(f"Total inserted: {loader.inserted_count}")
    print(f"Total errors:   {loader.error_count}")
    print("=" * 60)


if __name__ == '__main__':
    main()
