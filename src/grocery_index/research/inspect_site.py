import re
from urllib.parse import urljoin

import httpx
from bs4 import BeautifulSoup


USER_AGENT = (
    "Mozilla/5.0 "
    "(compatible; OpenGroceryDataResearch/0.1; "
    "+https://github.com/your-org/open-grocery-data)"
)


CAPTCHA_PATTERNS = [
    r"captcha",
    r"recaptcha",
    r"hcaptcha",
    r"turnstile",
]

AUTH_PATTERNS = [
    r"sign in",
    r"log in",
    r"login",
    r"create account",
]

PAYWALL_PATTERNS = [
    r"subscribe to continue",
    r"subscription required",
    r"paywall",
]


def fetch(url: str, timeout: int = 20) -> dict:
    try:
        response = httpx.get(
            url,
            headers={"User-Agent": USER_AGENT},
            timeout=timeout,
            follow_redirects=True,
        )

        return {
            "status_code": response.status_code,
            "final_url": str(response.url),
            "content_type": response.headers.get("content-type", ""),
            "text": response.text,
            "error": None,
        }

    except Exception as exc:
        return {
            "status_code": None,
            "final_url": url,
            "content_type": "",
            "text": "",
            "error": str(exc),
        }


def detect_barriers(text: str, status_code: int) -> dict:
    lower = text.lower()

    captcha = any(
        re.search(pattern, lower)
        for pattern in CAPTCHA_PATTERNS
    )

    authentication = (
        status_code in {401, 403}
        or any(re.search(pattern, lower) for pattern in AUTH_PATTERNS)
    )

    paywall = any(
        re.search(pattern, lower)
        for pattern in PAYWALL_PATTERNS
    )

    return {
        "captcha": captcha,
        "authentication": authentication,
        "paywall": paywall,
    }


def discover_links(base_url: str, html: str) -> list[str]:
    soup = BeautifulSoup(html, "html.parser")

    links = set()

    for anchor in soup.find_all("a", href=True):
        href = urljoin(base_url, anchor["href"])

        if href.startswith(("http://", "https://")):
            links.add(href)

    return sorted(links)


def inspect_website(website: str) -> dict:
    result = fetch(website)

    barriers = detect_barriers(
        result["text"],
        result["status_code"] or 0,
    )

    links = discover_links(
        result["final_url"],
        result["text"],
    )

    interesting = [
        link for link in links
        if any(
            word in link.lower()
            for word in [
                "product",
                "products",
                "shop",
                "search",
                "store",
                "location",
                "grocery",
                "catalog",
                "api",
            ]
        )
    ]

    return {
        "status_code": result["status_code"],
        "final_url": result["final_url"],
        "content_type": result["content_type"],
        "captcha_detected": barriers["captcha"],
        "authentication_detected": barriers["authentication"],
        "paywall_detected": barriers["paywall"],
        "interesting_links": interesting[:100],
        "error": result["error"],
    }