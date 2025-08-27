import os
import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")


def get_connection():
    return psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)

def run_query(sql: str, fetch: bool = False):
    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute(sql)
        result = cur.fetchall() if fetch else None
        conn.commit()
        return result
    finally:
        cur.close()
        conn.close()
