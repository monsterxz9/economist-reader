"""Stateless dedup: query the public site's /api/files/{date} to learn what's
already on R2. Falls back to empty set on errors so a fresh deploy still works."""
import re

import requests

API_BASE = "https://economist.897654321.space/api"
TIMEOUT = 15


def _safe_filename(title_en: str) -> str:
    clean = re.sub(r'[<>:"/\\|?*]', "", title_en).strip()
    return clean[:80]


def pdf_filename(title_en: str) -> str:
    return f"{_safe_filename(title_en)}.pdf"


def existing_files_for_date(date: str) -> set[str]:
    try:
        r = requests.get(f"{API_BASE}/files/{date}", timeout=TIMEOUT)
        r.raise_for_status()
        return set(r.json())
    except requests.RequestException as e:
        print(f"[state] could not fetch existing files for {date}: {e}")
        return set()


def is_already_uploaded(date: str, title_en: str) -> bool:
    return pdf_filename(title_en) in existing_files_for_date(date)
