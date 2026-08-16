from __future__ import annotations

from decimal import Decimal
from typing import Any


def normalize_currency(value: Any) -> str | None:
    if value is None:
        return None

    currency = str(value).strip().upper()

    if not currency:
        return None

    return currency


def normalize_price_value(
    value: Any,
) -> Decimal | None:
    if value is None:
        return None

    if isinstance(value, Decimal):
        price = value
    else:
        text = str(value).strip()

        if not text:
            return None

        text = (
            text.replace("$", "")
            .replace(",", "")
        )

        try:
            price = Decimal(text)
        except Exception:
            return None

    if price < 0:
        return None

    return price.quantize(Decimal("0.01"))


def normalize_price_record(
    price: Any,
    currency: Any = None,
) -> dict[str, Any]:
    return {
        "price": normalize_price_value(price),
        "currency": normalize_currency(currency),
    }
