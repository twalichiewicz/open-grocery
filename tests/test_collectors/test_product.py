from decimal import Decimal

from grocery_index.models import Product


def test_product_creation():
    product = Product(
        product_id="example-1",
        upc_gtin="012345678901",
        retailer="Example",
        product_name="Whole Milk",
        brand="Example Brand",
        package_quantity=Decimal("1"),
        package_unit="gallon",
    )

    assert product.product_name == "Whole Milk"
    assert product.brand == "Example Brand"
    assert product.package_quantity == Decimal("1")
