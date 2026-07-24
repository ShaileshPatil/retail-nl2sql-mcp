"""
Natural-language-to-tool-call router: maps a plain-English question to ONE
of the schema-scoped tools in `src/query_tools.py` (never to raw SQL), then
narrates the result. This is the "safe NL2SQL" pattern this project
demonstrates -- the LLM's job is to pick a tool and fill in validated
parameters, never to generate a query string itself.

Same honest-fallback discipline as this author's other projects: without
an API key, a deterministic keyword/regex-based router handles a
constrained (but real, correctly-functioning) subset of questions instead
of failing.
"""
import json
import os
import re

from src.query_tools import (
    list_categories, list_stores, get_total_sales, get_top_products,
    get_sales_trend, InvalidToolInput, VALID_CATEGORIES,
)

TOOL_REGISTRY = {
    "list_categories": list_categories,
    "list_stores": list_stores,
    "get_total_sales": get_total_sales,
    "get_top_products": get_top_products,
    "get_sales_trend": get_sales_trend,
}

REFUSAL_MESSAGE = (
    "I can only answer questions using these tools: list_categories, list_stores, "
    "get_total_sales, get_top_products, get_sales_trend. I can't run arbitrary SQL "
    "or answer questions outside that schema."
)


def _fallback_route(question):
    q = question.lower()

    if "categor" in q and "top" not in q:
        return {"tool": "list_categories", "params": {}}
    if "store" in q and "sales" not in q and "revenue" not in q:
        return {"tool": "list_stores", "params": {}}

    product_match = re.search(r"\b([A-Z]{3}\d{3})\b", question)
    if product_match and ("trend" in q or "over time" in q or "weekly" in q):
        return {"tool": "get_sales_trend", "params": {"product_id": product_match.group(1)}}

    if "top" in q or "best sell" in q or "best-sell" in q:
        category = next((c for c in VALID_CATEGORIES if c in q), None)
        return {"tool": "get_top_products", "params": {"n": 5, "category": category}}

    if "total" in q or "how many" in q or "revenue" in q or "units" in q:
        category = next((c for c in VALID_CATEGORIES if c in q), None)
        return {"tool": "get_total_sales", "params": {"category": category}}

    return None  # no confident match -> refuse


def _llm_route(question):
    import anthropic
    tool_descriptions = (
        "list_categories() -> list all product categories.\n"
        "list_stores() -> list all stores.\n"
        "get_total_sales(category=None, store_id=None, start_week=None, end_week=None) -> total units/revenue.\n"
        "get_top_products(n=5, category=None) -> top N products by revenue.\n"
        "get_sales_trend(product_id, start_week=0, end_week=51) -> weekly units sold for one product.\n"
    )
    prompt = (
        "You are a retail analytics tool router. Given the user's question, choose EXACTLY ONE tool "
        f"from this list and fill in its parameters:\n{tool_descriptions}\n"
        "You may ONLY use these tools -- never propose running SQL directly or a tool not listed. "
        "If no tool can answer the question, respond with exactly: null\n\n"
        f"Question: {question}\n\n"
        "Respond with ONLY a JSON object: {\"tool\": \"<tool_name>\", \"params\": {...}} or the literal null."
    )
    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    resp = client.messages.create(model="claude-haiku-4-5", max_tokens=200,
                                   messages=[{"role": "user", "content": prompt}])
    text = resp.content[0].text.strip()
    if text == "null":
        return None
    parsed = json.loads(text)
    if parsed.get("tool") not in TOOL_REGISTRY:
        return None
    return parsed


def answer_question(question):
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    routed, mode = None, "fallback"

    if api_key:
        try:
            routed = _llm_route(question)
            mode = "llm"
        except Exception:
            routed = _fallback_route(question)
            mode = "fallback"
    else:
        routed = _fallback_route(question)

    if routed is None or routed.get("tool") not in TOOL_REGISTRY:
        return {"answer": REFUSAL_MESSAGE, "tool_used": None, "mode": mode, "refused": True}

    tool_fn = TOOL_REGISTRY[routed["tool"]]
    params = routed.get("params", {}) or {}
    try:
        result = tool_fn(**params)
    except InvalidToolInput as e:
        return {"answer": f"I couldn't fulfill that: {e}", "tool_used": routed["tool"], "mode": mode, "refused": True}
    except TypeError as e:
        return {"answer": REFUSAL_MESSAGE, "tool_used": None, "mode": mode, "refused": True}

    return {
        "answer": _narrate(routed["tool"], params, result),
        "tool_used": routed["tool"],
        "params": params,
        "result": result,
        "mode": mode,
        "refused": False,
    }


def _narrate(tool_name, params, result):
    if tool_name == "list_categories":
        return f"Available categories: {', '.join(result)}."
    if tool_name == "list_stores":
        return f"There are {len(result)} stores in the dataset."
    if tool_name == "get_total_sales":
        scope = f" in category '{params['category']}'" if params.get("category") else ""
        return f"Total sales{scope}: {result['total_units']} units, ${result['total_revenue']:,.2f} revenue."
    if tool_name == "get_top_products":
        top_list = ", ".join(f"{p['name']} (${p['total_revenue']:,.0f})" for p in result)
        return f"Top products: {top_list}."
    if tool_name == "get_sales_trend":
        return f"Weekly units sold for {params['product_id']}: {[r['units_sold'] for r in result]}."
    return str(result)
