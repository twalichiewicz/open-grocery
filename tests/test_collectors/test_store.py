from grocery_index.models import Store


def test_store_creation():
    store = Store(
        store_id="store-123",
        retailer="Example",
        store_name="Example Market",
        city="San Diego",
        state="CA",
        zip_code="92101",
    )

    assert store.store_id == "store-123"
    assert store.city == "San Diego"
