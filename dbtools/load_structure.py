#!/usr/bin/env python3
"""
Load structure hierarchy from NDJSON into the database.

Supports multi-jurisdiction schema.
"""

import argparse
import os
import sys
from pathlib import Path

from psycopg2.extras import execute_batch

# Import BaseLoader
from dbtools.common import BaseLoader


class StructureLoader(BaseLoader):
    """Loads structure hierarchy from NDJSON to database with resume capability."""

    def validate_record(self, record):
        """Validate a structure record has required fields."""
        required = ['jurisdiction', 'id', 'level', 'label', 'heading', 'ordinal']

        for field in required:
            if field not in record:
                print(f"Warning: Skipping record missing field '{field}'", file=sys.stderr)
                return False

        return True

    def _insert_batch(self, cursor, batch):
        """Insert a batch of structure nodes with ON CONFLICT DO UPDATE."""
        # SQL for upsert with multi-jurisdiction support
        sql = """
            INSERT INTO structure (
                jurisdiction, id, parent_id, level, label, heading, ordinal
            ) VALUES (
                %(jurisdiction)s, %(id)s, %(parent_id)s, %(level)s,
                %(label)s, %(heading)s, %(ordinal)s
            )
            ON CONFLICT (jurisdiction, id) DO UPDATE SET
                parent_id = EXCLUDED.parent_id,
                level = EXCLUDED.level,
                label = EXCLUDED.label,
                heading = EXCLUDED.heading,
                ordinal = EXCLUDED.ordinal
        """

        # Ensure all records have parent_id (even if None)
        normalized_batch = []
        for record in batch:
            normalized = record.copy()
            if 'parent_id' not in normalized:
                normalized['parent_id'] = None
            normalized_batch.append(normalized)

        try:
            execute_batch(cursor, sql, normalized_batch)
            self.inserted_count += len(batch)
        except Exception as e:
            self.error_count += len(batch)
            print(f"Error inserting batch: {e}", file=sys.stderr)
            raise


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Load structure hierarchy from NDJSON into database"
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
    loader = StructureLoader(
        database_url=database_url,
        input_file=args.input,
        batch_size=args.batch_size,
        state_file=args.state_file,
        jurisdiction=args.jurisdiction
    )

    # Run the loader (BaseLoader handles all the complexity!)
    loader.run()

    return 0


if __name__ == '__main__':
    sys.exit(main())
