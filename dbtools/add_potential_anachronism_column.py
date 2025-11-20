#!/usr/bin/env python3
"""
Add potential_anachronism column to section_similarity_classifications table.

This migration adds the boolean column for tracking anachronism flags from
similarity classification analysis.
"""

import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

def main():
    print("=" * 60)
    print("Adding potential_anachronism Column")
    print("=" * 60)
    print()

    conn = psycopg2.connect(DATABASE_URL)
    cursor = conn.cursor()

    # Check if column exists
    cursor.execute("""
        SELECT column_name
        FROM information_schema.columns
        WHERE table_schema = 'public'
        AND table_name = 'section_similarity_classifications'
        AND column_name = 'potential_anachronism'
    """)

    if cursor.fetchone():
        print("✅ potential_anachronism column already exists")
        cursor.close()
        conn.close()
        return

    print("📝 Adding potential_anachronism column to section_similarity_classifications...")
    cursor.execute("""
        ALTER TABLE section_similarity_classifications
        ADD COLUMN potential_anachronism boolean DEFAULT false
    """)
    conn.commit()
    print("✅ Column added successfully")

    cursor.close()
    conn.close()

    print()
    print("=" * 60)
    print("✅ Migration complete!")
    print("=" * 60)
    print()
    print("Now reload similarity classifications with:")
    print("  ./scripts/load-database.sh --corpus=<your_corpus> --tables=similarity_classifications")

if __name__ == "__main__":
    main()
