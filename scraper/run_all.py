"""Runs every scraper, diffs against the previous run to build a changelog
("what's new today"), and writes a manifest with the last-updated timestamp."""
from __future__ import annotations

import json

import scrape_documents
import scrape_governance
import scrape_news
from common import DATA_DIR, now_iso, write_json

CHANGELOG_MAX_ENTRIES = 90  # keep roughly the last ~3 months of daily runs


def load_previous(filename: str) -> list[dict]:
    path = DATA_DIR / filename
    if not path.exists():
        return []
    try:
        with path.open(encoding="utf-8") as fh:
            return json.load(fh)
    except (json.JSONDecodeError, OSError):
        return []


def diff_by_key(old: list[dict], new: list[dict], key: str) -> list[dict]:
    old_keys = {item[key] for item in old}
    return [item for item in new if item[key] not in old_keys]


if __name__ == "__main__":
    prev_documents = load_previous("documents.json")
    prev_news = load_previous("news.json")

    documents = scrape_documents.run()
    news = scrape_news.run()
    governance = scrape_governance.run()

    new_documents = diff_by_key(prev_documents, documents, "file_url")
    new_news = diff_by_key(prev_news, news, "url")

    write_json("documents.json", documents)
    write_json("news.json", news)
    write_json("governance.json", governance)

    today = now_iso()[:10]
    changelog = load_previous("changelog.json")
    if new_documents or new_news:
        # avoid double-logging if the workflow is re-run same day
        changelog = [c for c in changelog if c.get("date") != today]
        changelog.insert(
            0,
            {
                "date": today,
                "new_documents": [
                    {"title": d["title"], "url": d["file_url"], "category": d["category"]}
                    for d in new_documents
                ],
                "new_news": [{"title": n["title"], "url": n["url"]} for n in new_news],
            },
        )
        changelog = changelog[:CHANGELOG_MAX_ENTRIES]
    write_json("changelog.json", changelog)

    write_json(
        "manifest.json",
        {
            "last_updated": now_iso(),
            "counts": {
                "documents": len(documents),
                "news": len(news),
                "governance": len(governance),
            },
            "today_new_counts": {
                "documents": len(new_documents),
                "news": len(new_news),
            },
        },
    )
    print(f"\nAll scrapers finished. New today: {len(new_documents)} documents, {len(new_news)} news items.")
