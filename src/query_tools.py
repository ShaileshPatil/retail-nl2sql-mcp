"""
Safe, schema-scoped query functions backing the MCP tools. Deliberately
NOT a general-purpose "run this SQL" tool: every function takes typed,
validated parameters and executes a single, hardcoded, PARAMETERIZED SQL
statement (values passed via `?` placeholders, never string-interpolated).
This is the safety property this whole project exists to demonstrate --
schema-scoped tools beat NL-to-raw-SQL generation for exactly this reason.
"""
import os
import sqlite3
from contextlib import contextmanager

from data.create_retail_db import DB_PATH, CATEGORIES

VALID_CATEGORIES = set(CATEGORIES)


class InvalidToolInput(ValueError):
    """Raised when a request falls outside the tool's allowed schema/values."""


@contextmanager
def _connect(db_path=None):
    resolved_path = db_path or DB_PATH
    if not os.path.exists(resolved_path):
        # zero-setup convenience: build the synthetic DB on first use if it
        # doesn't exist yet, rather than requiring a separate manual step.
        from data.create_retail_db import build_database
        build_database(db_path=resolved_path)
    conn = sqlite3.connect(resolved_path)
    try:
        yield conn
    finally:
        conn.close()


def _validate_category(category):
    if category is not None and category not in VALID_CATEGORIES:
        raise InvalidToolInput(f"Unknown category '{category}'. Valid categories: {sorted(VALID_CATEGORIES)}")


def _validate_store(conn, store_id):
    if store_id is None:
        return
    row = conn.execute("SELECT 1 FROM stores WHERE store_id = ?", (store_id,)).fetchone()
    if row is None:
        raise InvalidToolInput(f"Unknown store_id '{store_id}'")


def _validate_product(conn, product_id):
    row = conn.execute("SELECT 1 FROM products WHERE product_id = ?", (product_id,)).fetchone()
    if row is None:
        raise InvalidToolInput(f"Unknown product_id '{product_id}'")


def _validate_week_range(start_week, end_week):
    for w, label in [(start_week, "start_week"), (end_week, "end_week")]:
        if w is not None and (not isinstance(w, int) or w < 0 or w > 51):
            raise InvalidToolInput(f"{label} must be an integer between 0 and 51, got {w!r}")


def list_categories(db_path=None):
    return sorted(VALID_CATEGORIES)


def list_stores(db_path=None):
    with _connect(db_path) as conn:
        rows = conn.execute("SELECT store_id, city, state FROM stores ORDER BY store_id").fetchall()
    return [{"store_id": r[0], "city": r[1], "state": r[2]} for r in rows]


def get_total_sales(category=None, store_id=None, start_week=None, end_week=None, db_path=None):
    _validate_category(category)
    _validate_week_range(start_week, end_week)
    with _connect(db_path) as conn:
        _validate_store(conn, store_id)

        query = """
            SELECT COALESCE(SUM(s.units_sold), 0), COALESCE(SUM(s.revenue), 0)
            FROM sales s JOIN products p ON s.product_id = p.product_id
            WHERE 1=1
        """
        params = []
        if category is not None:
            query += " AND p.category = ?"
            params.append(category)
        if store_id is not None:
            query += " AND s.store_id = ?"
            params.append(store_id)
        if start_week is not None:
            query += " AND s.week >= ?"
            params.append(start_week)
        if end_week is not None:
            query += " AND s.week <= ?"
            params.append(end_week)

        total_units, total_revenue = conn.execute(query, params).fetchone()
    return {"total_units": int(total_units), "total_revenue": round(float(total_revenue), 2)}


def get_top_products(n=5, category=None, db_path=None):
    if not isinstance(n, int) or n <= 0 or n > 50:
        raise InvalidToolInput(f"n must be an integer between 1 and 50, got {n!r}")
    _validate_category(category)

    with _connect(db_path) as conn:
        query = """
            SELECT p.product_id, p.name, SUM(s.revenue) as total_revenue
            FROM sales s JOIN products p ON s.product_id = p.product_id
            WHERE 1=1
        """
        params = []
        if category is not None:
            query += " AND p.category = ?"
            params.append(category)
        query += " GROUP BY p.product_id, p.name ORDER BY total_revenue DESC LIMIT ?"
        params.append(n)

        rows = conn.execute(query, params).fetchall()
    return [{"product_id": r[0], "name": r[1], "total_revenue": round(float(r[2]), 2)} for r in rows]


def get_sales_trend(product_id, start_week=0, end_week=51, db_path=None):
    _validate_week_range(start_week, end_week)
    with _connect(db_path) as conn:
        _validate_product(conn, product_id)
        rows = conn.execute(
            """SELECT week, SUM(units_sold) FROM sales
               WHERE product_id = ? AND week >= ? AND week <= ?
               GROUP BY week ORDER BY week""",
            (product_id, start_week, end_week),
        ).fetchall()
    return [{"week": r[0], "units_sold": int(r[1])} for r in rows]
