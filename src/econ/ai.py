import json
import os
import re
import time

import requests

MODEL = "gemma-3-27b-it"
ENDPOINT_TMPL = (
    "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={key}"
)

ANALYZE_PROMPT = """Analyze this Economist article. Return ONLY a JSON object (no markdown, no commentary):

{{
    "title_en": "Original English title",
    "title_cn": "Chinese title (translated)",
    "summary": "One-sentence Chinese summary",
    "sections": [
        {{
            "subtitle_en": "Section subtitle in English",
            "subtitle_cn": "Same subtitle translated to Chinese",
            "paragraphs": [
                {{"en": "English paragraph", "cn": "Professional Chinese translation"}}
            ]
        }}
    ],
    "vocabulary": [
        {{"word": "advanced word/phrase", "mean": "Chinese meaning", "context": "brief English usage note"}}
    ]
}}

Requirements:
- 5-8 advanced TOEIC-level vocabulary words
- Professional, fluent Chinese translation (no machine-translation tone)
- Divide article into 3-5 logical sections by subtopic

Article title: {title}

Article body:
{body}
"""

_FENCE_RE = re.compile(r"^```(?:json)?\s*|\s*```$", re.MULTILINE)


def _strip_fences(text: str) -> str:
    return _FENCE_RE.sub("", text).strip()


def _call(prompt: str, retries: int = 3) -> dict:
    key = os.environ["GEMINI_API_KEY"]
    url = ENDPOINT_TMPL.format(model=MODEL, key=key)
    payload = {"contents": [{"parts": [{"text": prompt}]}]}

    last_err: Exception | None = None
    for attempt in range(retries):
        try:
            r = requests.post(url, json=payload, timeout=120)
            if r.status_code == 429:
                wait = 30 * (attempt + 1)
                print(f"[ai] 429 rate-limited, sleep {wait}s")
                time.sleep(wait)
                continue
            r.raise_for_status()
            text = r.json()["candidates"][0]["content"]["parts"][0]["text"]
            return json.loads(_strip_fences(text))
        except (requests.RequestException, json.JSONDecodeError, KeyError) as e:
            last_err = e
            print(f"[ai] attempt {attempt + 1}/{retries} failed: {e}")
            time.sleep(5 * (attempt + 1))

    raise RuntimeError(f"Gemma call failed after {retries} retries: {last_err}")


def analyze(title: str, body: str) -> dict:
    return _call(ANALYZE_PROMPT.format(title=title, body=body))
