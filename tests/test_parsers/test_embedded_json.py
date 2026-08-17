from parsers.embedded_json import product_from_dict
from parsers.embedded_json import extract_embedded_products


def test_name_alone_is_not_a_product():
    assert (
        product_from_dict(
            {
                "name": "navigation.click",
            },
            "https://example.com",
        )
        is None
    )


def test_title_alone_is_not_a_product():
    assert (
        product_from_dict(
            {
                "title": "Find a store",
            },
            "https://example.com",
        )
        is None
    )


def test_product_with_sku_is_accepted():
    result = product_from_dict(
        {
            "name": "Organic Milk",
            "sku": "12345",
        },
        "https://example.com",
    )

    assert result is not None
    assert result["product_name"] == "Organic Milk"
    assert result["sku"] == "12345"


def test_product_with_gtin_is_accepted():
    result = product_from_dict(
        {
            "name": "Organic Milk",
            "gtin": "036000291452",
        },
        "https://example.com",
    )

    assert result is not None
    assert result["product_name"] == "Organic Milk"


def test_product_with_price_is_accepted():
    result = product_from_dict(
        {
            "name": "Organic Milk",
            "price": "$4.05",
        },
        "https://example.com",
    )

    assert result is not None
    assert result["price"] == "$4.05"


def test_instacart_product_typename_is_accepted():
    result = product_from_dict(
        {
            "__typename": "ItemsResponseBackedItemV2",
            "name": "Organic Milk",
        },
        "https://example.com",
    )

    assert result is not None
    assert result["product_name"] == "Organic Milk"


def test_analytics_typename_is_not_accepted():
    result = product_from_dict(
        {
            "__typename": "AnalyticsEvent",
            "name": "navigation.click",
        },
        "https://example.com",
    )

    assert result is None


def test_cross_script_dedupe():
    scripts = [
        """
        {
          "product": {
            "name": "Organic Milk",
            "sku": "MILK-1",
            "price": "$4.05"
          }
        }
        """,
        """
        {
          "anotherProduct": {
            "name": "Organic Milk",
            "sku": "MILK-1",
            "price": "$4.05"
          }
        }
        """,
    ]

    result = extract_embedded_products(
        scripts,
        "https://example.com",
    )

    assert len(result) == 1

def test_product_with_item_id_is_accepted():
    result = product_from_dict(
        {
            "name": "Organic Milk",
            "itemId": "ITEM-123",
        },
        "https://example.com",
    )

    assert result is not None
    assert result["product_name"] == "Organic Milk"


def test_product_with_product_id_is_accepted():
    result = product_from_dict(
        {
            "name": "Organic Milk",
            "productId": "PRODUCT-123",
        },
        "https://example.com",
    )

    assert result is not None
    assert result["product_name"] == "Organic Milk"


def test_navigation_with_item_id_is_rejected():
    result = product_from_dict(
        {
            "__typename": "NavigationV2ResponseBackedDefaultItemSection",
            "name": "Products & Services",
            "itemId": "navigation-123",
        },
        "https://example.com",
    )

    assert result is None
