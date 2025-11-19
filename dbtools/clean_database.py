#!/usr/bin/env python3
"""
Clean all data from database tables (but keep the schema).
Useful when switching between different corpus sizes.
"""

import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

# Tables to clean (in order to avoid FK constraint violations)
TABLES = [
    "section_similarity_classifications",
    "section_reporting",
    "section_refs",
    "section_similarities",
    "dc_section_highlights",
    "dc_section_tags",
    "dc_global_tags",
    "dc_section_amounts",
    "dc_section_deadlines",
    "dc_section_refs",
    "structure",
    "sections",
    "dc_sections",
]

def main():
    print("⚠️  WARNING: This will delete ALL data from database tables!")
    print("Schema will be preserved, but all records will be removed.\n")

    response = input("Are you sure you want to continue? (type 'yes' to confirm): ")
    if response.lower() != 'yes':
        print("Aborted.")
        return

    conn = psycopg2.connect(DATABASE_URL)
    cursor = conn.cursor()

    print("\nCleaning database tables...")

    for table in TABLES:
        try:
            cursor.execute(f"TRUNCATE TABLE {table} CASCADE")
            cursor.execute(f"SELECT COUNT(*) FROM {table}")
            count = cursor.fetchone()[0]
            print(f"✓ Cleaned {table} (verified: {count} rows)")
        except psycopg2.errors.UndefinedTable:
            print(f"⊘ Skipped {table} (table does not exist)")
            conn.rollback()
        except Exception as e:
            print(f"✗ Error cleaning {table}: {e}")
            conn.rollback()

    conn.commit()
    cursor.close()
    conn.close()

    print("\n✅ Database cleaned!")
    print("You can now load a different corpus without data mixing.")

if __name__ == "__main__":
    main()
