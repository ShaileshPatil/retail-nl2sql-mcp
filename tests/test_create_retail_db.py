import sqlite3
from data.create_retail_db import build_database, CATEGORIES, N_STORES


def test_build_database_creates_expected_tables(tmp_path):
    db_path = str(tmp_path / "test.db")
    build_database(db_path=db_path, seed=1)
    conn = sqlite3.connect(db_path)
    tables = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    assert {"stores", "products", "sales"}.issubset(tables)
    conn.close()


def test_build_database_row_counts(tmp_path):
    db_path = str(tmp_path / "test.db")
    build_database(db_path=db_path, seed=1)
    conn = sqlite3.connect(db_path)
    n_stores = conn.execute("SELECT COUNT(*) FROM stores").fetchone()[0]
    n_products = conn.execute("SELECT COUNT(*) FROM products").fetchone()[0]
    n_sales = conn.execute("SELECT COUNT(*) FROM sales").fetchone()[0]
    conn.close()
    assert n_stores == N_STORES
    assert n_products == len(CATEGORIES) * 6
    assert n_sales == n_stores * n_products * 52


def test_build_database_deterministic_given_seed(tmp_path):
    db_path1 = str(tmp_path / "a.db")
    db_path2 = str(tmp_path / "b.db")
    build_database(db_path=db_path1, seed=42)
    build_database(db_path=db_path2, seed=42)
    conn1, conn2 = sqlite3.connect(db_path1), sqlite3.connect(db_path2)
    rows1 = conn1.execute("SELECT * FROM sales ORDER BY sale_id LIMIT 20").fetchall()
    rows2 = conn2.execute("SELECT * FROM sales ORDER BY sale_id LIMIT 20").fetchall()
    conn1.close(); conn2.close()
    assert rows1 == rows2
