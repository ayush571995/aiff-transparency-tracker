"""Runs every scraper and writes a manifest with the last-updated timestamp."""
from __future__ import annotations

import scrape_documents
import scrape_governance
import scrape_news
from common import now_iso, write_json

if __name__ == "__main__":
    documents = scrape_documents.run()
    write_json("documents.json", documents)

    news = scrape_news.run()
    write_json("news.json", news)

    governance = scrape_governance.run()
    write_json("governance.json", governance)

    write_json(
        "manifest.json",
        {
            "last_updated": now_iso(),
            "counts": {
                "documents": len(documents),
                "news": len(news),
                "governance": len(governance),
            },
        },
    )
    print("\nAll scrapers finished.")
