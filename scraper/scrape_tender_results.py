"""
Finds tender/RFP documents whose titles suggest AIFF has published a *result*
(not just the call for bids) and tries to extract who won and for how much,
directly from the PDF text.

This deals with real money attributed to real companies, so accuracy matters
more than coverage:
  - We only assert a specific winner + amount when the document itself
    explicitly says so (the "L1 BIDDER" pattern AIFF uses).
  - For raw bid-comparison tables with no explicit award statement, we list
    every bidder and every amount exactly as printed, but do NOT claim a
    "winner" ourselves - readers can compare (usually lowest wins on paper),
    but we're not putting words in AIFF's document.
  - For tenders bundling multiple line items (e.g. two events in one tender,
    each with its own amount), we do NOT collapse that to one figure -
    multiple amounts per bidder are shown as multiple amounts, not guessed
    at which is which.
  - Anything we can't confidently parse is still listed, flagged as
    unparsed, with a link to the source PDF - never silently dropped.
"""
from __future__ import annotations

import re

import fitz  # pymupdf
from common import DATA_DIR, get_soup, now_iso, write_json, HEADERS, TIMEOUT_SECONDS, REQUEST_DELAY_SECONDS
import time
import requests

SIGNAL_KEYWORDS = [
    "result", "financial bid", "l1 bidder", "award", "selected",
    "successful bidder", "loi ", "loi-", "loi_",
]

AMOUNT_RE = re.compile(r"(?:Rs\.?|INR)\s*[\d][\d,\s]*\d", re.IGNORECASE)
NAME_LINE_RE = re.compile(r"^[A-Za-z][A-Za-z0-9 &.,'()/\-]{2,80}$")
STOPWORDS = {"TEAM AIFF", "FINANCIAL BID", "FINANCIAL BIDS", "BIDDER", "BID AMOUNT"}


def _clean(s: str) -> str:
    return re.sub(r"\s+", " ", s).strip()


def _parse_amount(s: str) -> int | None:
    digits = re.sub(r"[^\d]", "", s)
    return int(digits) if digits else None


def parse_tender_pdf_text(text: str) -> dict:
    result: dict = {"pattern": "unrecognized", "awarded_to": None, "bidders": [], "lowest_bidder": None}

    if not text or not text.strip():
        # Scanned/image-only PDF - nothing to extract, say so explicitly rather
        # than lumping it in with "we tried and the pattern didn't match".
        result["pattern"] = "image_only"
        return result

    lines = [l.strip() for l in text.split("\n")]
    lines = [l for l in lines if l]
    joined = "\n".join(lines)

    if re.search(r"L1\s*BIDDER", joined, re.IGNORECASE):
        idx = next(i for i, l in enumerate(lines) if re.search(r"L1\s*BIDDER", l, re.IGNORECASE))
        name, amount, quote_basis = None, None, None
        for l in lines[idx + 1: idx + 8]:
            if l.upper() in STOPWORDS:
                continue
            if "QUOTE" in l.upper() or "GST" in l.upper():
                quote_basis = quote_basis or _clean(l)  # e.g. "PER-TEST QUOTE (GST INCLUDED)"
                continue
            if AMOUNT_RE.search(l):
                if amount is None:
                    amount = _parse_amount(AMOUNT_RE.search(l).group(0))
                continue
            if name is None and NAME_LINE_RE.match(l):
                name = _clean(l)
                continue
            if name is not None:
                break
        result["pattern"] = "single_l1"
        result["awarded_to"] = {"name": name, "amount_inr": amount, "quote_basis": quote_basis}
        return result

    if re.search(r"FINANCIAL BIDS?", joined, re.IGNORECASE) and "BIDDER" in joined.upper():
        start_idx = next(i for i, l in enumerate(lines) if re.search(r"FINANCIAL BIDS?", l, re.IGNORECASE))
        sub_lines = lines[start_idx + 1:]
        row_re = re.compile(r"^(\d{1,2})$")
        bidders: list[dict] = []
        i, n = 0, len(sub_lines)
        while i < n:
            if row_re.match(sub_lines[i]) and sub_lines[i] != "#":
                j = i + 1
                block = []
                while j < n and not row_re.match(sub_lines[j]) and sub_lines[j].upper() not in STOPWORDS:
                    block.append(sub_lines[j])
                    j += 1
                name_parts, amounts = [], []
                for bl in block:
                    if AMOUNT_RE.search(bl):
                        amounts += [_parse_amount(a) for a in AMOUNT_RE.findall(bl)]
                    elif not amounts:
                        name_parts.append(bl)
                name = _clean(" ".join(name_parts))
                if name and "INDIAN RUPEES" not in name.upper() and not name.upper().startswith("BIDDER"):
                    bidders.append({"name": name, "amounts_inr": amounts})
                i = j
            else:
                i += 1
        result["pattern"] = "bid_table"
        result["bidders"] = bidders
        if bidders and all(len(b["amounts_inr"]) == 1 for b in bidders):
            lowest = min(bidders, key=lambda b: b["amounts_inr"][0])
            result["lowest_bidder"] = {"name": lowest["name"], "amount_inr": lowest["amounts_inr"][0]}
        else:
            result["multi_line_item"] = any(len(b["amounts_inr"]) > 1 for b in bidders)
        return result

    return result


def fetch_pdf_text(url: str) -> str | None:
    try:
        resp = requests.get(url, headers=HEADERS, timeout=TIMEOUT_SECONDS)
        time.sleep(REQUEST_DELAY_SECONDS)
        if resp.status_code != 200:
            print(f"  [warn] {url} -> HTTP {resp.status_code}")
            return None
        doc = fitz.open(stream=resp.content, filetype="pdf")
        return "\n".join(page.get_text() for page in doc)
    except Exception as exc:  # noqa: BLE001 - want to keep the pipeline going on any single bad PDF
        print(f"  [warn] {url} -> {exc}")
        return None


def run(documents: list[dict]) -> list[dict]:
    tenders = [d for d in documents if d.get("category") == "Tenders & RFPs"]
    candidates = [
        d for d in tenders
        if any(k in d["title"].lower() for k in SIGNAL_KEYWORDS)
    ]
    print(f"Checking {len(candidates)} tender documents that look like results/awards ...")

    records = []
    for d in candidates:
        text = fetch_pdf_text(d["file_url"])
        if text is None:
            records.append({
                "title": d["title"],
                "file_url": d["file_url"],
                "source_page": d["source_page"],
                "pattern": "fetch_failed",
                "awarded_to": None,
                "bidders": [],
                "lowest_bidder": None,
            })
            continue
        parsed = parse_tender_pdf_text(text)
        parsed.update({
            "title": d["title"],
            "file_url": d["file_url"],
            "source_page": d["source_page"],
            "excerpt": text.strip()[:600],
        })
        records.append(parsed)
        print(f"  [ok] {d['title']}: {parsed['pattern']}")

    scraped_at = now_iso()
    for r in records:
        r["scraped_at"] = scraped_at
    return records


if __name__ == "__main__":
    import json
    docs_path = DATA_DIR / "documents.json"
    with docs_path.open(encoding="utf-8") as fh:
        documents = json.load(fh)
    results = run(documents)
    write_json("tender_results.json", results)
