#!/usr/bin/env python3
"""Check classification values in database."""

import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv('DATABASE_URL')
conn = psycopg2.connect(DATABASE_URL)
cursor = conn.cursor()

cursor.execute("""
    SELECT classification, COUNT(*)
    FROM dc_section_similarity_classifications
    GROUP BY classification
    ORDER BY COUNT(*) DESC
""")

print("Current classification values:")
for row in cursor.fetchall():
    print(f"  {row[0]}: {row[1]}")

cursor.close()
conn.close()
