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

    # Sample records by category
    print("\nSample obligations by category:")
    cur.execute("""
        SELECT DISTINCT ON (category) category, phrase, value, unit
        FROM obligations
        ORDER BY category, RANDOM()
    """)
    for row in cur.fetchall():
        category, phrase, value, unit = row
        value_str = f"{value} {unit}" if value and unit else "N/A"
        phrase_display = phrase[:50] + "..." if len(phrase) > 50 else phrase
        print(f"  [{category:12}] {phrase_display:55} = {value_str}")

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

    # Data quality checks
    print("\nData quality checks:")

    # Check for obligations with value but no unit
    cur.execute("""
        SELECT COUNT(*)
        FROM obligations
        WHERE value IS NOT NULL AND (unit IS NULL OR unit = '')
    """)
    missing_units = cur.fetchone()[0]
    if missing_units == 0:
        print("  ✓ All obligations with values have units")
    else:
        print(f"  ⚠ Found {missing_units} obligations with values but no units")

    # Check for very short phrases (likely errors)
    cur.execute("""
        SELECT COUNT(*)
        FROM obligations
        WHERE LENGTH(phrase) < 5
    """)
    short_phrases = cur.fetchone()[0]
    if short_phrases == 0:
        print("  ✓ No suspiciously short phrases")
    else:
        print(f"  ⚠ Found {short_phrases} obligations with phrases < 5 characters")

    # Check for very long phrases (might indicate extraction issues)
    cur.execute("""
        SELECT COUNT(*)
        FROM obligations
        WHERE LENGTH(phrase) > 200
    """)
    long_phrases = cur.fetchone()[0]
    if long_phrases == 0:
        print("  ✓ No suspiciously long phrases")
    else:
        print(f"  ⚠ Found {long_phrases} obligations with phrases > 200 characters")

    # Check distribution of values by category
    print("\nValue statistics by category:")
    cur.execute("""
        SELECT
            category,
            COUNT(*) as total,
            COUNT(value) as with_values,
            ROUND(100.0 * COUNT(value) / COUNT(*), 1) as pct_with_values,
            ROUND(AVG(value), 2) as avg_value,
            MIN(value) as min_value,
            MAX(value) as max_value
        FROM obligations
        GROUP BY category
        ORDER BY category
    """)
    for row in cur.fetchall():
        category, total, with_values, pct, avg_val, min_val, max_val = row
        print(f"  {category:12} Total: {total:5} | With values: {with_values:5} ({pct:4.1f}%) | Avg: {avg_val or 'N/A'} | Range: {min_val or 'N/A'}-{max_val or 'N/A'}")

    # Check most common units by category
    print("\nMost common units by category:")
    cur.execute("""
        SELECT category, unit, COUNT(*) as count
        FROM (
            SELECT category, unit,
                   ROW_NUMBER() OVER (PARTITION BY category ORDER BY COUNT(*) DESC) as rn
            FROM obligations
            WHERE unit IS NOT NULL
            GROUP BY category, unit
        ) ranked
        WHERE rn <= 3
        ORDER BY category, count DESC
    """)
    current_category = None
    for row in cur.fetchall():
        category, unit, count = row
        if category != current_category:
            print(f"  {category}:")
            current_category = category
        print(f"    - {unit}: {count}")

    # Check sections with most obligations
    print("\nTop 10 sections with most obligations:")
    cur.execute("""
        SELECT o.section_id, s.citation, s.heading, COUNT(*) as count
        FROM obligations o
        JOIN sections s ON (o.jurisdiction = s.jurisdiction AND o.section_id = s.id)
        GROUP BY o.section_id, s.citation, s.heading
        ORDER BY count DESC
        LIMIT 10
    """)
    for i, row in enumerate(cur.fetchall(), 1):
        section_id, citation, heading, count = row
        heading_short = heading[:40] + "..." if len(heading) > 40 else heading
        print(f"  {i:2}. {citation:15} {heading_short:45} ({count} obligations)")

    cur.close()
    conn.close()

    print("\n" + "=" * 60)
    print("✓ Verification Complete")
    print("=" * 60)

if __name__ == '__main__':
    main()
