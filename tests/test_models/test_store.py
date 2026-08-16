from grocery_index.models import Store


def test_store_creation():
    store = Store(
        retailer="Example",
        store_id="123",
        address="123 Main St",
        city="Dallas",
        state="TX",
        zip_code="75201",
        latitude=32.7767,
        longitude=-96.7970,
    )

    assert store.retailer == "Example"
    assert store.store_id == "123"
    assert store.city == "Dallas"
    assert store.state == "TX"
