"""
Scrapes AIFF's own News listing (the-aiff.com/articles).

We only store title, category, date and a link back to the original article —
never the article body. Reproducing AIFF's copyrighted articles in full would
be both a copyright problem and pointless; the goal is a dated, linkable index
("what did AIFF say/announce, and when"), not a mirror.
"""
from __future__ import annotations

from common import BASE_URL, get_soup, now_iso, write_json

NEWS_PATH = "/articles"
MAX_PAGES = 5  # be conservative; AIFF's listing may paginate via query params


def scrape_page(path: str) -> list[dict]:
    soup = get_soup(path)
    if soup is None:
        return []

    items = []
    for info in soup.select("div.info"):
        cat_a = info.select_one("a.category")
        title_a = info.select_one(".heading2 a, .heading3 a, h2 a, h3 a") or info.find("a", href=lambda h: h and "/article/" in h)
        date_div = info.select_one(".date")

        if not title_a or not title_a.get("href"):
            continue

        href = title_a["href"].strip()
        if not href.startswith("http"):
            href = f"{BASE_URL}{href}"

        items.append(
            {
                "title": title_a.get_text(strip=True),
                "url": href,
                "category": cat_a.get_text(strip=True) if cat_a else None,
                "date_text": date_div.get_text(strip=True) if date_div else None,
                "source_page": f"{BASE_URL}{path}",
            }
        )
    return items


def run() -> list[dict]:
    print(f"Scraping AIFF news listing ({NEWS_PATH}) ...")
    all_items = scrape_page(NEWS_PATH)

    # de-dupe by URL, keep order
    seen = set()
    deduped = []
    for it in all_items:
        if it["url"] in seen:
            continue
        seen.add(it["url"])
        deduped.append(it)

    scraped_at = now_iso()
    for it in deduped:
        it["scraped_at"] = scraped_at

    print(f"  [ok] {len(deduped)} news items found")
    return deduped


if __name__ == "__main__":
    news = run()
    write_json("news.json", news)
