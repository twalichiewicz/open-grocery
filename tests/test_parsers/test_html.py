from parsers.html import extract_html_product


def test_generic_page_title_is_not_a_product():
    html = """
    <html>
      <head>
        <title>Find an Albertsons location near you</title>
        <meta
          property="og:title"
          content="Find an Albertsons location near you | Pharmacy, Grocery, Fuel Stations"
        />
      </head>
      <body></body>
    </html>
    """

    assert extract_html_product(
        html,
        "https://www.albertsons.com/locations",
    ) is None


def test_product_og_title_with_price_is_a_product():
    html = """
    <html>
      <head>
        <title>Whole Milk</title>
        <meta property="og:title" content="Friendly Farms Whole Milk" />
        <meta property="product:price:amount" content="4.05" />
        <meta property="product:price:currency" content="USD" />
        <meta property="product:sku" content="16902710" />
      </head>
      <body></body>
    </html>
    """

    product = extract_html_product(
        html,
        "https://example.com/product/milk",
    )

    assert product is not None
    assert product["product_name"] == "Friendly Farms Whole Milk"
    assert product["price"] == "4.05"
    assert product["currency"] == "USD"
    assert product["sku"] == "16902710"


def test_product_metadata_preserves_availability():
    html = """
    <html>
      <head>
        <meta property="product:name" content="Example Milk" />
        <meta property="product:availability" content="in_stock" />
      </head>
      <body></body>
    </html>
    """

    product = extract_html_product(
        html,
        "https://example.com/product/milk",
    )

    assert product is not None
    assert product["availability"] == "in_stock"


def test_og_type_product_is_a_product_signal():
    html = """
    <html>
      <head>
        <meta property="og:title" content="Example Milk" />
        <meta property="og:type" content="product" />
      </head>
      <body></body>
    </html>
    """

    product = extract_html_product(
        html,
        "https://example.com/product/milk",
    )

    assert product is not None
    assert product["product_name"] == "Example Milk"


def test_non_product_og_type_does_not_count():
    html = """
    <html>
      <head>
        <meta property="og:title" content="Grocery Catalog" />
        <meta property="og:type" content="website" />
      </head>
      <body></body>
    </html>
    """

    assert extract_html_product(
        html,
        "https://example.com/grocery",
    ) is None
