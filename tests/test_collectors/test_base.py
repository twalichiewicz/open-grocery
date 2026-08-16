from grocery_index.collectors import BaseCollector, CollectorResult


class ExampleCollector(BaseCollector):
    retailer = "Example"
    source_name = "Example Source"

    def collect(self, **kwargs):
        return CollectorResult(
            retailer=self.retailer,
            source_name=self.source_name,
            records=[
                {
                    "product_name": "Example Milk",
                    "price": "3.99",
                }
            ],
        )


def test_collector_returns_result():
    collector = ExampleCollector()

    result = collector.collect()

    assert isinstance(result, CollectorResult)
    assert result.retailer == "Example"
    assert result.source_name == "Example Source"
    assert result.record_count == 1
    assert result.status == "success"
