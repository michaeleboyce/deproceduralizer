#!/usr/bin/env python3
"""
Load DC Code sections from NDJSON into the database.

Features:
- Batch inserts (configurable batch size)
- Resume from checkpoint (.state file)
- Progress bar with tqdm
- ON CONFLICT DO UPDATE for idempotency
"""

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Optional

import psycopg2
from psycopg2.extras import execute_batch, Json
from tqdm import tqdm


class SectionLoader:
    """Loads DC Code sections from NDJSON to database with resume capability."""

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
        self.updated_count = 0
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
                'updated': self.updated_count,
                'errors': self.error_count
            }, f)

    def count_lines(self) -> int:
        """Count total lines in input file for progress bar."""
        with open(self.input_file, 'r') as f:
            return sum(1 for _ in f)

    def load_sections(self):
        """Load sections from NDJSON file into database."""
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
                    desc="Loading sections",
                    unit="sections"
                )

                for line in f:
                    try:
                        section = json.loads(line)
                        batch.append(section)

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
                            'updated': self.updated_count,
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
            print(f"  - Updated: {self.updated_count}")
            print(f"  - Errors: {self.error_count}")

        except Exception as e:
            conn.rollback()
            print(f"Error during load: {e}", file=sys.stderr)
            raise
        finally:
            cursor.close()
            conn.close()

    def _insert_batch(self, cursor, batch):
        """Insert a batch of sections with ON CONFLICT DO UPDATE."""
        # SQL for upsert
        sql = """
            INSERT INTO dc_sections (
                id, citation, heading, text_plain, text_html,
                ancestors, title_label, chapter_label
            ) VALUES (
                %(id)s, %(citation)s, %(heading)s, %(text_plain)s, %(text_html)s,
                %(ancestors)s, %(title_label)s, %(chapter_label)s
            )
            ON CONFLICT (id) DO UPDATE SET
                citation = EXCLUDED.citation,
                heading = EXCLUDED.heading,
                text_plain = EXCLUDED.text_plain,
                text_html = EXCLUDED.text_html,
                ancestors = EXCLUDED.ancestors,
                title_label = EXCLUDED.title_label,
                chapter_label = EXCLUDED.chapter_label,
                updated_at = now()
        """

        # Wrap JSON fields with Json() for psycopg2
        adapted_batch = []
        for section in batch:
            adapted = section.copy()
            adapted['ancestors'] = Json(section['ancestors'])
            adapted_batch.append(adapted)

        try:
            execute_batch(cursor, sql, adapted_batch)
            # Note: We can't easily track inserted vs updated with execute_batch
            # For now, just count total operations
            self.inserted_count += len(batch)
        except Exception as e:
            self.error_count += len(batch)
            print(f"Error inserting batch: {e}", file=sys.stderr)
            raise


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Load DC Code sections from NDJSON into database"
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
    loader = SectionLoader(
        database_url=database_url,
        input_file=args.input,
        batch_size=args.batch_size,
        state_file=args.state_file
    )

    loader.load_sections()


if __name__ == '__main__':
    main()
