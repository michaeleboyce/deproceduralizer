#!/usr/bin/env python3
"""Execute SQL migration script against database."""

import os
import sys
from pathlib import Path

import psycopg2
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

DATABASE_URL = os.getenv('DATABASE_URL')
if not DATABASE_URL:
    print("Error: DATABASE_URL not found in environment", file=sys.stderr)
    sys.exit(1)

# Get migration file from command line
if len(sys.argv) != 2:
    print("Usage: python run_migration.py <migration_file.sql>", file=sys.stderr)
    sys.exit(1)

migration_file = Path(sys.argv[1])
if not migration_file.exists():
    print(f"Error: Migration file not found: {migration_file}", file=sys.stderr)
    sys.exit(1)

print(f"Reading migration: {migration_file}")
with open(migration_file, 'r') as f:
    sql = f.read()

print(f"Connecting to database...")
conn = psycopg2.connect(DATABASE_URL)
conn.autocommit = True  # Don't need transaction wrapper since SQL has BEGIN/COMMIT
cursor = conn.cursor()

try:
    print(f"Executing migration...")
    cursor.execute(sql)

    print(f"\n✓ Migration executed successfully!")

except Exception as e:
    print(f"\n✗ Migration failed: {e}", file=sys.stderr)
    sys.exit(1)
finally:
    cursor.close()
    conn.close()
