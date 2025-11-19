import os
import psycopg2
from urllib.parse import urlparse

def get_db_url():
    with open('.env') as f:
        for line in f:
            if line.startswith('DATABASE_URL='):
                return line.strip().split('=', 1)[1]
    return None

def check_tables():
    url = get_db_url()
    if not url:
        print("DATABASE_URL not found in .env")
        return

    try:
        conn = psycopg2.connect(url)
        cur = conn.cursor()
        
        tables = ['obligations', 'similarity_classifications', 'section_similarities']
        for table in tables:
            cur.execute(f"SELECT to_regclass('public.{table}');")
            exists = cur.fetchone()[0] is not None
            print(f"Table '{table}': {'✅ Exists' if exists else '❌ Missing'}")
            
        conn.close()
    except Exception as e:
        print(f"Error connecting to DB: {e}")

if __name__ == "__main__":
    check_tables()
