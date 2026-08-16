from decimal import Decimal

from grocery_index.models import Product


def test_product_creation():
    product = Product(
        product_id="example-1",
        retailer="Example",
        product_name="Example Milk",
        upc_gtin="012345678901",
        brand="Example Brand",
        package_quantity=Decimal("1"),
        package_unit="gallon",
    )

    assert product.product_id == "example-1"
    assert product.retailer == "Example"
    assert product.product_name == "Example Milk"
    assert product.upc_gtin == "012345678901"
    assert product.package_quantity == Decimal("1")
    assert product.package_unit == "gallon"
