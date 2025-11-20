#!/usr/bin/env python3
"""
Load anachronism analysis results from NDJSON into the database.

Supports multi-jurisdiction schema and uses BaseLoader for DRY principles.

Features:
- Multi-table operations (3 tables: section_anachronisms, anachronism_indicators, section_anachronism_highlights)
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


class AnachronismsLoader(BaseLoader):
    """Loads anachronism analysis from NDJSON to database (3 tables) with resume capability."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Custom statistics for this multi-table loader
        self.anachronisms_inserted = 0
        self.indicators_inserted = 0
        self.highlights_inserted = 0

    def validate_record(self, record):
        """Validate an anachronism record has required fields."""
        required = [
            'section_id',
            'has_anachronism',
            'indicators',
            'summary',
            'requires_immediate_review',
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
            # 1. Insert into section_anachronisms
            self._insert_anachronisms(cursor, batch)

            # 2. Insert indicators (and get their IDs)
            indicator_ids = self._insert_indicators(cursor, batch)

            # 3. Insert highlight phrases
            self._insert_highlights(cursor, batch, indicator_ids)

        except Exception as e:
            # Don't increment error_count here - BaseLoader will handle it
            print(f"Error processing batch: {e}", file=sys.stderr)
            raise

    def _insert_anachronisms(self, cursor, batch: List[Dict[str, Any]]):
        """Insert main anachronism analysis records."""
        # Prepare data
        data = []
        for record in batch:
            data.append({
                'jurisdiction': self.jurisdiction,
                'section_id': record['section_id'],
                'has_anachronism': record['has_anachronism'],
                'overall_severity': record.get('overall_severity'),
                'summary': record.get('summary', ''),
                'requires_immediate_review': record['requires_immediate_review'],
                'model_used': record['model_used'],
                'analyzed_at': record['analyzed_at']
            })

        # SQL for inserting/updating anachronisms
        sql = """
            INSERT INTO section_anachronisms (
                jurisdiction, section_id, has_anachronism, overall_severity,
                summary, requires_immediate_review, model_used, analyzed_at
            )
            VALUES (
                %(jurisdiction)s, %(section_id)s, %(has_anachronism)s, %(overall_severity)s,
                %(summary)s, %(requires_immediate_review)s, %(model_used)s, %(analyzed_at)s
            )
            ON CONFLICT (jurisdiction, section_id) DO UPDATE SET
                has_anachronism = EXCLUDED.has_anachronism,
                overall_severity = EXCLUDED.overall_severity,
                summary = EXCLUDED.summary,
                requires_immediate_review = EXCLUDED.requires_immediate_review,
                model_used = EXCLUDED.model_used,
                analyzed_at = EXCLUDED.analyzed_at
        """

        execute_batch(cursor, sql, data)
        self.anachronisms_inserted += len(batch)

    def _insert_indicators(self, cursor, batch: List[Dict[str, Any]]) -> Dict[str, List[int]]:
        """
        Insert anachronism indicators and return mapping of section_id -> indicator IDs.

        Returns:
            Dict mapping section_id to list of indicator IDs (in order)
        """
        # First, delete existing indicators for these sections (to avoid duplicates on re-run)
        section_ids = [record['section_id'] for record in batch]
        if section_ids:
            cursor.execute(
                """
                DELETE FROM anachronism_indicators
                WHERE jurisdiction = %s AND section_id = ANY(%s)
                """,
                (self.jurisdiction, section_ids)
            )

        # Prepare indicator data with section_id tracking
        indicator_data = []
        section_indicator_counts = {}

        for record in batch:
            section_id = record['section_id']
            indicators = record.get('indicators', [])
            section_indicator_counts[section_id] = len(indicators)

            for indicator in indicators:
                indicator_data.append({
                    'jurisdiction': self.jurisdiction,
                    'section_id': section_id,
                    'category': indicator['category'],
                    'severity': indicator['severity'],
                    'modern_equivalent': indicator.get('modern_equivalent'),
                    'recommendation': indicator['recommendation'],
                    'explanation': indicator['explanation']
                })

        if not indicator_data:
            return {}

        # SQL for inserting indicators (returns ID for highlights)
        sql = """
            INSERT INTO anachronism_indicators (
                jurisdiction, section_id, category, severity,
                modern_equivalent, recommendation, explanation
            )
            VALUES (
                %(jurisdiction)s, %(section_id)s, %(category)s, %(severity)s,
                %(modern_equivalent)s, %(recommendation)s, %(explanation)s
            )
            RETURNING id, section_id
        """

        # Execute and collect IDs (must use loop for RETURNING clause)
        indicator_ids = {}
        for data in indicator_data:
            cursor.execute(sql, data)
            result = cursor.fetchone()
            if result:
                indicator_id, section_id = result
                if section_id not in indicator_ids:
                    indicator_ids[section_id] = []
                indicator_ids[section_id].append(indicator_id)

        self.indicators_inserted += len(indicator_data)

        return indicator_ids

    def _insert_highlights(
        self,
        cursor,
        batch: List[Dict[str, Any]],
        indicator_ids: Dict[str, List[int]]
    ):
        """Insert highlight phrases for each indicator."""
        highlight_data = []

        for record in batch:
            section_id = record['section_id']
            indicators = record.get('indicators', [])
            section_indicator_ids = indicator_ids.get(section_id, [])

            # Match indicators to their IDs (should be in same order)
            for i, indicator in enumerate(indicators):
                if i >= len(section_indicator_ids):
                    print(f"Warning: Missing indicator ID for {section_id} indicator {i}", file=sys.stderr)
                    continue

                indicator_id = section_indicator_ids[i]
                matched_phrases = indicator.get('matched_phrases', [])

                for phrase in matched_phrases:
                    highlight_data.append({
                        'indicator_id': indicator_id,
                        'matched_phrase': phrase
                    })

        if not highlight_data:
            return

        # SQL for inserting highlights
        sql = """
            INSERT INTO section_anachronism_highlights (indicator_id, matched_phrase)
            VALUES (%(indicator_id)s, %(matched_phrase)s)
        """

        execute_batch(cursor, sql, highlight_data)
        self.highlights_inserted += len(highlight_data)

    def print_summary(self):
        """Print custom summary for anachronisms loader."""
        super().print_summary()
        print(f"\n📊 Anachronism Loading Statistics:")
        print(f"  • Anachronism records inserted: {self.anachronisms_inserted}")
        print(f"  • Indicators inserted: {self.indicators_inserted}")
        print(f"  • Highlight phrases inserted: {self.highlights_inserted}")


def main():
    parser = argparse.ArgumentParser(
        description="Load anachronism analysis from NDJSON to database"
    )
    parser.add_argument(
        "--input",
        required=True,
        help="Input NDJSON file (anachronisms)"
    )
    parser.add_argument(
        "--jurisdiction",
        default="dc",
        help="Jurisdiction code (default: dc)"
    )
    parser.add_argument(
        "--state-file",
        type=Path,
        help="Path to state file (default: input_file.state)"
    )

    args = parser.parse_args()

    # Get database URL from environment
    database_url = os.getenv('DATABASE_URL')
    if not database_url:
        print("Error: DATABASE_URL environment variable not set", file=sys.stderr)
        return 1

    input_file = Path(args.input)
    if not input_file.exists():
        print(f"Error: Input file not found: {input_file}", file=sys.stderr)
        return 1

    # Initialize and run loader
    loader = AnachronismsLoader(
        database_url=database_url,
        input_file=str(input_file),
        jurisdiction=args.jurisdiction,
        state_file=args.state_file  # Uses input_file.state by default (corpus-specific)
    )

    loader.run()

    return 0


if __name__ == "__main__":
    exit(main())
