#!/usr/bin/env python3
"""
Load DC Code deadlines and dollar amounts from NDJSON into the database.

Features:
- Loads both deadlines and amounts in one script
- Batch inserts (configurable batch size)
- Resume from checkpoint (.state files)
- Progress bars with tqdm
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


class DeadlinesAmountsLoader:
    """Loads deadlines and amounts from NDJSON files to database with resume capability."""

    def __init__(
        self,
        database_url: str,
        deadlines_file: Optional[Path] = None,
        amounts_file: Optional[Path] = None,
        batch_size: int = 500,
        deadlines_state: Optional[Path] = None,
        amounts_state: Optional[Path] = None
    ):
        self.database_url = database_url
        self.deadlines_file = deadlines_file
        self.amounts_file = amounts_file
        self.batch_size = batch_size

        # State files
        self.deadlines_state = deadlines_state or (deadlines_file.with_suffix('.state') if deadlines_file else None)
        self.amounts_state = amounts_state or (amounts_file.with_suffix('.state') if amounts_file else None)

        # Statistics
        self.deadlines_inserted = 0
        self.deadlines_errors = 0
        self.amounts_inserted = 0
        self.amounts_errors = 0

    def get_checkpoint(self, state_file: Path) -> int:
        """Get the last processed byte offset from state file."""
        if state_file and state_file.exists():
            with open(state_file, 'r') as f:
                data = json.load(f)
                return data.get('byte_offset', 0)
        return 0

    def save_checkpoint(self, state_file: Path, byte_offset: int, inserted: int, errors: int):
        """Save current byte offset to state file."""
        if state_file:
            with open(state_file, 'w') as f:
                json.dump({
                    'byte_offset': byte_offset,
                    'inserted': inserted,
                    'errors': errors
                }, f)

    def count_lines(self, file_path: Path) -> int:
        """Count total lines in input file for progress bar."""
        with open(file_path, 'r') as f:
            return sum(1 for _ in f)

    def load_deadlines(self):
        """Load deadlines from NDJSON file into database."""
        if not self.deadlines_file:
            print("Skipping deadlines (no file provided)")
            return

        print(f"\n📅 Loading deadlines from {self.deadlines_file}")

        # Get starting position
        start_offset = self.get_checkpoint(self.deadlines_state)

        # Count total lines for progress
        total_lines = self.count_lines(self.deadlines_file)

        # Connect to database
        conn = psycopg2.connect(self.database_url)
        conn.autocommit = False
        cursor = conn.cursor()

        try:
            batch = []
            current_offset = 0
            lines_processed = 0

            with open(self.deadlines_file, 'r') as f:
                # Skip to checkpoint
                if start_offset > 0:
                    f.seek(start_offset)
                    current_offset = start_offset

                # Progress bar
                pbar = tqdm(
                    total=total_lines,
                    initial=lines_processed,
                    desc="Loading deadlines",
                    unit="deadlines"
                )

                for line in f:
                    try:
                        deadline = json.loads(line)
                        batch.append(deadline)

                        # Process batch when full
                        if len(batch) >= self.batch_size:
                            self._insert_deadlines_batch(cursor, batch)
                            conn.commit()
                            batch = []

                            # Update checkpoint
                            current_offset = f.tell()
                            self.save_checkpoint(
                                self.deadlines_state,
                                current_offset,
                                self.deadlines_inserted,
                                self.deadlines_errors
                            )

                        lines_processed += 1
                        pbar.update(1)
                        pbar.set_postfix({
                            'inserted': self.deadlines_inserted,
                            'errors': self.deadlines_errors
                        })

                    except json.JSONDecodeError as e:
                        self.deadlines_errors += 1
                        print(f"Error parsing JSON: {e}", file=sys.stderr)
                        continue

                # Process remaining batch
                if batch:
                    self._insert_deadlines_batch(cursor, batch)
                    conn.commit()
                    self.save_checkpoint(
                        self.deadlines_state,
                        f.tell(),
                        self.deadlines_inserted,
                        self.deadlines_errors
                    )

                pbar.close()

        except Exception as e:
            conn.rollback()
            print(f"Error during deadlines load: {e}", file=sys.stderr)
            raise
        finally:
            cursor.close()
            conn.close()

    def load_amounts(self):
        """Load dollar amounts from NDJSON file into database."""
        if not self.amounts_file:
            print("Skipping amounts (no file provided)")
            return

        print(f"\n💰 Loading amounts from {self.amounts_file}")

        # Get starting position
        start_offset = self.get_checkpoint(self.amounts_state)

        # Count total lines for progress
        total_lines = self.count_lines(self.amounts_file)

        # Connect to database
        conn = psycopg2.connect(self.database_url)
        conn.autocommit = False
        cursor = conn.cursor()

        try:
            batch = []
            current_offset = 0
            lines_processed = 0

            with open(self.amounts_file, 'r') as f:
                # Skip to checkpoint
                if start_offset > 0:
                    f.seek(start_offset)
                    current_offset = start_offset

                # Progress bar
                pbar = tqdm(
                    total=total_lines,
                    initial=lines_processed,
                    desc="Loading amounts",
                    unit="amounts"
                )

                for line in f:
                    try:
                        amount = json.loads(line)
                        batch.append(amount)

                        # Process batch when full
                        if len(batch) >= self.batch_size:
                            self._insert_amounts_batch(cursor, batch)
                            conn.commit()
                            batch = []

                            # Update checkpoint
                            current_offset = f.tell()
                            self.save_checkpoint(
                                self.amounts_state,
                                current_offset,
                                self.amounts_inserted,
                                self.amounts_errors
                            )

                        lines_processed += 1
                        pbar.update(1)
                        pbar.set_postfix({
                            'inserted': self.amounts_inserted,
                            'errors': self.amounts_errors
                        })

                    except json.JSONDecodeError as e:
                        self.amounts_errors += 1
                        print(f"Error parsing JSON: {e}", file=sys.stderr)
                        continue

                # Process remaining batch
                if batch:
                    self._insert_amounts_batch(cursor, batch)
                    conn.commit()
                    self.save_checkpoint(
                        self.amounts_state,
                        f.tell(),
                        self.amounts_inserted,
                        self.amounts_errors
                    )

                pbar.close()

        except Exception as e:
            conn.rollback()
            print(f"Error during amounts load: {e}", file=sys.stderr)
            raise
        finally:
            cursor.close()
            conn.close()

    def _insert_deadlines_batch(self, cursor, batch):
        """Insert a batch of deadlines."""
        sql = """
            INSERT INTO dc_section_deadlines (section_id, phrase, days, kind)
            VALUES (%(section_id)s, %(phrase)s, %(days)s, %(kind)s)
        """

        try:
            execute_batch(cursor, sql, batch)
            self.deadlines_inserted += len(batch)
        except Exception as e:
            self.deadlines_errors += len(batch)
            print(f"Error inserting deadlines batch: {e}", file=sys.stderr)
            raise

    def _insert_amounts_batch(self, cursor, batch):
        """Insert a batch of dollar amounts."""
        sql = """
            INSERT INTO dc_section_amounts (section_id, phrase, amount_cents)
            VALUES (%(section_id)s, %(phrase)s, %(amount_cents)s)
        """

        try:
            execute_batch(cursor, sql, batch)
            self.amounts_inserted += len(batch)
        except Exception as e:
            self.amounts_errors += len(batch)
            print(f"Error inserting amounts batch: {e}", file=sys.stderr)
            raise

    def run(self):
        """Run both deadlines and amounts loading."""
        print("=" * 60)
        print("DC Code Obligations Loader")
        print("=" * 60)

        # Load deadlines
        if self.deadlines_file:
            self.load_deadlines()

        # Load amounts
        if self.amounts_file:
            self.load_amounts()

        # Print summary
        print("\n" + "=" * 60)
        print("✓ Load Complete")
        print("=" * 60)
        if self.deadlines_file:
            print(f"Deadlines: {self.deadlines_inserted} inserted, {self.deadlines_errors} errors")
        if self.amounts_file:
            print(f"Amounts:   {self.amounts_inserted} inserted, {self.amounts_errors} errors")
        print(f"Total:     {self.deadlines_inserted + self.amounts_inserted} records")
        print("=" * 60)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Load DC Code deadlines and dollar amounts from NDJSON into database"
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
        help='Number of rows per batch (default: 500 or LOADER_BATCH_SIZE env)'
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

    # Create loader and run
    loader = DeadlinesAmountsLoader(
        database_url=database_url,
        deadlines_file=args.deadlines,
        amounts_file=args.amounts,
        batch_size=args.batch_size,
        deadlines_state=args.deadlines_state,
        amounts_state=args.amounts_state
    )

    loader.run()


if __name__ == '__main__':
    main()
