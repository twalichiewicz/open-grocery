from grocery_index.research import Source, SourceCheck


def test_source_check_is_usable():
    source = Source(
        retailer="Example",
        source_url="https://example.com/products",
        source_type="website",
    )

    check = SourceCheck(
        source=source,
        reachable=True,
        status_code=200,
        robots_allowed=True,
    )

    assert check.usable is True


def test_source_check_is_not_usable_when_unreachable():
    source = Source(
        retailer="Example",
        source_url="https://example.com/products",
        source_type="website",
    )

    check = SourceCheck(
        source=source,
        reachable=False,
        error="Connection failed",
    )

    assert check.usable is False


def test_source_check_is_not_usable_when_robots_disallow():
    source = Source(
        retailer="Example",
        source_url="https://example.com/products",
        source_type="website",
    )

    check = SourceCheck(
        source=source,
        reachable=True,
        status_code=200,
        robots_allowed=False,
    )

    assert check.usable is False
