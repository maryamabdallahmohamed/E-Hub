from .db_adapter import run_query

def query_db(sql: str) -> list[dict]:
    """Run a SELECT query on the Neon DB and return rows as a list of dicts."""
    return run_query(sql, fetch=True)

def execute_db(sql: str) -> str:
    """Run an INSERT, UPDATE, or DELETE query on the Neon DB."""
    run_query(sql, fetch=False)
    return "Query executed successfully"

# def insert_article(link: str, summary: str) -> str:
#     sql = f"""
#     INSERT INTO articles (link, summary)
#     VALUES ('{link}', '{summary}')
#     ON CONFLICT (link) DO UPDATE
#     SET summary = EXCLUDED.summary;
#     """
#     execute_db(sql)
#     return f"Article saved for link: {link}"

def get_article_by_link(link: str) -> dict | None:
    sql = f"SELECT * FROM articles WHERE link = '{link}' LIMIT 1;"
    rows = query_db(sql)
    return rows[0] if rows else None

def get_latest_articles(limit: int = 5) -> list[dict]:
    sql = f"SELECT * FROM articles ORDER BY id DESC LIMIT {limit};"
    return query_db(sql)
