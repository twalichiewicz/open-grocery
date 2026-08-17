from decimal import Decimal

from normalize.products import (
    normalize_price,
    normalize_product,
)


def test_price_rejects_non_finite():
    assert normalize_price("NaN") is None
    assert normalize_price("Infinity") is None
    assert normalize_price("-Infinity") is None


def test_price_rejects_unrepresentable_large_value():
    assert normalize_price("1e30") is None


def test_price_european_decimal():
    assert normalize_price("1.234,56") == Decimal("1234.56")


def test_price_us_decimal():
    assert normalize_price("1,234.56") == Decimal("1234.56")


def test_price_simple_comma_decimal():
    assert normalize_price("4,39") == Decimal("4.39")


def test_price_currency_symbol():
    assert normalize_price("€4.39") == Decimal("4.39")


def test_price_currency_suffix():
    assert normalize_price("4.39 USD") == Decimal("4.39")


def test_availability_dict_not_stringified():
    result = normalize_product(
        {
            "product_name": "Test product",
            "availability": {
                "available": True,
            },
        }
    )

    assert result["availability"] is None


def test_brand_dict_extracts_name():
    result = normalize_product(
        {
            "product_name": "Test product",
            "brand": {
                "name": "Example Brand",
            },
        }
    )

    assert result["brand"] == "Example Brand"


def test_gtin_rejects_label():
    result = normalize_product(
        {
            "product_name": "Test product",
            "gtin": "GTIN-13: n/a",
        }
    )

    assert result["gtin"] is None


def test_gtin_validates_check_digit():
    # Valid UPC-A.
    result = normalize_product(
        {
            "product_name": "Test product",
            "gtin": "036000291452",
        }
    )

    assert result["gtin"] == "036000291452"


def test_gtin_rejects_bad_check_digit():
    result = normalize_product(
        {
            "product_name": "Test product",
            "gtin": "036000291453",
        }
    )

    assert result["gtin"] is None
