import re

import requests
from bs4 import BeautifulSoup

UA = (
    "Mozilla/5.0 (Linux; Android 14) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/127.0.6533.103 Mobile Safari/537.36 Liskov"
)
HEADERS = {
    "User-Agent": UA,
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Cache-Control": "no-cache",
    "Pragma": "no-cache",
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "none",
    "Upgrade-Insecure-Requests": "1",
}

HOMEPAGE = "https://www.economist.com/"
ARTICLE_PATH_RE = re.compile(r'href="(/[a-z-]+/\d{4}/\d{2}/\d{2}/[a-z0-9-]+)"')

MIN_PARA_CHARS = 200
PAYWALL_SENTINEL = "Subscribers to"


def _get(url: str) -> str:
    r = requests.get(url, headers=HEADERS, timeout=30)
    r.raise_for_status()
    return r.text


def list_homepage_articles(limit: int = 20) -> list[str]:
    html = _get(HOMEPAGE)
    paths = list(dict.fromkeys(ARTICLE_PATH_RE.findall(html)))
    if not paths:
        print(f"[scraper] WARNING: 0 articles parsed from homepage ({len(html)} bytes)")
        print(f"[scraper] first 800 chars: {html[:800]!r}")
    return [f"https://www.economist.com{p}" for p in paths[:limit]]


def fetch_article(url: str) -> dict:
    """Return {url, title, body, date}. Raises on network/parse error."""
    html = _get(url)
    soup = BeautifulSoup(html, "html.parser")

    h1 = soup.find("h1")
    if not h1:
        raise ValueError(f"no <h1> in {url}")
    title = h1.get_text(strip=True)

    article = soup.find("article")
    if not article:
        raise ValueError(f"no <article> in {url}")

    paragraphs = []
    for p in article.find_all("p"):
        text = p.get_text(strip=True)
        if PAYWALL_SENTINEL in text:
            break
        if len(text) < MIN_PARA_CHARS:
            continue
        paragraphs.append(text)

    if not paragraphs:
        raise ValueError(f"no body paragraphs in {url}")

    m = re.search(r"/(\d{4})/(\d{2})/(\d{2})/", url)
    date = f"{m.group(1)}-{m.group(2)}-{m.group(3)}" if m else None

    return {
        "url": url,
        "title": title,
        "body": "\n\n".join(paragraphs),
        "date": date,
    }
