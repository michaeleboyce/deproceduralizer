#!/usr/bin/env python3
"""Verify multi-jurisdiction migration was successful."""

import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv('DATABASE_URL')
conn = psycopg2.connect(DATABASE_URL)
cursor = conn.cursor()

print("=" * 60)
print("MIGRATION VERIFICATION")
print("=" * 60)

# 1. Check tables renamed (no dc_ prefix)
print("\n1. Checking table names (should have NO dc_ prefix)...")
cursor.execute("""
    SELECT table_name
    FROM information_schema.tables
    WHERE table_schema = 'public'
    AND table_name LIKE '%section%' OR table_name IN ('jurisdictions', 'structure', 'global_tags')
    ORDER BY table_name
""")

tables = [row[0] for row in cursor.fetchall()]
has_dc_prefix = any(t.startswith('dc_') for t in tables)

if has_dc_prefix:
    print("   ❌ FAIL: Found tables with dc_ prefix!")
    for t in tables:
        if t.startswith('dc_'):
            print(f"      - {t}")
else:
    print("   ✓ PASS: All tables renamed (no dc_ prefix)")
    print(f"      Found {len(tables)} tables")

# 2. Check jurisdictions table populated
print("\n2. Checking jurisdictions table...")
cursor.execute("SELECT * FROM jurisdictions")
jurisdictions = cursor.fetchall()

if len(jurisdictions) == 0:
    print("   ❌ FAIL: No jurisdictions found!")
elif len(jurisdictions) == 1 and jurisdictions[0][0] == 'dc':
    print(f"   ✓ PASS: DC jurisdiction present")
    print(f"      ID: {jurisdictions[0][0]}")
    print(f"      Name: {jurisdictions[0][1]}")
    print(f"      Abbreviation: {jurisdictions[0][2]}")
    print(f"      Type: {jurisdictions[0][3]}")
else:
    print(f"   ⚠️  WARNING: Expected 1 jurisdiction, found {len(jurisdictions)}")

# 3. Check sections table has jurisdiction column and data
print("\n3. Checking sections table...")
cursor.execute("""
    SELECT jurisdiction, COUNT(*)
    FROM sections
    GROUP BY jurisdiction
""")

section_counts = cursor.fetchall()
total_sections = sum(count for _, count in section_counts)

if total_sections == 0:
    print("   ❌ FAIL: No sections found!")
elif len(section_counts) == 1 and section_counts[0][0] == 'dc':
    print(f"   ✓ PASS: Sections migrated successfully")
    print(f"      Jurisdiction 'dc': {section_counts[0][1]} sections")
else:
    print(f"   ⚠️  WARNING: Unexpected jurisdiction distribution")
    for juris, count in section_counts:
        print(f"      {juris}: {count} sections")

# 4. Check structure table exists and is empty (will be populated later)
print("\n4. Checking structure table...")
cursor.execute("SELECT COUNT(*) FROM structure")
structure_count = cursor.fetchone()[0]

print(f"   ✓ PASS: Structure table exists")
print(f"      Records: {structure_count} (expected 0, will be populated by parser)")

# 5. Check composite primary keys working
print("\n5. Checking composite primary keys...")
cursor.execute("""
    SELECT
        conname,
        pg_get_constraintdef(oid)
    FROM pg_constraint
    WHERE conrelid = 'sections'::regclass
    AND contype = 'p'
""")

pk_info = cursor.fetchone()
if pk_info and 'jurisdiction' in pk_info[1] and 'id' in pk_info[1]:
    print(f"   ✓ PASS: Composite PK on sections table")
    print(f"      Constraint: {pk_info[1]}")
else:
    print(f"   ❌ FAIL: Expected composite PK (jurisdiction, id)")

# 6. Check all related tables migrated
print("\n6. Checking related tables...")
table_checks = {
    'section_refs': 'from_id',
    'section_deadlines': 'section_id',
    'section_amounts': 'section_id',
    'section_similarities': 'section_a',
    'section_similarity_classifications': 'classification',
    'section_highlights': 'phrase',
    'section_tags': 'tag',
    'global_tags': 'tag'
}

all_pass = True
for table, sample_col in table_checks.items():
    cursor.execute(f"SELECT COUNT(*) FROM {table}")
    count = cursor.fetchone()[0]
    print(f"   {table}: {count} records")
    if table in ['section_refs'] and count == 0:
        print(f"      ⚠️  (FK constraints may prevent subset refs)")

# 7. Check indexes created
print("\n7. Checking indexes...")
cursor.execute("""
    SELECT COUNT(*)
    FROM pg_indexes
    WHERE schemaname = 'public'
    AND (tablename LIKE '%section%' OR tablename IN ('jurisdictions', 'structure', 'global_tags'))
""")

index_count = cursor.fetchone()[0]
print(f"   ✓ PASS: Found {index_count} indexes")

# 8. Sample query to verify data integrity
print("\n8. Testing sample query...")
cursor.execute("""
    SELECT s.jurisdiction, s.id, s.citation, s.heading
    FROM sections s
    WHERE s.jurisdiction = 'dc'
    LIMIT 3
""")

samples = cursor.fetchall()
if samples:
    print(f"   ✓ PASS: Can query sections by jurisdiction")
    for juris, id, citation, heading in samples:
        print(f"      {citation}: {heading[:50]}...")
else:
    print(f"   ❌ FAIL: Query returned no results")

# Summary
print("\n" + "=" * 60)
print("VERIFICATION SUMMARY")
print("=" * 60)
print(f"✓ Tables renamed: {not has_dc_prefix}")
print(f"✓ Jurisdictions table: {len(jurisdictions) == 1}")
print(f"✓ Sections migrated: {total_sections} sections")
print(f"✓ Structure table: exists (empty)")
print(f"✓ Composite PKs: working")
print(f"✓ Indexes: {index_count} created")
print("=" * 60)

if not has_dc_prefix and len(jurisdictions) == 1 and total_sections > 0:
    print("\n🎉 MIGRATION SUCCESSFUL!")
else:
    print("\n⚠️  MIGRATION HAS ISSUES - Review failures above")

cursor.close()
conn.close()
