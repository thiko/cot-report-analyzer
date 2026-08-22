# COT Report Analyser

Weekly build of the CFTC [Commitments of Traders](https://www.cftc.gov/MarketReports/CommitmentsofTraders/index.htm)
data across five report types, published as a static site with the full
history kept in the repository.

**Site:** GitHub Pages (Settings → Pages → Source: *GitHub Actions*)

The interface is available in English and German — the picker sits next to the
theme button. Market names, trader group labels and report names stay in English
in both: they are the CFTC's own terms, and German market commentary uses them
untranslated.

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
available. Every row also carries an ⓘ that states the week in words — what the
position is, how stretched, which way it moved, and whether anything is flagged.

## The watchlist

Above the table, **Worth a closer look** scans all five report types for the
selected week and ranks the markets where speculators sit at a 52-week extreme
*and* the weekly flow has turned against it. One card per CFTC market code, so a
contract flagged in three reports at once shows up as one entry with three chips
rather than three rows.

The tiers come out of a forward test over the committed history — 2022 to 2026,
three report types, the speculator net position eight weeks later, measured in
units of its own 52-week standard deviation:

| Bucket | n | Median unwind | Unwound |
|---|---|---|---|
| liquid, extreme percentile only | 6201 | +0.37 | 61.1% |
| **C** liquid + weekly flow turning | 1617 | +0.45 | 63.0% |
| **B** C + hedgers at the mirror extreme | 987 | +0.56 | 64.2% |
| **A** B + open interest rising | 564 | +0.57 | 66.5% |
| *excluded* illiquid + turning + mirror | 437 | +0.26 | 57.2% |

Three things this deliberately does not do. It does not flag an extreme on its
own: that occurs in roughly 38% of market-weeks and persists for a median of
three, because a trending position sits at the edge of its own window by
construction. It does not rank by position concentration, which ran backwards in
the test — past 15% of open interest the unwind got *slower*, so that rides along
as a caution mark instead. And it drops anything under 50,000 contracts of open
interest, which was the single largest effect measured; those markets are listed
under the cards rather than silently dropped.

**What it is not.** No price series enters this build, so every number above
describes how the *position* unwound, not what the market did. The cards say
which flow an unwind implies — crowded longs have to sell — and stop there.
Treat the list as a research queue, not as a signal. Two further caveats worth
keeping in mind: the CFTC publishes Friday for the preceding Tuesday, so the
freshest row is already three days old on arrival, and an extreme is a condition
rather than a trigger — it says the fuel is there, not that it has been lit.

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
  prices.py        daily settlement prices (best effort, see below)
  termstructure.py CME settlement curves (see the caveat below)
  pipeline.py      orchestration
site/              static client: index.html, app.js, styles.css, i18n.js
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
.venv/bin/python main.py --prices        # also refresh the price feed
python -m http.server 8000               # then open http://localhost:8000/site/
```

## Prices

`cot/prices.py` pulls daily closes for 57 of the 70 markets and stores them
alongside the positions, so a positioning signal can eventually be scored
against what the market did rather than only against how the position unwound.
Tickers are derived from the COT symbol — `CL` becomes `CL=F` — with the
exceptions listed in `PRICE_SYMBOL_OVERRIDES`.

The thirteen markets without a price carry `None` there rather than an ETF
stand-in. An ETF tracks something different enough from the contract (fees,
currency hedging, its own roll schedule) that a return computed off it would not
be the contract's return, and a quietly substituted series is worse than an
absent one.

**The stage is off by default and currently has no working source.** Yahoo
answers GitHub's shared address ranges with a standing HTTP 429 — not a burst
limit that clears, but a refusal — and it also blocked an ordinary residential
address for hours after roughly eighty requests. It is not dependable enough to
build on, so nothing in the weekly run touches it.

The code stays because the problem is the source rather than the design, and
swapping in another one is a matter of `fetch_series` and the ticker map. A
key-authenticated API would sidestep the whole issue, since address reputation
stops mattering once a request is authenticated.

If you want to run it anyway:

```bash
.venv/bin/python main.py --prices        # as part of a normal build
.venv/bin/python main.py --prices-only   # feed only, then commit data/prices.json
```

It cannot fail a build either way. Every fetch is wrapped, `_update_prices`
catches whatever is left, and a circuit breaker abandons the stage after three
consecutive transport failures rather than working through the retry ladder for
every market. A symbol the feed answers but has no data for is a delisted
contract, not a wall, and does not count against the breaker. Per-symbol storage
is incremental, so a partial run is kept and the next one continues from it.

Stooq was the first choice and is not usable: it now answers automated requests
with a JavaScript proof-of-work challenge, which is bot detection rather than a
rate limit and is not something to work around.

## Term structure is unavailable

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
