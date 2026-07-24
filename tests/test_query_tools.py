import pytest
from src.query_tools import (
    list_categories, list_stores, get_total_sales, get_top_products,
    get_sales_trend, InvalidToolInput,
)


def test_list_categories_returns_all_five(test_db_path):
    cats = list_categories(db_path=test_db_path)
    assert len(cats) == 5


def test_list_stores_returns_expected_count(test_db_path):
    stores = list_stores(db_path=test_db_path)
    assert len(stores) == 8
    assert all({"store_id", "city", "state"} <= set(s.keys()) for s in stores)


def test_get_total_sales_unfiltered_positive(test_db_path):
    result = get_total_sales(db_path=test_db_path)
    assert result["total_units"] > 0
    assert result["total_revenue"] > 0


def test_get_total_sales_filtered_by_category_is_subset_of_total(test_db_path):
    total = get_total_sales(db_path=test_db_path)
    filtered = get_total_sales(category="grocery", db_path=test_db_path)
    assert filtered["total_units"] < total["total_units"]


def test_get_total_sales_rejects_invalid_category(test_db_path):
    with pytest.raises(InvalidToolInput):
        get_total_sales(category="not_real", db_path=test_db_path)


def test_get_total_sales_rejects_invalid_store(test_db_path):
    with pytest.raises(InvalidToolInput):
        get_total_sales(store_id="NOT_A_STORE", db_path=test_db_path)


def test_get_total_sales_rejects_out_of_range_week(test_db_path):
    with pytest.raises(InvalidToolInput):
        get_total_sales(start_week=999, db_path=test_db_path)


def test_get_top_products_respects_n(test_db_path):
    result = get_top_products(n=3, db_path=test_db_path)
    assert len(result) == 3


def test_get_top_products_rejects_invalid_n(test_db_path):
    with pytest.raises(InvalidToolInput):
        get_top_products(n=0, db_path=test_db_path)
    with pytest.raises(InvalidToolInput):
        get_top_products(n=1000, db_path=test_db_path)


def test_get_top_products_sorted_descending_by_revenue(test_db_path):
    result = get_top_products(n=5, db_path=test_db_path)
    revenues = [p["total_revenue"] for p in result]
    assert revenues == sorted(revenues, reverse=True)


def test_get_sales_trend_returns_52_weeks(test_db_path):
    products = get_top_products(n=1, db_path=test_db_path)
    product_id = products[0]["product_id"]
    trend = get_sales_trend(product_id, db_path=test_db_path)
    assert len(trend) == 52


def test_get_sales_trend_rejects_unknown_product(test_db_path):
    with pytest.raises(InvalidToolInput):
        get_sales_trend("NOT_A_PRODUCT", db_path=test_db_path)
