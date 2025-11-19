#!/usr/bin/env python3
"""
Load section similarity classifications from NDJSON into the database.

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


class ClassificationsLoader(BaseLoader):
    """Loads similarity classifications from NDJSON to database with resume capability."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.updated_count = 0  # Track updates separately from inserts

    def validate_record(self, record):
        """Validate a classification record has required fields."""
        required = ['section_a', 'section_b', 'classification', 'explanation',
                   'model_used', 'analyzed_at']

        for field in required:
            if field not in record:
                print(f"Warning: Skipping record missing field '{field}'", file=sys.stderr)
                return False

        return True

    def _insert_batch(self, cursor, batch):
        """Insert a batch of classifications with ON CONFLICT DO UPDATE."""
        # SQL for upsert - allows re-running with updated classifications
        # Now includes cross-encoder triage metadata for Model Cascading
        sql = """
            INSERT INTO section_similarity_classifications
              (jurisdiction, section_a, section_b, classification, explanation,
               model_used, analyzed_at, cross_encoder_label, cross_encoder_score)
            VALUES
              (%(jurisdiction)s, %(section_a)s, %(section_b)s, %(classification)s,
               %(explanation)s, %(model_used)s, %(analyzed_at)s,
               %(cross_encoder_label)s, %(cross_encoder_score)s)
            ON CONFLICT (jurisdiction, section_a, section_b) DO UPDATE
              SET classification = EXCLUDED.classification,
                  explanation = EXCLUDED.explanation,
                  model_used = EXCLUDED.model_used,
                  analyzed_at = EXCLUDED.analyzed_at,
                  cross_encoder_label = EXCLUDED.cross_encoder_label,
                  cross_encoder_score = EXCLUDED.cross_encoder_score
        """

        # Normalize batch to ensure cross-encoder fields exist (backwards compatibility)
        normalized_batch = []
        for record in batch:
            normalized = record.copy()
            if 'cross_encoder_label' not in normalized:
                normalized['cross_encoder_label'] = None
            if 'cross_encoder_score' not in normalized:
                normalized['cross_encoder_score'] = None
            normalized_batch.append(normalized)

        try:
            # Count before insert to track new vs updated
            cursor.execute(
                "SELECT COUNT(*) FROM section_similarity_classifications WHERE jurisdiction = %s",
                (self.jurisdiction,)
            )
            before_count = cursor.fetchone()[0]

            execute_batch(cursor, sql, normalized_batch)

            # Count after to determine insertions vs updates
            cursor.execute(
                "SELECT COUNT(*) FROM section_similarity_classifications WHERE jurisdiction = %s",
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
        description="Load section similarity classifications from NDJSON into database"
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
    loader = ClassificationsLoader(
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
