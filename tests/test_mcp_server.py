import asyncio
from mcp_server.server import mcp


def test_mcp_server_has_expected_tools_registered():
    async def get_tools():
        return await mcp.list_tools()

    tools = asyncio.run(get_tools())
    tool_names = {t.name for t in tools}
    assert tool_names == {
        "list_categories_tool", "list_stores_tool", "get_total_sales_tool",
        "get_top_products_tool", "get_sales_trend_tool",
    }


def test_mcp_server_tools_have_descriptions():
    async def get_tools():
        return await mcp.list_tools()

    tools = asyncio.run(get_tools())
    for t in tools:
        assert t.description and len(t.description) > 10


def test_mcp_server_name():
    assert mcp.name == "retail-analytics"
