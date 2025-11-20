#!/usr/bin/env python3
"""
Load Pahlka implementation analysis results from NDJSON into the database.

Supports multi-jurisdiction schema and uses BaseLoader for DRY principles.

Features:
- Multi-table operations (3 tables: section_pahlka_implementations, pahlka_implementation_indicators, section_pahlka_highlights)
- Batch processing with transaction integrity
- JSON array expansion for indicators and highlights
"""

import argparse
import os
import sys
from pathlib import Path
from typing import List, Dict, Any

from psycopg2.extras import execute_batch

# Import BaseLoader
from dbtools.common import BaseLoader


class PahlkaImplementationLoader(BaseLoader):
    """Loads Pahlka implementation analysis from NDJSON to database (3 tables) with resume capability."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Custom statistics for this multi-table loader
        self.implementations_inserted = 0
        self.indicators_inserted = 0
        self.highlights_inserted = 0

    def validate_record(self, record):
        """Validate a Pahlka implementation record has required fields."""
        required = [
            'section_id',
            'has_implementation_issues',
            'indicators',
            'summary',
            'requires_technical_review',
            'model_used',
            'analyzed_at'
        ]

        for field in required:
            if field not in record:
                print(f"Warning: Skipping record missing field '{field}'", file=sys.stderr)
                return False

        return True

    def _insert_batch(self, cursor, batch: List[Dict[str, Any]]):
        """Process a batch across all 3 tables in a single transaction."""
        try:
            # 1. Insert into section_pahlka_implementations
            self._insert_implementations(cursor, batch)

            # 2. Insert indicators (and get their IDs)
            indicator_ids = self._insert_indicators(cursor, batch)

            # 3. Insert highlight phrases
            self._insert_highlights(cursor, batch, indicator_ids)

        except Exception as e:
            self.error_count += len(batch)
            print(f"Error processing batch: {e}", file=sys.stderr)
            raise

    def _insert_implementations(self, cursor, batch: List[Dict[str, Any]]):
        """Insert main Pahlka implementation analysis records."""
        # Prepare data
        data = []
        for record in batch:
            data.append({
                'jurisdiction': self.jurisdiction,
                'section_id': record['section_id'],
                'has_implementation_issues': record['has_implementation_issues'],
                'overall_complexity': record.get('overall_complexity'),
                'summary': record.get('summary', ''),
                'requires_technical_review': record['requires_technical_review'],
                'model_used': record['model_used'],
                'analyzed_at': record['analyzed_at']
            })

        # SQL for inserting/updating implementations
        sql = """
            INSERT INTO section_pahlka_implementations (
                jurisdiction, section_id, has_implementation_issues, overall_complexity,
                summary, requires_technical_review, model_used, analyzed_at
            )
            VALUES (
                %(jurisdiction)s, %(section_id)s, %(has_implementation_issues)s, %(overall_complexity)s,
                %(summary)s, %(requires_technical_review)s, %(model_used)s, %(analyzed_at)s
            )
            ON CONFLICT (jurisdiction, section_id) DO UPDATE SET
                has_implementation_issues = EXCLUDED.has_implementation_issues,
                overall_complexity = EXCLUDED.overall_complexity,
                summary = EXCLUDED.summary,
                requires_technical_review = EXCLUDED.requires_technical_review,
                model_used = EXCLUDED.model_used,
                analyzed_at = EXCLUDED.analyzed_at
        """

        execute_batch(cursor, sql, data)
        self.implementations_inserted += len(batch)

    def _insert_indicators(self, cursor, batch: List[Dict[str, Any]]) -> Dict[str, List[int]]:
        """
        Insert Pahlka implementation indicators and return mapping of section_id -> indicator IDs.

        Returns:
            Dict mapping section_id to list of indicator IDs (in order)
        """
        # First, delete existing indicators for these sections (to avoid duplicates on re-run)
        section_ids = [record['section_id'] for record in batch]
        if section_ids:
            cursor.execute(
                """
                DELETE FROM pahlka_implementation_indicators
                WHERE jurisdiction = %s AND section_id = ANY(%s)
                """,
                (self.jurisdiction, section_ids)
            )

        # Build list of (section_id, indicator_data) tuples
        all_indicators = []
        for record in batch:
            section_id = record['section_id']
            for indicator in record.get('indicators', []):
                all_indicators.append((section_id, indicator))

        # Nothing to insert
        if not all_indicators:
            return {}

        # Prepare data
        data = []
        for section_id, indicator in all_indicators:
            data.append({
                'jurisdiction': self.jurisdiction,
                'section_id': section_id,
                'category': indicator['category'],
                'complexity': indicator['complexity'],
                'implementation_approach': indicator['implementation_approach'],
                'effort_estimate': indicator.get('effort_estimate'),
                'explanation': indicator['explanation']
            })

        # SQL to insert indicators and return IDs
        sql = """
            INSERT INTO pahlka_implementation_indicators (
                jurisdiction, section_id, category, complexity,
                implementation_approach, effort_estimate, explanation
            )
            VALUES (
                %(jurisdiction)s, %(section_id)s, %(category)s, %(complexity)s,
                %(implementation_approach)s, %(effort_estimate)s, %(explanation)s
            )
            RETURNING id, section_id
        """

        # Execute and collect returned IDs
        indicator_ids = {}  # section_id -> [id1, id2, ...]

        for row_data in data:
            cursor.execute(sql, row_data)
            result = cursor.fetchone()
            returned_id = result[0]
            section_id = result[1]

            if section_id not in indicator_ids:
                indicator_ids[section_id] = []
            indicator_ids[section_id].append(returned_id)

        self.indicators_inserted += len(data)

        return indicator_ids

    def _insert_highlights(
        self,
        cursor,
        batch: List[Dict[str, Any]],
        indicator_ids: Dict[str, List[int]]
    ):
        """Insert highlight phrases for each indicator."""
        # Build list of (indicator_id, phrase) tuples
        all_highlights = []

        for record in batch:
            section_id = record['section_id']
            indicators = record.get('indicators', [])

            # Get indicator IDs for this section
            ids_for_section = indicator_ids.get(section_id, [])

            # Match indicators to IDs (they're in order)
            for idx, indicator in enumerate(indicators):
                if idx >= len(ids_for_section):
                    print(f"Warning: Indicator index {idx} exceeds ID list for section {section_id}", file=sys.stderr)
                    continue

                indicator_id = ids_for_section[idx]
                phrases = indicator.get('matched_phrases', [])

                for phrase in phrases:
                    all_highlights.append((indicator_id, phrase))

        # Nothing to insert
        if not all_highlights:
            return

        # Prepare data
        data = [
            {'indicator_id': indicator_id, 'phrase': phrase}
            for indicator_id, phrase in all_highlights
        ]

        # SQL to insert highlights
        sql = """
            INSERT INTO section_pahlka_highlights (indicator_id, phrase)
            VALUES (%(indicator_id)s, %(phrase)s)
        """

        execute_batch(cursor, sql, data)
        self.highlights_inserted += len(data)

    def run(self):
        """Override run to print custom statistics."""
        super().run()

        # Print custom statistics
        print(f"\n✓ Pahlka Implementation Loader Statistics:")
        print(f"  - Main records inserted/updated: {self.implementations_inserted}")
        print(f"  - Indicators inserted: {self.indicators_inserted}")
        print(f"  - Highlight phrases inserted: {self.highlights_inserted}")


def main():
    parser = argparse.ArgumentParser(
        description="Load Pahlka implementation analysis from NDJSON into database"
    )
    parser.add_argument(
        "--in",
        dest="input_file",
        required=True,
        help="Path to input NDJSON file with Pahlka implementation analysis"
    )
    parser.add_argument(
        "--jurisdiction",
        default="dc",
        help="Jurisdiction code (default: dc)"
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=500,
        help="Batch size for inserts (default: 500)"
    )

    args = parser.parse_args()

    # Get database URL from environment
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        print("Error: DATABASE_URL environment variable not set", file=sys.stderr)
        return 1

    # Run loader
    loader = PahlkaImplementationLoader(
        database_url=database_url,
        input_file=Path(args.input_file),
        batch_size=args.batch_size,
        jurisdiction=args.jurisdiction
    )

    try:
        loader.run()
        return 0
    except Exception as e:
        print(f"Fatal error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    exit(main())
