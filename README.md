# RoadTo FIFA WC — AIFF Transparency Tracker

An independent, non-commercial index of what the All India Football Federation (AIFF) has
already published on its own website — audit reports, tenders & RFPs, compliance filings,
judicial decisions, news, and its Executive Committee — made searchable, dated, and easy to
link to. Plus a hand-curated, fully-cited timeline of AIFF governance events since 2022.

**Not affiliated with AIFF, FIFA, AFC, or the Government of India.** See [`site/about.html`](site/about.html)
for the full methodology, sourcing policy, and how to flag a correction.

## Pages

`index` (home) · `today` (daily changelog) · `news` · `documents` (audit reports, tenders/RFPs,
judicial decisions, compliance filings) · `financials` (real audited income/expenditure by fiscal
year, spending-purpose breakdown, RTI request generator) · `governance` (Executive Committee) ·
`conduct` (legal/regulatory framework AIFF operates under) · `timeline` (cited governance history)
· `legal` (editorial policy, sourcing standard, disclaimer, corrections process) · `about`
(methodology).

## How it's built

- `scraper/` — Python (requests + BeautifulSoup) scripts that pull structured records from
  AIFF's own public pages and write them to `site/data/*.json`. Every record carries a
  `source_url`/`source_page` and a `scraped_at` timestamp. No text is generated or summarized —
  titles/dates/links are parsed directly out of AIFF's HTML.
- `site/` — the public site itself: plain HTML + CSS + vanilla JS, no framework, no build step.
  Each page `fetch()`es the relevant JSON at load time and renders it, always with a link back
  to the source.
- `site/data/timeline.json` — the one hand-curated file. Governance-controversy entries
  (FIFA suspension, CAG audit, corruption allegations, ISL/FSDL collapse, etc.), each with an
  explicit `status` (`reported` / `disputed` / `denied`) and one or more source citations.
  This is *not* auto-scraped, on purpose — judgment calls about phrasing disputed claims need
  a human.
- `.github/workflows/scrape.yml` — runs the scraper daily via cron, commits any changes.
- `.github/workflows/deploy.yml` — deploys `site/` to Azure Static Web Apps on every push to
  `main` (including the bot's own daily commits).
- `azure/` — Bicep template + step-by-step `az` CLI instructions to provision the (free-tier)
  Azure Static Web App. See [`azure/DEPLOY.md`](azure/DEPLOY.md).

## Running the scraper locally

```bash
pip install -r requirements.txt
cd scraper
python run_all.py
```

This refreshes `site/data/documents.json`, `news.json`, `governance.json`, and `manifest.json`
straight from the live AIFF site (polite rate-limited requests, identified User-Agent).

## Previewing the site locally

```bash
cd site
python -m http.server 8080
# open http://localhost:8080
```

## Deploying

See [`azure/DEPLOY.md`](azure/DEPLOY.md) for the full walkthrough (create the Static Web App,
wire up the `AZURE_STATIC_WEB_APPS_API_TOKEN` GitHub secret, point a custom domain at it).

## Contributing / corrections

This project only has value if it's accurate. If a scraped title looks wrong, a link is dead,
or a timeline entry needs updating, please open an issue or PR — corrections are the priority,
not new content.

## License

Site and scraper code: MIT. Scraped data is a factual index of AIFF's own public disclosures,
linked back to the originals at every point — no ownership is asserted over AIFF's documents or
news content.
