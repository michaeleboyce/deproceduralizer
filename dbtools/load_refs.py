#!/usr/bin/env python3
"""
Load DC Code cross-references from NDJSON into the database.

Features:
- Batch inserts (configurable batch size)
- Resume from checkpoint (.state file)
- Progress bar with tqdm
- ON CONFLICT DO NOTHING for idempotency
"""

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Optional

import psycopg2
from psycopg2.extras import execute_batch
from tqdm import tqdm


class RefLoader:
    """Loads cross-references from NDJSON to database with resume capability."""

    def __init__(
        self,
        database_url: str,
        input_file: Path,
        batch_size: int = 500,
        state_file: Optional[Path] = None
    ):
        self.database_url = database_url
        self.input_file = input_file
        self.batch_size = batch_size
        self.state_file = state_file or input_file.with_suffix('.state')

        # Statistics
        self.inserted_count = 0
        self.skipped_count = 0
        self.error_count = 0

    def get_checkpoint(self) -> int:
        """Get the last processed byte offset from state file."""
        if self.state_file.exists():
            with open(self.state_file, 'r') as f:
                data = json.load(f)
                return data.get('byte_offset', 0)
        return 0

    def save_checkpoint(self, byte_offset: int):
        """Save current byte offset to state file."""
        with open(self.state_file, 'w') as f:
            json.dump({
                'byte_offset': byte_offset,
                'inserted': self.inserted_count,
                'skipped': self.skipped_count,
                'errors': self.error_count
            }, f)

    def count_lines(self) -> int:
        """Count total lines in input file for progress bar."""
        with open(self.input_file, 'r') as f:
            return sum(1 for _ in f)

    def load_refs(self):
        """Load cross-references from NDJSON file into database."""
        # Get starting position
        start_offset = self.get_checkpoint()

        # Count total lines for progress
        total_lines = self.count_lines()

        # Connect to database
        conn = psycopg2.connect(self.database_url)
        conn.autocommit = False
        cursor = conn.cursor()

        try:
            batch = []
            current_offset = 0
            lines_processed = 0

            with open(self.input_file, 'r') as f:
                # Skip to checkpoint
                if start_offset > 0:
                    f.seek(start_offset)
                    current_offset = start_offset

                # Progress bar
                pbar = tqdm(
                    total=total_lines,
                    initial=lines_processed,
                    desc="Loading cross-refs",
                    unit="refs"
                )

                for line in f:
                    try:
                        ref = json.loads(line)
                        batch.append(ref)

                        # Process batch when full
                        if len(batch) >= self.batch_size:
                            self._insert_batch(cursor, batch)
                            conn.commit()
                            batch = []

                            # Update checkpoint
                            current_offset = f.tell()
                            self.save_checkpoint(current_offset)

                        lines_processed += 1
                        pbar.update(1)
                        pbar.set_postfix({
                            'inserted': self.inserted_count,
                            'skipped': self.skipped_count,
                            'errors': self.error_count
                        })

                    except json.JSONDecodeError as e:
                        self.error_count += 1
                        print(f"Error parsing JSON: {e}", file=sys.stderr)
                        continue

                # Process remaining batch
                if batch:
                    self._insert_batch(cursor, batch)
                    conn.commit()
                    self.save_checkpoint(f.tell())

                pbar.close()

            print(f"\n✓ Load complete:")
            print(f"  - Inserted: {self.inserted_count}")
            print(f"  - Skipped (duplicates): {self.skipped_count}")
            print(f"  - Errors: {self.error_count}")

        except Exception as e:
            conn.rollback()
            print(f"Error during load: {e}", file=sys.stderr)
            raise
        finally:
            cursor.close()
            conn.close()

    def _insert_batch(self, cursor, batch):
        """Insert a batch of cross-references with ON CONFLICT DO NOTHING."""
        # SQL for insert with conflict handling
        sql = """
            INSERT INTO dc_section_refs (from_id, to_id, raw_cite)
            VALUES (%(from_id)s, %(to_id)s, %(raw_cite)s)
            ON CONFLICT (from_id, to_id, raw_cite) DO NOTHING
        """

        try:
            # Count before insert to track actual insertions
            cursor.execute("SELECT COUNT(*) FROM dc_section_refs")
            before_count = cursor.fetchone()[0]

            execute_batch(cursor, sql, batch)

            # Count after to determine how many were actually inserted
            cursor.execute("SELECT COUNT(*) FROM dc_section_refs")
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
        description="Load DC Code cross-references from NDJSON into database"
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
        help='Number of rows per batch (default: 500 or LOADER_BATCH_SIZE env)'
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
    loader = RefLoader(
        database_url=database_url,
        input_file=args.input,
        batch_size=args.batch_size,
        state_file=args.state_file
    )

    loader.load_refs()


if __name__ == '__main__':
    main()
