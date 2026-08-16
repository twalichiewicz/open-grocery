from urllib.parse import urljoin
from urllib.robotparser import RobotFileParser


USER_AGENT = "OpenGroceryDataResearch/0.1"


def inspect_robots(website: str) -> dict:
    robots_url = urljoin(website.rstrip("/") + "/", "robots.txt")

    result = {
        "robots_url": robots_url,
        "available": False,
        "can_fetch_root": None,
        "error": None,
    }

    try:
        rp = RobotFileParser()
        rp.set_url(robots_url)
        rp.read()

        result["available"] = True
        result["can_fetch_root"] = rp.can_fetch(USER_AGENT, website)

    except Exception as exc:
        result["error"] = str(exc)

    return result