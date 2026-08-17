from parsers.common import extract_products


def test_jsonld_product_extracts_offer():
    html = b"""
    <html>
      <script type="application/ld+json">
        {
          "@context": "https://schema.org",
          "@type": "Product",
          "name": "Organic Milk",
          "brand": {"@type": "Brand", "name": "Example Farms"},
          "sku": "MILK-1",
          "offers": {
            "@type": "Offer",
            "price": "4.05",
            "priceCurrency": "USD",
            "availability": "https://schema.org/InStock"
          }
        }
      </script>
    </html>
    """

    result = extract_products(
        html,
        "https://example.com/milk",
    )

    assert result == [
        {
            "source_url": "https://example.com/milk",
            "product_name": "Organic Milk",
            "brand": "Example Farms",
            "gtin": "",
            "sku": "MILK-1",
            "price": "4.05",
            "currency": "USD",
            "availability": "https://schema.org/InStock",
        }
    ]


def test_jsonld_array_is_supported():
    html = b"""
    <script type="application/ld+json">
      [
        {
          "@type": "Product",
          "name": "Milk",
          "sku": "MILK-1",
          "offers": {"price": "4.05"}
        },
        {
          "@type": "Product",
          "name": "Eggs",
          "sku": "EGG-1",
          "offers": {"price": "3.99"}
        }
      ]
    </script>
    """

    result = extract_products(
        html,
        "https://example.com",
    )

    assert [item["product_name"] for item in result] == [
        "Milk",
        "Eggs",
    ]


def test_jsonld_graph_is_supported():
    html = b"""
    <script type="application/ld+json">
      {
        "@context": "https://schema.org",
        "@graph": [
          {
            "@type": "WebSite",
            "name": "Example"
          },
          {
            "@type": "Product",
            "name": "Butter",
            "sku": "BUTTER-1",
            "offers": {
              "price": "5.49",
              "priceCurrency": "USD"
            }
          }
        ]
      }
    </script>
    """

    result = extract_products(
        html,
        "https://example.com",
    )

    assert len(result) == 1
    assert result[0]["product_name"] == "Butter"


def test_jsonld_non_product_is_ignored():
    html = b"""
    <script type="application/ld+json">
      {
        "@type": "Organization",
        "name": "Example Grocery"
      }
    </script>
    """

    assert extract_products(
        html,
        "https://example.com",
    ) == []
