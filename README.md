# COT Report Analyser

Weekly build of the CFTC [Commitments of Traders](https://www.cftc.gov/MarketReports/CommitmentsofTraders/index.htm)
data across five report types, published as a static site with the full
history kept in the repository.

**Site:** GitHub Pages (Settings → Pages → Source: *GitHub Actions*)

## What it produces

| Tab | CFTC report | Trader groups |
|---|---|---|
| Disaggregated | `fut_disagg_txt_` | Producer/Merchant, Swap Dealers, Managed Money, Other Reportable, Non-Reportable |
| Disaggregated F&O | `com_disagg_txt_` | same, futures **and** options |
| Legacy | `deacot` | Commercial, Non-Commercial, Non-Reportable |
| Financials | `fut_fin_txt_` | Dealer, Asset Manager, Leveraged Funds, Other Reportable, Non-Reportable |
| Supplemental | `dea_cit_txt_` | Commercial ex-CIT, Non-Commercial ex-CIT, Index Traders, Non-Reportable |

For every market and trader group the site shows the net position, the weekly
change, an optional delta against any earlier week, and the percentile rank of
the net position within the trailing 25 weeks, 52 weeks and 3 years. A derived
**Gap** column tracks speculators minus hedgers — the divergence that flags
crowded positioning.

Expanding a row gives the net-position history chart for the selected groups,
the long/short/spread split, and the futures term structure when curve data is
available.

## How the history works

The pipeline writes `data/<report>/<year>.json` and commits it. Only the current
year's file changes on a weekly run, so git stores the history as small deltas
and every past week stays reachable through the date picker — no more
single-snapshot GitHub Pages deploy that overwrites last week's report.

Files are columnar: a list of dates, a list of markets, and one date-by-market
matrix per metric. That is roughly a third the size of a row-per-market layout
and feeds the charts without reshaping.

Working files — the downloaded CFTC archives and the SQLite build database —
live in `outputs/` and are not committed. The workflow restores them from the
Actions cache and rebuilds from scratch on a cache miss.

## Layout

```
cot/
  reports.py       report type registry: archives, date columns, trader groups
  markets.py       market whitelist keyed by CFTC contract market code
  download.py      archive download, extraction, header normalisation
  store.py         SQLite ingest into one generic table shape per report
  metrics.py       net, weekly change, rolling percentiles, gap
  export.py        columnar JSON for the site
  termstructure.py CME settlement curves (see the caveat below)
  pipeline.py      orchestration
site/              static client: index.html, app.js, styles.css
data/              committed output — this is the history
```

Markets are selected by **CFTC contract market code**, which identifies one
contract across all report types. Add a market by adding its code to
`cot/markets.py`; nothing else needs to change.

## Running it locally

```bash
python -m venv .venv && .venv/bin/pip install -r requirements.txt
.venv/bin/python main.py                 # build every report into data/
.venv/bin/python main.py -r legacy_fut   # one report type only
.venv/bin/python main.py --no-download   # re-export from the existing database
python -m http.server 8000               # then open http://localhost:8000/site/
```

## Term structure is currently unavailable

CME Group blocks automated access to its settlements endpoint and answers with
HTTP 403 and a scraping notice. The scraper is still in the tree but is off by
default; `--term-structure` opts in. The site degrades cleanly and says so in
the market detail panel. Restoring the curves means a licensed data source
rather than a workaround.

## Credits

The original downloader was adapted from
[NDelventhal/cot_reports](https://github.com/NDelventhal/cot_reports). The
current `cot/download.py` is a rewrite, but the archive naming conventions came
from there.
