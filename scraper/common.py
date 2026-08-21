"""
Shared helpers for the AIFF Transparency Tracker scraper.

Design principles:
- Be polite: identify ourselves with a real User-Agent, rate-limit requests,
  cache nothing sensitive, only pull pages that are already public.
- Be honest: never invent data. If a page can't be parsed, log a warning and
  skip it rather than guessing.
- Every record we emit carries `source_url` and `scraped_at` so every claim
  on the website can be traced back to where it came from.
"""
from __future__ import annotations

import datetime as _dt
import json
import time
from pathlib import Path
from typing import Any

import requests
from bs4 import BeautifulSoup

BASE_URL = "https://www.the-aiff.com"

HEADERS = {
    "User-Agent": (
        "AIFFTransparencyTrackerBot/0.1 "
        "(+https://roadtowc34football - independent, non-commercial public-interest "
        "tracker; contact via GitHub issues; only reads publicly published pages)"
    ),
    "Accept-Language": "en-IN,en;q=0.9",
}

REQUEST_DELAY_SECONDS = 2.0  # be gentle with AIFF's servers
TIMEOUT_SECONDS = 20

DATA_DIR = Path(__file__).resolve().parent.parent / "site" / "data"


def now_iso() -> str:
    return _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def get_soup(path_or_url: str) -> BeautifulSoup | None:
    """Fetch a page and return a BeautifulSoup tree, or None on failure."""
    url = path_or_url if path_or_url.startswith("http") else f"{BASE_URL}{path_or_url}"
    try:
        resp = requests.get(url, headers=HEADERS, timeout=TIMEOUT_SECONDS)
        time.sleep(REQUEST_DELAY_SECONDS)
        if resp.status_code != 200:
            print(f"  [warn] {url} -> HTTP {resp.status_code}, skipping")
            return None
        resp.encoding = resp.apparent_encoding or "utf-8"
        return BeautifulSoup(resp.text, "lxml")
    except requests.RequestException as exc:
        print(f"  [warn] {url} -> {exc}, skipping")
        return None


def write_json(filename: str, payload: Any) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    out_path = DATA_DIR / filename
    with out_path.open("w", encoding="utf-8") as fh:
        json.dump(payload, fh, ensure_ascii=False, indent=2)
    print(f"  [ok] wrote {out_path} ({len(payload) if isinstance(payload, list) else '1'} records)")


def guess_year(text: str) -> str | None:
    """Best-effort extraction of a fiscal/calendar year like 2023-24 or 2019 from text."""
    import re

    m = re.search(r"(20\d{2})\s*[-–—]\s*(20\d{2}|\d{2})", text)
    if m:
        return m.group(0).replace(" ", "")
    m = re.search(r"20\d{2}", text)
    return m.group(0) if m else None
