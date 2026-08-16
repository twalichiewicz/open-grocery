# parsers/jsonld.py

import json
from bs4 import BeautifulSoup


def extract_jsonld(html: bytes):
    soup = BeautifulSoup(html, "html.parser")

    results = []

    for script in soup.find_all(
        "script",
        attrs={"type": "application/ld+json"}
    ):
        try:
            data = json.loads(script.string or script.get_text())
            results.append(data)
        except (json.JSONDecodeError, TypeError):
            continue

    return results
