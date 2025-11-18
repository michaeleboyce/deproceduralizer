#!/usr/bin/env python3
"""
Verify obligations data was loaded correctly.
"""

import os
import sys
import psycopg2

def main():
    database_url = os.getenv('DATABASE_URL')
    if not database_url:
        print("Error: DATABASE_URL environment variable not set", file=sys.stderr)
        sys.exit(1)

    conn = psycopg2.connect(database_url)
    cur = conn.cursor()

    print("=" * 60)
    print("Obligations Data Verification")
    print("=" * 60)

    # Total count
    cur.execute("SELECT COUNT(*) FROM obligations")
    total = cur.fetchone()[0]
    print(f"\nTotal obligations: {total}")

    # Count by category
    print("\nObligations by category:")
    cur.execute("""
        SELECT category, COUNT(*) as count
        FROM obligations
        GROUP BY category
        ORDER BY count DESC
    """)
    for row in cur.fetchall():
        print(f"  {row[0]:15} {row[1]:5}")

    # Count by jurisdiction
    print("\nObligations by jurisdiction:")
    cur.execute("""
        SELECT jurisdiction, COUNT(*) as count
        FROM obligations
        GROUP BY jurisdiction
        ORDER BY count DESC
    """)
    for row in cur.fetchall():
        print(f"  {row[0]:15} {row[1]:5}")

    # Sample records
    print("\nSample obligations:")
    cur.execute("""
        SELECT category, phrase, value, unit
        FROM obligations
        LIMIT 5
    """)
    for row in cur.fetchall():
        category, phrase, value, unit = row
        value_str = f"{value} {unit}" if value and unit else "N/A"
        print(f"  [{category}] {phrase[:60]}... = {value_str}")

    # Verify foreign key relationships
    print("\nForeign key integrity check:")
    cur.execute("""
        SELECT COUNT(*)
        FROM obligations o
        LEFT JOIN sections s ON (o.jurisdiction = s.jurisdiction AND o.section_id = s.id)
        WHERE s.id IS NULL
    """)
    orphans = cur.fetchone()[0]
    if orphans == 0:
        print("  ✓ All obligations reference valid sections")
    else:
        print(f"  ✗ Found {orphans} orphaned obligations")

    cur.close()
    conn.close()

    print("\n" + "=" * 60)
    print("✓ Verification Complete")
    print("=" * 60)

if __name__ == '__main__':
    main()
