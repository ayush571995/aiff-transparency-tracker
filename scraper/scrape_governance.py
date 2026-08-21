"""
Scrapes AIFF's published Executive Committee (office bearers) listing.

This is who is currently accountable for the organisation, straight from
AIFF's own site — useful as a reference table linked from every other page
("who was in charge when this document was published / this news happened").
"""
from __future__ import annotations

from common import BASE_URL, get_soup, now_iso, write_json

GOVERNANCE_PATH = "/executive-committees"


def run() -> list[dict]:
    print(f"Scraping AIFF Executive Committee ({GOVERNANCE_PATH}) ...")
    soup = get_soup(GOVERNANCE_PATH)
    if soup is None:
        return []

    members = []
    for m in soup.select("div.member"):
        name_el = m.select_one("h4")
        role_el = m.select_one("p")
        img_el = m.select_one("img")
        if not name_el:
            continue
        members.append(
            {
                "name": " ".join(name_el.get_text(strip=True).split()),
                "role": role_el.get_text(strip=True) if role_el else None,
                "photo_url": img_el["src"] if img_el and img_el.get("src") else None,
                "source_page": f"{BASE_URL}{GOVERNANCE_PATH}",
            }
        )

    scraped_at = now_iso()
    for m in members:
        m["scraped_at"] = scraped_at

    print(f"  [ok] {len(members)} executive committee members found")
    return members


if __name__ == "__main__":
    gov = run()
    write_json("governance.json", gov)
