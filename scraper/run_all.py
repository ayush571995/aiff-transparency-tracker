"""Runs every scraper, diffs against the previous run, and writes today's result
as its own dated partition file under site/data/history/ — so "what changed on
2026-08-21" is a permanent, individually-addressable record, not a row in a
capped rolling array that eventually falls off the end."""
from __future__ import annotations

import json

import scrape_documents
import scrape_governance
import scrape_news
import scrape_tender_results
from common import DATA_DIR, now_iso, write_json

HISTORY_DIR = DATA_DIR / "history"


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


def write_history_partition(today: str, new_documents: list[dict], new_news: list[dict], totals: dict) -> None:
    """One immutable file per calendar day: site/data/history/YYYY-MM-DD.json.
    Re-running the scraper same-day overwrites just that day's file, never others."""
    HISTORY_DIR.mkdir(parents=True, exist_ok=True)
    partition = {
        "date": today,
        "new_documents": [
            {"title": d["title"], "url": d["file_url"], "category": d["category"]} for d in new_documents
        ],
        "new_news": [{"title": n["title"], "url": n["url"]} for n in new_news],
        "totals": totals,
    }
    with (HISTORY_DIR / f"{today}.json").open("w", encoding="utf-8") as fh:
        json.dump(partition, fh, ensure_ascii=False, indent=2)
    print(f"  [ok] wrote history/{today}.json "
          f"({len(new_documents)} new documents, {len(new_news)} new news)")


def rebuild_history_index() -> None:
    """A small index of every partition date that exists, newest first, so the
    static frontend can discover them without directory listing (which static
    hosts don't support). Cheap to rebuild in full every run."""
    HISTORY_DIR.mkdir(parents=True, exist_ok=True)
    dates = sorted(
        (p.stem for p in HISTORY_DIR.glob("*.json") if p.stem != "index"),
        reverse=True,
    )
    with (HISTORY_DIR / "index.json").open("w", encoding="utf-8") as fh:
        json.dump({"dates": dates}, fh, ensure_ascii=False, indent=2)
    print(f"  [ok] wrote history/index.json ({len(dates)} days on record)")


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

    tender_results = scrape_tender_results.run(documents)
    write_json("tender_results.json", tender_results)

    today = now_iso()[:10]
    write_history_partition(
        today,
        new_documents,
        new_news,
        totals={"documents": len(documents), "news": len(news), "governance": len(governance)},
    )
    rebuild_history_index()

    write_json(
        "manifest.json",
        {
            "last_updated": now_iso(),
            "counts": {
                "documents": len(documents),
                "news": len(news),
                "governance": len(governance),
                "tender_results": len(tender_results),
            },
            "today_new_counts": {
                "documents": len(new_documents),
                "news": len(new_news),
            },
        },
    )
    print(f"\nAll scrapers finished. New today: {len(new_documents)} documents, {len(new_news)} news items.")
