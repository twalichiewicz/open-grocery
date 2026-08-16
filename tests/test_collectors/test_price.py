from datetime import datetime, timezone
from decimal import Decimal

from grocery_index.models import Price


def test_price_creation():
    observed_at = datetime.now(timezone.utc)

    price = Price(
        product_id="product-123",
        retailer="Example",
        store_id="store-123",
        regular_price=Decimal("4.99"),
        sale_price=Decimal("3.99"),
        observed_at=observed_at,
    )

    assert price.regular_price == Decimal("4.99")
    assert price.sale_price == Decimal("3.99")
