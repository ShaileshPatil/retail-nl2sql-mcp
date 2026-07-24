"""
Builds a small synthetic SQLite retail database: stores, products, and
weekly sales. Used as the backing data for schema-scoped MCP tools --
never queried via free-form/user-constructed SQL.

Fully synthetic. No real Walmart or retail data is used anywhere.
"""
import os
import random
import sqlite3

CATEGORIES = ["grocery", "electronics", "apparel", "home", "sporting_goods"]
STATES = ["AR", "TX", "CA", "NY", "OH"]
N_STORES = 8
N_PRODUCTS_PER_CATEGORY = 6
N_WEEKS = 52

DB_PATH = os.path.join(os.path.dirname(__file__), "retail.db")


def build_database(db_path=None, seed=7):
    db_path = db_path or DB_PATH
    if os.path.exists(db_path):
        os.remove(db_path)

    rng = random.Random(seed)
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    cur.execute("""CREATE TABLE stores (
        store_id TEXT PRIMARY KEY, city TEXT, state TEXT
    )""")
    cur.execute("""CREATE TABLE products (
        product_id TEXT PRIMARY KEY, name TEXT, category TEXT, price REAL
    )""")
    cur.execute("""CREATE TABLE sales (
        sale_id INTEGER PRIMARY KEY AUTOINCREMENT,
        store_id TEXT, product_id TEXT, week INTEGER, units_sold INTEGER, revenue REAL,
        FOREIGN KEY(store_id) REFERENCES stores(store_id),
        FOREIGN KEY(product_id) REFERENCES products(product_id)
    )""")

    stores = []
    for i in range(N_STORES):
        store_id = f"ST{i:03d}"
        city = f"City{i}"
        state = rng.choice(STATES)
        stores.append((store_id, city, state))
    cur.executemany("INSERT INTO stores VALUES (?, ?, ?)", stores)

    products = []
    for category in CATEGORIES:
        for i in range(N_PRODUCTS_PER_CATEGORY):
            product_id = f"{category[:3].upper()}{i:03d}"
            name = f"{category.title()} Item {i}"
            price = round(rng.uniform(5, 200), 2)
            products.append((product_id, name, category, price))
    cur.executemany("INSERT INTO products VALUES (?, ?, ?, ?)", products)

    sales_rows = []
    for store_id, _, _ in stores:
        for product_id, _, _, price in products:
            base_units = rng.randint(5, 60)
            for week in range(N_WEEKS):
                units = max(0, int(rng.gauss(base_units, base_units * 0.25)))
                revenue = round(units * price, 2)
                sales_rows.append((store_id, product_id, week, units, revenue))
    cur.executemany("INSERT INTO sales (store_id, product_id, week, units_sold, revenue) VALUES (?, ?, ?, ?, ?)", sales_rows)

    conn.commit()
    conn.close()
    return db_path


if __name__ == "__main__":
    path = build_database()
    print(f"Database built at {path}")
