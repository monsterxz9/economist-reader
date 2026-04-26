"""Stateless dedup: query the public site's /api/files/{date} to learn what's
already on R2. Falls back to empty set on errors so a fresh deploy still works."""
import re

import requests

API_BASE = "https://economist.897654321.space/api"
TIMEOUT = 15
SECTION_RE = re.compile(r"economist\.com/([a-z-]+)/\d{4}/\d{2}/\d{2}/")


def _safe(text: str, max_len: int) -> str:
    clean = re.sub(r'[<>:"/\\|?*]', "", text).strip()
    return clean[:max_len]


def section_from_url(url: str) -> str:
    m = SECTION_RE.search(url)
    return m.group(1) if m else "article"


def pdf_filename(url: str, title_en: str) -> str:
    """`[section] Title.pdf` — section disambiguates same-titled summaries
    (e.g. weekly 'Business' / 'Politics' across the-world-this-week issues)."""
    section = section_from_url(url)
    return f"[{section}] {_safe(title_en, 80)}.pdf"


def existing_files_for_date(date: str) -> set[str]:
    try:
        r = requests.get(f"{API_BASE}/files/{date}", timeout=TIMEOUT)
        r.raise_for_status()
        return set(r.json())
    except requests.RequestException as e:
        print(f"[state] could not fetch existing files for {date}: {e}")
        return set()


def is_already_uploaded(date: str, url: str, title_en: str) -> bool:
    return pdf_filename(url, title_en) in existing_files_for_date(date)
