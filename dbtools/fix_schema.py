#!/usr/bin/env python3
"""
Fix database schema issues:
1. Add missing reporting_text column if needed
2. Fix cross_encoder_score constraint to allow values > 1.0
"""

import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

def main():
    conn = psycopg2.connect(DATABASE_URL)
    cursor = conn.cursor()

    print("Checking database schema...")

    # Check if reporting_text column exists
    cursor.execute("""
        SELECT column_name
        FROM information_schema.columns
        WHERE table_name = 'sections' AND column_name = 'reporting_text'
    """)

    if cursor.fetchone() is None:
        print("❌ Missing reporting_text column in sections table")
        print("   Adding column...")
        cursor.execute("""
            ALTER TABLE sections
            ADD COLUMN IF NOT EXISTS reporting_text text
        """)
        conn.commit()
        print("✅ Added reporting_text column")
    else:
        print("✅ reporting_text column exists")

    # Fix cross_encoder_score constraint
    print("\nFixing cross_encoder_score constraint...")

    # Drop the old constraint
    cursor.execute("""
        ALTER TABLE section_similarity_classifications
        DROP CONSTRAINT IF EXISTS section_similarity_classifications_cross_encoder_score_check
    """)

    # Add new constraint that allows any positive value (unnormalized logits)
    cursor.execute("""
        ALTER TABLE section_similarity_classifications
        ADD CONSTRAINT section_similarity_classifications_cross_encoder_score_check
        CHECK (cross_encoder_score >= 0.0 OR cross_encoder_score IS NULL)
    """)

    conn.commit()
    print("✅ Fixed cross_encoder_score constraint (now allows values > 1.0)")

    cursor.close()
    conn.close()

    print("\n✅ Schema fixes complete!")

if __name__ == "__main__":
    main()
