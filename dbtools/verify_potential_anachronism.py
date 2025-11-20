#!/usr/bin/env python3
"""
Verify that potential_anachronism column exists and has data.
"""

import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

def main():
    print("=" * 60)
    print("Verifying potential_anachronism Column")
    print("=" * 60)
    print()

    conn = psycopg2.connect(DATABASE_URL)
    cursor = conn.cursor()

    # Check if column exists
    cursor.execute("""
        SELECT column_name, data_type, column_default
        FROM information_schema.columns
        WHERE table_schema = 'public'
        AND table_name = 'section_similarity_classifications'
        AND column_name = 'potential_anachronism'
    """)

    result = cursor.fetchone()
    if not result:
        print("❌ Column potential_anachronism does not exist!")
        cursor.close()
        conn.close()
        return

    column_name, data_type, default_value = result
    print(f"✅ Column exists: {column_name}")
    print(f"   Type: {data_type}")
    print(f"   Default: {default_value}")
    print()

    # Check how many records have potential_anachronism = true
    cursor.execute("""
        SELECT COUNT(*) as total,
               SUM(CASE WHEN potential_anachronism = true THEN 1 ELSE 0 END) as flagged
        FROM section_similarity_classifications
    """)

    total, flagged = cursor.fetchone()
    print(f"📊 Data Statistics:")
    print(f"   Total records: {total}")
    print(f"   Flagged as potential anachronism: {flagged}")
    print(f"   Percentage: {(flagged/total*100):.1f}%" if total > 0 else "   Percentage: N/A")
    print()

    # Show a few examples of flagged records
    if flagged > 0:
        cursor.execute("""
            SELECT jurisdiction, section_a, section_b, classification, explanation
            FROM section_similarity_classifications
            WHERE potential_anachronism = true
            LIMIT 3
        """)

        print("📝 Sample Flagged Records:")
        print()
        for i, row in enumerate(cursor.fetchall(), 1):
            jurisdiction, section_a, section_b, classification, explanation = row
            print(f"   {i}. {section_a} ↔ {section_b}")
            print(f"      Classification: {classification}")
            print(f"      Explanation: {explanation[:100]}...")
            print()

    cursor.close()
    conn.close()

    print("=" * 60)
    print("✅ Verification complete!")
    print("=" * 60)

if __name__ == "__main__":
    main()
