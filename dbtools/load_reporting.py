#!/usr/bin/env python3
"""
Load DC Code reporting requirements from NDJSON into the database.

Features:
- Multi-table operations (4 tables: sections, global_tags, section_tags, highlights)
- Batch processing with transaction integrity
- Resume from checkpoint (.state file)
- Progress bar with detailed statistics
- JSON array expansion for tags and highlights
"""

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Optional, List, Dict, Any

import psycopg2
from psycopg2.extras import execute_batch, Json
from tqdm import tqdm


class ReportingLoader:
    """Loads reporting metadata from NDJSON to database (4 tables) with resume capability."""

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
        self.sections_updated = 0
        self.tags_created = 0
        self.section_tags_created = 0
        self.highlights_created = 0
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
                'sections_updated': self.sections_updated,
                'tags_created': self.tags_created,
                'section_tags_created': self.section_tags_created,
                'highlights_created': self.highlights_created,
                'errors': self.error_count
            }, f)

    def count_lines(self) -> int:
        """Count total lines in input file for progress bar."""
        with open(self.input_file, 'r') as f:
            return sum(1 for _ in f)

    def load_reporting(self):
        """Load reporting metadata from NDJSON file into database."""
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
                    desc="Loading reporting data",
                    unit="sections"
                )

                for line in f:
                    try:
                        report = json.loads(line)
                        batch.append(report)

                        # Process batch when full
                        if len(batch) >= self.batch_size:
                            self._process_batch(cursor, batch)
                            conn.commit()
                            batch = []

                            # Update checkpoint
                            current_offset = f.tell()
                            self.save_checkpoint(current_offset)

                        lines_processed += 1
                        pbar.update(1)
                        pbar.set_postfix({
                            'sections': self.sections_updated,
                            'tags': self.tags_created,
                            'highlights': self.highlights_created,
                            'errors': self.error_count
                        })

                    except json.JSONDecodeError as e:
                        self.error_count += 1
                        print(f"Error parsing JSON: {e}", file=sys.stderr)
                        continue

                # Process remaining batch
                if batch:
                    self._process_batch(cursor, batch)
                    conn.commit()
                    self.save_checkpoint(f.tell())

                pbar.close()

            print(f"\n✓ Load complete:")
            print(f"  - Sections updated: {self.sections_updated}")
            print(f"  - Unique tags created: {self.tags_created}")
            print(f"  - Section-tag pairs: {self.section_tags_created}")
            print(f"  - Highlight phrases: {self.highlights_created}")
            print(f"  - Errors: {self.error_count}")

        except Exception as e:
            conn.rollback()
            print(f"Error during load: {e}", file=sys.stderr)
            raise
        finally:
            cursor.close()
            conn.close()

    def _process_batch(self, cursor, batch: List[Dict[str, Any]]):
        """Process a batch across all 4 tables in a single transaction."""
        try:
            # 1. Update dc_sections
            self._update_sections(cursor, batch)

            # 2. Insert unique tags into dc_global_tags
            self._insert_global_tags(cursor, batch)

            # 3. Insert section-tag relationships
            self._insert_section_tags(cursor, batch)

            # 4. Insert highlight phrases
            self._insert_highlights(cursor, batch)

        except Exception as e:
            self.error_count += len(batch)
            print(f"Error processing batch: {e}", file=sys.stderr)
            raise

    def _update_sections(self, cursor, batch: List[Dict[str, Any]]):
        """Update dc_sections with reporting metadata."""
        # Prepare data for update
        update_data = []
        for report in batch:
            update_data.append({
                'id': report['id'],
                'has_reporting': report['has_reporting'],
                'reporting_summary': report['reporting_summary'],
                'tags': Json(report['tags'])  # Convert list to jsonb
            })

        # SQL for updating sections
        sql = """
            UPDATE dc_sections SET
              has_reporting = %(has_reporting)s,
              reporting_summary = %(reporting_summary)s,
              reporting_tags = %(tags)s,
              updated_at = now()
            WHERE id = %(id)s
        """

        execute_batch(cursor, sql, update_data)
        self.sections_updated += len(batch)

    def _insert_global_tags(self, cursor, batch: List[Dict[str, Any]]):
        """Insert unique tags into dc_global_tags."""
        # Collect all unique tags from batch
        all_tags = set()
        for report in batch:
            for tag in report['tags']:
                all_tags.add(tag)

        if not all_tags:
            return

        # Prepare tag data
        tag_data = [{'tag': tag} for tag in all_tags]

        # SQL for inserting tags (idempotent)
        sql = """
            INSERT INTO dc_global_tags (tag)
            VALUES (%(tag)s)
            ON CONFLICT (tag) DO NOTHING
        """

        # Count before insert to track new tags
        cursor.execute("SELECT COUNT(*) FROM dc_global_tags")
        before_count = cursor.fetchone()[0]

        execute_batch(cursor, sql, tag_data)

        # Count after to determine new tags
        cursor.execute("SELECT COUNT(*) FROM dc_global_tags")
        after_count = cursor.fetchone()[0]

        self.tags_created += (after_count - before_count)

    def _insert_section_tags(self, cursor, batch: List[Dict[str, Any]]):
        """Insert section-tag relationships into dc_section_tags."""
        # Expand: each section with N tags → N rows
        section_tag_data = []
        for report in batch:
            section_id = report['id']
            for tag in report['tags']:
                section_tag_data.append({
                    'section_id': section_id,
                    'tag': tag
                })

        if not section_tag_data:
            return

        # SQL for inserting section-tag pairs
        sql = """
            INSERT INTO dc_section_tags (section_id, tag)
            VALUES (%(section_id)s, %(tag)s)
            ON CONFLICT (section_id, tag) DO NOTHING
        """

        # Count before insert
        cursor.execute("SELECT COUNT(*) FROM dc_section_tags")
        before_count = cursor.fetchone()[0]

        execute_batch(cursor, sql, section_tag_data)

        # Count after to determine new pairs
        cursor.execute("SELECT COUNT(*) FROM dc_section_tags")
        after_count = cursor.fetchone()[0]

        self.section_tags_created += (after_count - before_count)

    def _insert_highlights(self, cursor, batch: List[Dict[str, Any]]):
        """Insert highlight phrases into dc_section_highlights."""
        # Expand: each section with M phrases → M rows
        highlight_data = []
        for report in batch:
            section_id = report['id']
            for phrase in report['highlight_phrases']:
                highlight_data.append({
                    'section_id': section_id,
                    'phrase': phrase
                })

        if not highlight_data:
            return

        # SQL for inserting highlights
        sql = """
            INSERT INTO dc_section_highlights (section_id, phrase)
            VALUES (%(section_id)s, %(phrase)s)
        """

        execute_batch(cursor, sql, highlight_data)
        self.highlights_created += len(highlight_data)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Load DC Code reporting metadata from NDJSON into database"
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
    loader = ReportingLoader(
        database_url=database_url,
        input_file=args.input,
        batch_size=args.batch_size,
        state_file=args.state_file
    )

    loader.load_reporting()


if __name__ == '__main__':
    main()
