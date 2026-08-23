# COT Report Analyser

Weekly build of the CFTC [Commitments of Traders](https://www.cftc.gov/MarketReports/CommitmentsofTraders/index.htm)
data across five report types, published as a static site with the full
history kept in the repository.

**Site:** <https://thiko.github.io/cot-report-analyzer/>
Published from Pages with Source set to *GitHub Actions*.

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
| *base rate* — liquid, any position off its own median | 16098 | +0.24 | 58.0% |
| liquid, extreme percentile only | 5903 | +0.38 | 61.5% |
| **C** liquid + weekly flow turning | 1621 | +0.46 | 63.3% |
| **B** C + hedgers at the mirror extreme | 982 | +0.53 | 64.3% |
| **A** B + open interest rising | 574 | +0.53 | 65.7% |
| *excluded* illiquid + turning + mirror | 425 | +0.22 | 56.9% |

Reproduce with `python -m cot.forward_test`, which is where these come from.

**Read the first row before the others.** Positions mean-revert over eight weeks
whether or not anything is flagged, so 58% is what doing nothing already gets
you. The full A stack is worth about eight points over that, and C about five —
real, but a good deal less than "66%" sounds on its own. Every rate the interface
quotes is shown against this baseline for that reason.

Extremity is also not monotone. Sorted by distance from a market's own 52-week
median, the unwind rate peaks in the 90th-95th percentile band (64.5%) and *falls*
past the 95th (61.4%); a position pinned at the very edge of its window unwound
57.3% of the time, which is the base rate. A reading that extreme usually means a
trend is running, and trends persist.

Three things this deliberately does not do. It does not flag an extreme on its
own: that occurs in roughly 38% of market-weeks and persists for a median of
three, because a trending position sits at the edge of its own window by
construction. It does not rank by position concentration, which ran backwards in
the test — past 15% of open interest the unwind got *slower*, so that rides along
as a caution mark instead. And it drops anything under 50,000 contracts of open
interest, which was the single largest effect measured; those markets are listed
under the cards rather than silently dropped.

### The price test

The tiers above measure whether the *position* unwound. Whether the price went
the way that unwinding implies is a different question, and now that a price
series exists it is a measurable one. Same horizon, same buckets, each market's
eight-week return normalised by its own weekly volatility, positive when the
market moved the way a crowded position unwinding would push it:

| Bucket | n | Went that way |
|---|---|---|
| *base rate* — any position off its own median | 10797 | 49.8% ±2.7 |
| extreme percentile only | 3713 | 48.6% ±4.5 |
| **C** + weekly flow turning | 1008 | 46.7% ±8.7 |
| **B** C + hedgers at the mirror | 532 | 45.1% ±12.0 |
| **A** B + open interest rising | 309 | 47.6% ±15.8 |

**Nothing here beats a coin flip, and the better buckets are, if anything,
slightly worse.** The interval is wide because consecutive observations share
seven of their eight forward weeks, so the row count is not a count of
independent trials; every bucket is one standard error from 50%. The honest
reading is not "the signal is inverted" but "there is no price signal here to
find". The same caveat applies upward to the position table, whose intervals
are of the same order — the ladder is monotone across five buckets, which is
corroborating structure a single number does not have, but 63.3% against 58.0%
is a smaller finding than it looks.

Two controls. Splitting tier C by source gives 46.5% on the benchmark series
and 47.0% on the ETF proxies, so this is not an artefact of the proxies. And
the sign convention was checked both ways: with the yield and reversed-currency
inversions switched off, or reversed outright, tier C reads 48.4% and 51.1% —
the orientation moves the number by as much as the "signal" does.

**What this means for the interface.** The cards and ⓘ boxes close on the
measured claim — the position probably unwinds, and a crowded long unwinding
means selling — and stop there. That was a caution when the price step was
merely untested. It is now the finding: positioning extremes say something
about positions and nothing this data can detect about price. Treat the list as
a research queue, not as a signal. Two further caveats worth
keeping in mind: the CFTC publishes Friday for the preceding Tuesday, so the
freshest row is already three days old on arrival, and an extreme is a condition
rather than a trigger — it says the fuel is there, not that it has been lit.

## Configuration and the API key

`config.ini` holds the non-secret settings and is committed. The Alpha Vantage
key is not among them: `Config.load` refuses to start if it finds one there,
because a key in that file would be published on the next weekly data push.

The key is read from `$ALPHAVANTAGE_API_KEY` only. In CI that is a repository
secret injected into the build step. Locally, copy `.env.example` to `.env` and
fill it in — `.env` is gitignored, and a real environment variable always wins
over it, so the same code path serves both.

    cp .env.example .env && $EDITOR .env

### The key in CI

Settings → Secrets and variables → Actions → *New repository secret*. Name it
`ALPHAVANTAGE_API_KEY` — the workflow reads exactly that name, and so does
`Config.load`. GitHub masks a secret in job logs on its own.

A repository secret is not available to workflow runs from forked pull
requests. That is the right default here and costs nothing: the weekly job runs
on schedule against `main`, and a fork's run simply builds without the Alpha
Vantage half.

### Where prices come from

| | Markets | Cost |
|---|---|---|
| FRED | 31 — rates, exchange rates, equity indices, energy benchmarks, crypto, VIX | no key, no limit |
| Alpha Vantage | 14 — agriculture, softs, metals, the international index funds | 14 of 25 daily requests |
| *unmapped* | 25 — dairy, canola, palm oil, ethanol, the fuel-oil crack, specialty metals | no free source |

**One key covers a weekly run with room to spare.** The mapping needs fourteen
Alpha Vantage requests against an allowance of twenty-five a day, and several
markets share a series — the ten-year note and the ultra ten-year both settle
against `DGS10` — so those are fetched once and written to each market that maps
to them. Rotating keys to widen the allowance would be circumventing it, and is
not needed: the allowance is already three quarters unused.

Alpha Vantage's own commodity endpoints are not usable here. `WHEAT`, `CORN`,
`COTTON`, `SUGAR`, `COFFEE`, `COPPER` and `ALUMINUM` return *monthly*
observations whatever `interval` is passed, running some weeks behind. Only the
energy series are weekly, and FRED serves those without a key at all. The route
that works for agriculture, softs and metals is `TIME_SERIES_WEEKLY` against the
sector ETFs.

**Benchmarks and proxies are labelled, and the difference matters.** A benchmark
is what the contract is written on — `DGS10` *is* the ten-year yield, `SP500`
*is* the index the E-mini settles against. A proxy is an ETF standing in for a
contract it does not track exactly: its own fees, its own roll schedule, and for
the international funds its own currency exposure all sit between it and the
futures return. `prices.json` carries `kind` per market for that reason. If the
forward test is ever rerun against prices, the proxy series are not the
contract's return and the result has to say so.

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
