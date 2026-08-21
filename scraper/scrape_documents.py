"""
Scrapes AIFF's own "Documents & Regulations" section — audit reports / financial
statements, tenders & RFPs, judicial body decisions, and MYAS compliance filings.

These are documents AIFF has chosen to publish itself, so this is the most
solid, undeniable layer of the tracker: we are not accusing them of anything,
we are indexing and dating what they already put in the public domain, and
making it searchable instead of buried in nested pages.
"""
from __future__ import annotations

import re
import urllib.parse

from common import BASE_URL, get_soup, guess_year, now_iso, write_json


# Keyword -> spending-purpose tag, applied to Tenders & RFPs titles so visitors can see
# *what kind* of thing AIFF is spending on, even though AIFF doesn't publish a per-contract
# "amount actually paid" ledger anywhere (that gap is called out explicitly on the site).
PURPOSE_KEYWORDS = [
    ("Media & Broadcasting Rights", ["media right", "broadcast", "streaming", "ott"]),
    ("Sponsorship & Commercial", ["sponsorship", "commercial partner", "brand"]),
    ("Catering & Hospitality", ["catering", "food service", "hospitality"]),
    ("Digital & Social Media", ["digital media", "social media", "website", "app development"]),
    ("Stadium & Venue Operations", ["stadium operations", "venue", "turf", "pitch"]),
    ("Ticketing", ["ticketing"]),
    ("Coaching, Academy & Talent", ["academy", "coaching", "talent", "nce", "scouting"]),
    ("Kit, Footballs & Equipment", ["football", "kit", "jersey", "equipment", "apparel"]),
    ("Travel & Logistics", ["travel", "logistics", "transport", "accommodation", "hotel"]),
    ("Security", ["security"]),
    ("Printing & Merchandise", ["merchandise", "printing"]),
]


def classify_purpose(title: str) -> str:
    t = title.lower()
    for label, keywords in PURPOSE_KEYWORDS:
        if any(k in t for k in keywords):
            return label
    return "Other / Uncategorized"


def prettify_filename(href: str) -> str:
    """Fallback title when the link has no visible text: turn a filename into
    a readable title, e.g. 'Financial-2023-24.pdf' -> 'Financial 2023 24'."""
    name = urllib.parse.unquote(href.rsplit("/", 1)[-1])
    name = re.sub(r"\.(pdf|docx?|xlsx?)$", "", name, flags=re.IGNORECASE)
    name = re.sub(r"[-_]+", " ", name).strip()
    return re.sub(r"\s+", " ", name)

# category slug -> (AIFF path, human label)
DOCUMENT_SECTIONS = [
    ("/documents/audit-report", "Financial Statements / Audit Reports"),
    ("/documents/tenders-and-rfps", "Tenders & RFPs"),
    ("/judicial-documents", "Decisions by AIFF Judicial Bodies"),
    ("/documents/myas-compliance", "MYAS Compliance Filings"),
    ("/documents/constitutionstatus", "Constitution & Statutes"),
]


def scrape_section(path: str, label: str) -> list[dict]:
    soup = get_soup(path)
    if soup is None:
        return []

    records: dict[str, dict] = {}  # dedupe by href, page usually links each file twice (icon + text)
    for a in soup.find_all("a", href=True):
        href = a["href"].strip()
        if not href.lower().endswith((".pdf", ".doc", ".docx", ".xlsx", ".xls")):
            continue
        if not href.startswith("http"):
            href = f"{BASE_URL}{href}"
        title = a.get_text(strip=True)
        if not title and a.find("img"):
            # icon-only link; the sibling text link (same href) will supply the title later
            title = ""
        if href not in records or not records[href]["title"]:
            final_title = title or prettify_filename(href)
            records[href] = {
                "title": final_title,
                "file_url": href,
                "year": guess_year(title) or guess_year(href),
                "category": label,
                "purpose_tag": classify_purpose(final_title) if label == "Tenders & RFPs" else None,
                "source_page": f"{BASE_URL}{path}",
            }

    docs = list(records.values())
    print(f"  [ok] {label}: {len(docs)} documents found")
    return docs


def run() -> list[dict]:
    all_docs: list[dict] = []
    for path, label in DOCUMENT_SECTIONS:
        print(f"Scraping {label} ({path}) ...")
        all_docs.extend(scrape_section(path, label))

    # newest-looking year first, undated last
    all_docs.sort(key=lambda d: d["year"] or "0000", reverse=True)

    scraped_at = now_iso()
    for d in all_docs:
        d["scraped_at"] = scraped_at

    return all_docs


if __name__ == "__main__":
    docs = run()
    write_json("documents.json", docs)
