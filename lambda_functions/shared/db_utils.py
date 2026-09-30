# Database connection utility for Lambda functions
# Lambda uses SYNC connections (not async like FastAPI)

import psycopg2
from psycopg2.extras import RealDictCursor
from shared.config import DATABASE_URL

# Connection pool — reused across Lambda invocations (warm starts)
_connection = None


def get_db_connection():
    """
    Get a database connection (reused for Lambda warm starts).

    WHY connection reuse:
        Lambda keeps the container alive between invocations (warm start).
        Creating a new DB connection every invocation wastes 50-100ms.
        Reusing the connection: ~1ms.
    """
    global _connection
    if _connection is None or _connection.closed:
        _connection = psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)
    return _connection


def execute_query(query: str, params: dict = None) -> list[dict]:
    """Execute a SELECT query and return rows as dicts."""
    conn = get_db_connection()
    with conn.cursor() as cur:
        cur.execute(query, params or {})
        return cur.fetchall()


def execute_update(query: str, params: dict = None) -> int:
    """Execute an INSERT/UPDATE/DELETE and return affected rows."""
    conn = get_db_connection()
    with conn.cursor() as cur:
        cur.execute(query, params or {})
        conn.commit()
        return cur.rowcount
