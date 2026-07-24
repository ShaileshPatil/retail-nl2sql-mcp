"""
A real MCP (Model Context Protocol) server exposing SAFE, schema-scoped
retail-analytics tools -- built with the official `mcp` Python SDK's
FastMCP high-level API.

Deliberately does NOT expose a "run arbitrary SQL" tool. Every tool here
is a specific, typed, validated operation over `src/query_tools.py`. This
is the safety argument this whole project makes: letting an LLM call a
small set of well-defined tools is far safer and more auditable than
letting it generate and execute free-form SQL against a production
database.

Run standalone with:  python -m mcp_server.server
(or via any MCP-compatible client/inspector using stdio transport)
"""
from mcp.server.fastmcp import FastMCP

from src.query_tools import (
    list_categories, list_stores, get_total_sales, get_top_products,
    get_sales_trend, InvalidToolInput,
)

mcp = FastMCP("retail-analytics")


@mcp.tool()
def list_categories_tool() -> list:
    """List all valid product categories in the retail dataset."""
    return list_categories()


@mcp.tool()
def list_stores_tool() -> list:
    """List all stores (store_id, city, state) in the retail dataset."""
    return list_stores()


@mcp.tool()
def get_total_sales_tool(category: str = None, store_id: str = None,
                           start_week: int = None, end_week: int = None) -> dict:
    """Get total units sold and revenue, optionally filtered by category,
    store, and/or a week range (weeks 0-51). Raises a clear error if an
    unknown category or store_id is given -- never falls back to
    executing arbitrary SQL."""
    try:
        return get_total_sales(category=category, store_id=store_id, start_week=start_week, end_week=end_week)
    except InvalidToolInput as e:
        return {"error": str(e)}


@mcp.tool()
def get_top_products_tool(n: int = 5, category: str = None) -> list:
    """Get the top N products by total revenue, optionally filtered by category."""
    try:
        return get_top_products(n=n, category=category)
    except InvalidToolInput as e:
        return {"error": str(e)}


@mcp.tool()
def get_sales_trend_tool(product_id: str, start_week: int = 0, end_week: int = 51) -> list:
    """Get the weekly units-sold trend for a specific product_id."""
    try:
        return get_sales_trend(product_id, start_week=start_week, end_week=end_week)
    except InvalidToolInput as e:
        return {"error": str(e)}


if __name__ == "__main__":
    mcp.run()
