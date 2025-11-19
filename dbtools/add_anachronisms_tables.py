#!/usr/bin/env python3
"""
Add anachronisms tables to the database.

This script creates the three anachronisms tables if they don't exist:
- section_anachronisms (main table)
- anachronism_indicators (detailed indicators)
- section_anachronism_highlights (matched phrases)
"""

import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

def main():
    print("=" * 60)
    print("Adding Anachronisms Tables")
    print("=" * 60)
    print()

    conn = psycopg2.connect(DATABASE_URL)
    cursor = conn.cursor()

    # Check if tables exist
    cursor.execute("""
        SELECT table_name
        FROM information_schema.tables
        WHERE table_schema = 'public'
        AND table_name IN ('section_anachronisms', 'anachronism_indicators', 'section_anachronism_highlights')
    """)
    existing_tables = [row[0] for row in cursor.fetchall()]

    if 'section_anachronisms' in existing_tables:
        print("✅ section_anachronisms table already exists")
    else:
        print("📝 Creating section_anachronisms table...")
        cursor.execute("""
            CREATE TABLE section_anachronisms (
              jurisdiction text NOT NULL,
              section_id text NOT NULL,
              has_anachronism boolean NOT NULL DEFAULT false,
              overall_severity text CHECK (overall_severity IN ('CRITICAL', 'HIGH', 'MEDIUM', 'LOW')),
              summary text,
              requires_immediate_review boolean NOT NULL DEFAULT false,
              model_used text,
              analyzed_at timestamp with time zone NOT NULL,
              created_at timestamp with time zone DEFAULT now(),
              PRIMARY KEY (jurisdiction, section_id),
              FOREIGN KEY (jurisdiction, section_id) REFERENCES sections(jurisdiction, id) ON DELETE CASCADE
            );
        """)
        conn.commit()
        print("✅ Created section_anachronisms table")

    if 'anachronism_indicators' in existing_tables:
        print("✅ anachronism_indicators table already exists")
    else:
        print("📝 Creating anachronism_indicators table...")
        cursor.execute("""
            CREATE TABLE anachronism_indicators (
              id bigserial PRIMARY KEY,
              jurisdiction text NOT NULL,
              section_id text NOT NULL,
              category text NOT NULL,
              severity text NOT NULL CHECK (severity IN ('CRITICAL', 'HIGH', 'MEDIUM', 'LOW')),
              modern_equivalent text,
              recommendation text NOT NULL,
              explanation text NOT NULL,
              FOREIGN KEY (jurisdiction, section_id) REFERENCES section_anachronisms(jurisdiction, section_id) ON DELETE CASCADE
            );
        """)
        conn.commit()
        print("✅ Created anachronism_indicators table")

    if 'section_anachronism_highlights' in existing_tables:
        print("✅ section_anachronism_highlights table already exists")
    else:
        print("📝 Creating section_anachronism_highlights table...")
        cursor.execute("""
            CREATE TABLE section_anachronism_highlights (
              id bigserial PRIMARY KEY,
              indicator_id bigint NOT NULL REFERENCES anachronism_indicators(id) ON DELETE CASCADE,
              matched_phrase text NOT NULL,
              UNIQUE (indicator_id, matched_phrase)
            );
        """)
        conn.commit()
        print("✅ Created section_anachronism_highlights table")

    # Create indexes
    print("\n📝 Creating indexes...")

    indexes = [
        ("section_anachronisms_severity_idx",
         "CREATE INDEX IF NOT EXISTS section_anachronisms_severity_idx ON section_anachronisms (jurisdiction, overall_severity) WHERE has_anachronism = true"),

        ("section_anachronisms_immediate_review_idx",
         "CREATE INDEX IF NOT EXISTS section_anachronisms_immediate_review_idx ON section_anachronisms (jurisdiction, requires_immediate_review) WHERE requires_immediate_review = true"),

        ("anachronism_indicators_section_idx",
         "CREATE INDEX IF NOT EXISTS anachronism_indicators_section_idx ON anachronism_indicators (jurisdiction, section_id)"),

        ("anachronism_indicators_category_idx",
         "CREATE INDEX IF NOT EXISTS anachronism_indicators_category_idx ON anachronism_indicators (category)"),

        ("anachronism_indicators_severity_idx",
         "CREATE INDEX IF NOT EXISTS anachronism_indicators_severity_idx ON anachronism_indicators (severity)"),

        ("anachronism_highlights_indicator_idx",
         "CREATE INDEX IF NOT EXISTS anachronism_highlights_indicator_idx ON section_anachronism_highlights (indicator_id)")
    ]

    for index_name, sql in indexes:
        cursor.execute(sql)
        print(f"✅ Created index: {index_name}")

    conn.commit()

    cursor.close()
    conn.close()

    print()
    print("=" * 60)
    print("✅ Anachronisms tables created successfully!")
    print("=" * 60)
    print()
    print("You can now load anachronisms data with:")
    print("  ./scripts/load-database.sh --corpus=small --tables=anachronisms")

if __name__ == "__main__":
    main()
