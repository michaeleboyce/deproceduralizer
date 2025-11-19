#!/usr/bin/env python3
"""
Drop anachronisms tables from the database.

This script drops the three anachronisms tables in the correct order
to handle foreign key constraints.
"""

import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

def main():
    print("=" * 60)
    print("Dropping Anachronisms Tables")
    print("=" * 60)
    print()

    conn = psycopg2.connect(DATABASE_URL)
    cursor = conn.cursor()

    # Drop tables in reverse order (respecting foreign key constraints)
    tables = [
        'section_anachronism_highlights',
        'anachronism_indicators',
        'section_anachronisms'
    ]

    for table in tables:
        print(f"📝 Dropping {table} table...")
        cursor.execute(f"DROP TABLE IF EXISTS {table} CASCADE")
        conn.commit()
        print(f"✅ Dropped {table} table")

    cursor.close()
    conn.close()

    print()
    print("=" * 60)
    print("✅ Anachronisms tables dropped successfully!")
    print("=" * 60)
    print()
    print("Now run: python dbtools/add_anachronisms_tables.py")

if __name__ == "__main__":
    main()
