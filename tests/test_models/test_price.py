from decimal import Decimal

from grocery_index.models import Price


def test_price_creation():
    price = Price(
        retailer="Example",
        product_id="milk-123",
        regular_price=Decimal("4.99"),
        sale_price=Decimal("3.99"),
    )

    assert price.regular_price == Decimal("4.99")
    assert price.sale_price == Decimal("3.99")
