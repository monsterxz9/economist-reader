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

RSS_FEEDS = [
    # Substantive sections first so they win the limit budget on busy runs.
    "https://www.economist.com/leaders/rss.xml",
    "https://www.economist.com/briefing/rss.xml",
    "https://www.economist.com/finance-and-economics/rss.xml",
    "https://www.economist.com/business/rss.xml",
    "https://www.economist.com/united-states/rss.xml",
    "https://www.economist.com/china/rss.xml",
    "https://www.economist.com/asia/rss.xml",
    "https://www.economist.com/europe/rss.xml",
    "https://www.economist.com/britain/rss.xml",
    "https://www.economist.com/middle-east-and-africa/rss.xml",
    "https://www.economist.com/the-americas/rss.xml",
    "https://www.economist.com/international/rss.xml",
    "https://www.economist.com/culture/rss.xml",
    "https://www.economist.com/science-and-technology/rss.xml",
    "https://www.economist.com/special-report/rss.xml",
    "https://www.economist.com/books-and-arts/rss.xml",
    "https://www.economist.com/obituary/rss.xml",
    "https://www.economist.com/the-world-this-week/rss.xml",
]
ARTICLE_URL_RE = re.compile(
    r"<link>(https://www\.economist\.com/[a-z-]+/\d{4}/\d{2}/\d{2}/[a-z0-9-]+)</link>"
)
SKIP_SLUG_PATTERNS = ("cartoon", "kals-cartoon", "graphic-detail", "podcast", "newsletter")

MIN_PARA_CHARS = 200
PAYWALL_SENTINEL = "Subscribers to"


def _get(url: str) -> str:
    r = requests.get(url, headers=HEADERS, timeout=30)
    r.raise_for_status()
    return r.text


def list_homepage_articles(limit: int = 20, per_feed: int = 3) -> list[str]:
    """Round-robin recent items across all RSS feeds for cross-section variety.

    Homepage HTML is served stripped on data-center IPs, so we lean on RSS
    which Economist exposes equally to everyone for indexer compatibility.
    """
    per_feed_lists: list[list[str]] = []
    for feed in RSS_FEEDS:
        try:
            xml = _get(feed)
        except Exception as e:
            print(f"[scraper] feed {feed} failed: {e}")
            per_feed_lists.append([])
            continue
        feed_urls: list[str] = []
        for url in ARTICLE_URL_RE.findall(xml):
            slug = url.rsplit("/", 1)[-1]
            if any(p in slug for p in SKIP_SLUG_PATTERNS):
                continue
            feed_urls.append(url)
            if len(feed_urls) >= per_feed:
                break
        per_feed_lists.append(feed_urls)

    seen: set[str] = set()
    out: list[str] = []
    for round_idx in range(per_feed):
        for feed_list in per_feed_lists:
            if round_idx >= len(feed_list):
                continue
            url = feed_list[round_idx]
            if url in seen:
                continue
            seen.add(url)
            out.append(url)
            if len(out) >= limit:
                return out

    if not out:
        print("[scraper] WARNING: 0 articles found across all RSS feeds")
    return out


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
