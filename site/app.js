/* COT Report Analyser — client.
 *
 * All data lives in data/<report>/<year>.json in a columnar layout: a list of
 * dates, a list of markets, and one date-by-market matrix per metric. The
 * client merges the year files it has loaded into a single store and reads
 * everything by (dateIndex, marketIndex).
 */

// The site is served two ways: from the repo root during development (page at
// /site/, data at /data) and from the Pages bundle (page and data at the root).
let DATA_ROOT = "data";

async function resolveDataRoot() {
  for (const candidate of ["data", "../data"]) {
    try {
      const probe = await fetch(`${candidate}/index.json`, { method: "HEAD" });
      if (probe.ok) { DATA_ROOT = candidate; return; }
    } catch { /* try the next one */ }
  }
}

import { DEFAULT_LANGUAGE, LANGUAGES, LANGUAGE_NAMES, STRINGS } from "./i18n.js";

const SERIES_COLORS = [
  "var(--series-1)", "var(--series-2)", "var(--series-3)",
  "var(--series-4)", "var(--series-5)", "var(--series-6)",
];

// Which trader groups open by default, per report type. Everything else stays
// one click away rather than making the first view 40 columns wide.
const DEFAULT_GROUPS = {
  disaggregated_fut: ["producer", "managed_money", "gap"],
  disaggregated_futopt: ["producer", "managed_money", "gap"],
  legacy_fut: ["commercial", "noncommercial", "gap"],
  traders_in_financial_futures_fut: ["dealer", "leveraged_money", "asset_manager"],
  supplemental_futopt: ["commercial", "noncommercial", "index_trader"],
};


const RANGES = [25, 52, 156, 0];

const COMPARE_OFFSETS = [1, 4, 13, 26, 52];

// Percentile thresholds that count as an extreme. The strong pair drives the
// deeper wash, the plain pair both the lighter wash and the signal engine.
const EXTREME_STRONG_HIGH = 95;
const EXTREME_HIGH = 90;
const EXTREME_LOW = 10;
const EXTREME_STRONG_LOW = 5;

// Rebuilt whenever the language changes: German groups thousands with a dot and
// separates decimals with a comma, so the formatters cannot be constants.
let numberFmt = new Intl.NumberFormat("en-US");
let signedFmt = new Intl.NumberFormat("en-US", { signDisplay: "always" });
let pctFmt = new Intl.NumberFormat("en-US", { maximumFractionDigits: 1 });

/* Look up an interface string in the active language. Values are either plain
 * strings or functions of the interpolated parts — see site/i18n.js. Falls back
 * to English rather than rendering a raw key. */
function t(key, params) {
  const table = STRINGS[state.lang] || STRINGS[DEFAULT_LANGUAGE];
  const value = key in table ? table[key] : STRINGS[DEFAULT_LANGUAGE][key];
  if (value === undefined) return key;
  return typeof value === "function" ? value(params) : value;
}

function compareOptionLabel(weeks) {
  return weeks === 1 ? t("toolbar.previousWeek") : t("toolbar.weeksAgo", { n: weeks });
}

/* ------------------------------------------------------------------ state */

const state = {
  index: null,
  report: null,
  date: null,
  compare: "",
  category: "",
  query: "",
  groups: [],
  measure: "net",
  sort: null,          // { column, direction } — null keeps the category grouping
  expanded: null,      // symbol
  lang: DEFAULT_LANGUAGE,
  shortlistOpen: true,
  shortlistDate: null, // date the cross-report scan currently holds data for
  detailRange: 52,
  stores: new Map(),   // report key -> merged store
  loadedYears: new Map(), // report key -> Set(year)
  termStructure: null,
};

const el = (id) => document.getElementById(id);

/* ------------------------------------------------------------------- data */

async function loadJson(path) {
  const response = await fetch(path, { cache: "no-cache" });
  if (!response.ok) throw new Error(`${path}: HTTP ${response.status}`);
  return response.json();
}

function emptyStore() {
  return { dates: [], markets: [], symbolIndex: new Map(), open_interest: [],
           open_interest_change: [], groups: {} };
}

/** Fold one year file into the report's store, keeping dates sorted. */
function mergeYear(store, payload) {
  const symbols = store.symbolIndex;
  payload.markets.forEach((market) => {
    if (!symbols.has(market.symbol)) {
      symbols.set(market.symbol, store.markets.length);
      store.markets.push(market);
    }
  });

  const columnFor = payload.markets.map((m) => symbols.get(m.symbol));
  const width = store.markets.length;

  const widen = (row) => {
    const out = new Array(width).fill(null);
    for (let i = 0; i < row.length; i += 1) out[columnFor[i]] = row[i];
    return out;
  };
  const grow = (matrix) => matrix.forEach((row) => {
    while (row.length < width) row.push(null);
  });

  grow(store.open_interest);
  grow(store.open_interest_change);
  Object.values(store.groups).forEach((fields) => Object.values(fields).forEach(grow));

  payload.dates.forEach((date, i) => {
    store.dates.push(date);
    store.open_interest.push(widen(payload.open_interest[i]));
    store.open_interest_change.push(widen(payload.open_interest_change[i]));
    Object.entries(payload.groups).forEach(([key, fields]) => {
      const target = store.groups[key] || (store.groups[key] = {});
      Object.entries(fields).forEach(([field, matrix]) => {
        (target[field] || (target[field] = [])).push(widen(matrix[i]));
      });
    });
  });

  sortStoreByDate(store);
  return store;
}

function sortStoreByDate(store) {
  const order = store.dates.map((date, i) => i).sort((a, b) =>
    store.dates[a] < store.dates[b] ? -1 : store.dates[a] > store.dates[b] ? 1 : 0);
  const reorder = (rows) => order.map((i) => rows[i]);

  store.dates = order.map((i) => store.dates[i]);
  store.open_interest = reorder(store.open_interest);
  store.open_interest_change = reorder(store.open_interest_change);
  Object.values(store.groups).forEach((fields) => {
    Object.keys(fields).forEach((field) => { fields[field] = reorder(fields[field]); });
  });
}

async function ensureYear(reportKey, year) {
  const loaded = state.loadedYears.get(reportKey) || new Set();
  if (loaded.has(year)) return;
  const payload = await loadJson(`${DATA_ROOT}/${reportKey}/${year}.json`);
  const store = state.stores.get(reportKey) || emptyStore();
  mergeYear(store, payload);
  state.stores.set(reportKey, store);
  loaded.add(year);
  state.loadedYears.set(reportKey, loaded);
}

/** Load the year holding `date` first so the table paints, then the rest. */
async function ensureReportData(reportKey, date) {
  const meta = reportMeta(reportKey);
  if (!meta.years.length) return;
  const primary = date ? Number(date.slice(0, 4)) : meta.years[meta.years.length - 1];
  await ensureYear(reportKey, meta.years.includes(primary) ? primary : meta.years.at(-1));

  const remaining = meta.years.filter((y) => y !== primary);
  if (!remaining.length) return;
  Promise.all(remaining.map((y) => ensureYear(reportKey, y).catch(() => {})))
    .then(() => { if (state.report === reportKey) render(); });
}

const reportMeta = (key) => state.index.reports.find((r) => r.key === key);

/* --------------------------------------------------------------- accessors */

function storeFor(key) { return state.stores.get(key) || emptyStore(); }

function store() { return storeFor(state.report); }

function dateIndex(date) { return store().dates.indexOf(date); }

function cell(groupKey, field, dateIdx, marketIdx, source = store()) {
  const group = source.groups[groupKey];
  if (!group || !group[field] || dateIdx < 0) return null;
  const row = group[field][dateIdx];
  return row ? row[marketIdx] ?? null : null;
}

function oiCell(field, dateIdx, marketIdx, source = store()) {
  const rows = source[field];
  if (!rows || dateIdx < 0) return null;
  const row = rows[dateIdx];
  return row ? row[marketIdx] ?? null : null;
}

function compareDateIndex() {
  const s = store();
  const current = dateIndex(state.date);
  if (!state.compare || current < 0) return -1;
  if (state.compare.startsWith("offset:")) {
    const weeks = Number(state.compare.slice(7));
    return current - weeks >= 0 ? current - weeks : -1;
  }
  return s.dates.indexOf(state.compare);
}

function activeGroups() {
  const meta = reportMeta(state.report);
  return meta.groups.filter((g) => state.groups.includes(g.key));
}

/* ------------------------------------------------------------------ format */

function fmtInt(value) {
  return value === null || value === undefined ? "—" : numberFmt.format(value);
}

function fmtSigned(value) {
  return value === null || value === undefined ? "—" : signedFmt.format(value);
}

function fmtMeasure(groupKey, dateIdx, marketIdx) {
  if (state.measure === "pct_oi") {
    const value = cell(groupKey, "pct_oi", dateIdx, marketIdx);
    return value === null ? "—" : `${pctFmt.format(value)}%`;
  }
  return fmtInt(cell(groupKey, "net", dateIdx, marketIdx));
}

function deltaClass(value) {
  if (value === null || value === undefined) return "delta-zero";
  if (value > 0) return "delta-pos";
  if (value < 0) return "delta-neg";
  return "delta-zero";
}

// Trailing percentile ranks are not uniformly distributed: a net position that
// trends sits at the edge of its own window for weeks on end, so the bottom and
// top deciles hold roughly a third of all observations. Shading everything from
// the 60th percentile up — as this did — coloured about four cells in five and
// said nothing. Only the deciles that are genuinely rare get a wash now.
function percentileStyle(value) {
  if (value === null || value === undefined) return "";
  if (value >= EXTREME_STRONG_HIGH) return "background: var(--pos-300)";
  if (value >= EXTREME_HIGH) return "background: var(--pos-100)";
  if (value <= EXTREME_STRONG_LOW) return "background: var(--neg-300)";
  if (value <= EXTREME_LOW) return "background: var(--neg-100)";
  return "";
}

/* ------------------------------------------------------------------ signal */

/* What the table is worth flagging.
 *
 * Measured over the committed history (2022-2026, three report types, ~9,000
 * market-weeks where the speculator group sits in its top or bottom decile),
 * asking how far the net position had unwound eight weeks later, in units of
 * its own 52-week standard deviation:
 *
 *   extreme percentile alone      median +0.29  reverted 59.0% of the time
 *   + weekly flow turning         median +0.36               61.0%
 *   + hedgers at the mirror       median +0.44               62.1%
 *
 * So the extreme is context, not an event — the turn is the event, and the
 * hedger mirror confirms it. Three candidates that looked plausible did not
 * survive the same test and are deliberately absent: agreement across the 25w,
 * 52w and 3y windows (no better than the 52w alone, worse in the financials),
 * a freshly entered extreme (+0.28 / 57.8%, below the baseline — a trend that
 * just started does not turn), and a 2-sigma weekly flow shock (27 cases,
 * +0.15 median, less than the plain sign of the weekly change).
 */

// The pair the engine reads, matching cot/metrics.py's gap pair: the first
// commercial group and the first speculator group of the report.
function signalPair(meta) {
  const speculator = meta.groups.find((g) => g.stance === "speculator");
  const commercial = meta.groups.find((g) => g.stance === "commercial");
  return speculator && commercial ? { speculator, commercial } : null;
}

function marketSignal(meta, idx, marketIdx, source = store()) {
  const pair = signalPair(meta);
  if (!pair) return null;

  const specPct = cell(pair.speculator.key, "p52w", idx, marketIdx, source);
  if (specPct === null) return null;

  const side = specPct >= EXTREME_HIGH ? 1 : (specPct <= EXTREME_LOW ? -1 : 0);
  const chg = cell(pair.speculator.key, "chg", idx, marketIdx, source);
  const commPct = cell(pair.commercial.key, "p52w", idx, marketIdx, source);

  const turning = side !== 0 && chg !== null && side * chg < 0;
  const mirror = side !== 0 && commPct !== null &&
    (side > 0 ? commPct <= EXTREME_LOW : commPct >= EXTREME_HIGH);

  return {
    side,
    turning,
    mirror,
    level: turning ? (mirror ? 2 : 1) : 0,
    spec: pair.speculator,
    comm: pair.commercial,
    specPct,
    commPct,
    chg,
    net: cell(pair.speculator.key, "net", idx, marketIdx, source),
    pctOi: cell(pair.speculator.key, "pct_oi", idx, marketIdx, source),
    p25: cell(pair.speculator.key, "p25w", idx, marketIdx, source),
    p156: cell(pair.speculator.key, "p156w", idx, marketIdx, source),
  };
}

const SIGNAL_LABEL = { 2: "signal.reversal", 1: "signal.turning" };

function signalBadge(signal) {
  const badge = document.createElement("span");
  badge.className = `signal signal--${signal.level} signal--${signal.side > 0 ? "long" : "short"}`;
  badge.textContent = t(SIGNAL_LABEL[signal.level]);
  badge.title = t(signal.level === 2 ? "signal.titleReversal" : "signal.titleTurning");
  return badge;
}

/* ------------------------------------------------------- situation summary */

/* The row's ⓘ button. This report gets opened every few weeks at best, by
 * which time nobody remembers what a blue 96 in the third column meant, so the
 * summary spells out the current row in words instead of leaving the reader to
 * decode the colours. */
function situationMarkup(market, marketIdx, idx, meta) {
  const paras = [];
  const signal = marketSignal(meta, idx, marketIdx);

  if (!signal) {
    paras.push(t("summary.noPair"));
  } else {
    const direction = signal.net === null ? t("summary.flat")
      : t(signal.net >= 0 ? "summary.long" : "summary.short");
    paras.push(t("summary.position", {
      group: esc(signal.spec.label),
      direction,
      size: signal.net === null ? "—" : numberFmt.format(Math.abs(signal.net)),
      share: signal.pctOi === null ? ""
        : t("summary.shareOfOi", { pct: pctFmt.format(Math.abs(signal.pctOi)) }),
    }));

    const reading = t(signal.side > 0 ? "summary.readingLong"
      : (signal.side < 0 ? "summary.readingShort" : "summary.readingMid"));
    paras.push(t("summary.percentile", {
      pct: ordinal(signal.specPct),
      windows: t("summary.windows", {
        p25: signal.p25 === null ? null : ordinal(signal.p25),
        p156: signal.p156 === null ? null : ordinal(signal.p156),
      }),
      reading,
    }));

    // Said as a rise or fall of the net figure, never as "added" or "cut": on a
    // net-short book a falling number means the short grew, and the plain verb
    // reads as the opposite.
    if (signal.chg !== null && signal.chg !== 0) {
      paras.push(t("summary.change", {
        verb: t(signal.chg > 0 ? "summary.rose" : "summary.fell"),
        size: numberFmt.format(Math.abs(signal.chg)),
        against: signal.turning ? t("summary.againstExtreme")
          : (signal.side !== 0 ? t("summary.pushingFurther") : ""),
      }));
    }

    if (signal.commPct !== null) {
      paras.push(t("summary.hedger", {
        group: esc(signal.comm.label),
        pct: ordinal(signal.commPct),
        mirror: signal.mirror ? t("summary.mirrorNote") : "",
      }));
    }

    paras.push(verdictHtml(signal));
  }

  const closing = signal ? takeawayHtml(signal) : "";
  return `<div class="tooltip__date">${esc(market.name)} · ${esc(market.symbol)} · ${esc(state.date)}</div>
    <div class="tooltip__note">${paras.map((t) => `<p>${t}</p>`).join("")}${closing}</div>`;
}

/* The line every card and every ⓘ box ends on, for a reader who opens this a few
 * times a year and should not have to reassemble the argument from percentiles.
 *
 * It stops where the forward test stopped. The test measured whether the net
 * position unwinds eight weeks out, so that is what the sentence claims; "which
 * means them selling" is arithmetic on top of it, not a second claim. It does
 * not say the price falls — no price series enters this build, so that step is
 * untested here however plausible it sounds.
 *
 * The rate rides along because the buckets only span 63-66% against a 58% base
 * rate for any position at all. Quoting the hit rate without that baseline
 * would overstate it exactly the way a price claim would. */
const TAKEAWAY_RATE = { A: 66, B: 64, C: 63 };
const TAKEAWAY_BASE = 58;

// The ⓘ box knows the level but not the tier, since the tier also depends on
// liquidity and the open-interest trend. Level 2 is quoted as B rather than A:
// without the open-interest check the better bucket is not established.
function takeawayParts(signal, tier) {
  if (signal.level === 0) {
    return {
      tone: "muted",
      text: t(signal.side !== 0 ? "takeaway.building" : "takeaway.quiet"),
    };
  }
  return {
    tone: signal.side > 0 ? "down" : "up",
    text: t(signal.side > 0 ? "takeaway.down" : "takeaway.up", {
      rate: TAKEAWAY_RATE[tier || (signal.level === 2 ? "B" : "C")],
      base: TAKEAWAY_BASE,
    }),
  };
}

function takeawayHtml(signal) {
  const { tone, text } = takeawayParts(signal);
  return `<p class="takeaway takeaway--${tone}">`
    + `<span class="takeaway__label">${esc(t("takeaway.label"))}</span> ${esc(text)}</p>`;
}

function verdictHtml(signal) {
  const verdict = (className, label, rest) =>
    `<span class="verdict ${className}">${t(label)}</span>${t(rest)}`;

  if (signal.level === 2) {
    return verdict("verdict--strong", "verdict.reversalLabel", "verdict.reversal");
  }
  if (signal.level === 1) {
    return verdict("", "verdict.turningLabel", "verdict.turning");
  }
  return verdict("verdict--muted", "verdict.noneLabel",
                 signal.side !== 0 ? "verdict.building" : "verdict.quiet");
}

function ordinal(value) {
  return t("meta.ordinal", Math.round(value));
}

function esc(text) {
  return String(text ?? "").replace(/[&<>"]/g, (ch) =>
    ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[ch]));
}

/* --------------------------------------------------------------- shortlist */

/* The watchlist: which markets are worth a closer look this week, ranked, in
 * one list across all five report types.
 *
 * The tiers are not invented, they are the buckets that separated in the same
 * forward test as the row badges (2022-2026, net position eight weeks later, in
 * units of its own 52-week deviation):
 *
 *   liquid, extreme only                      n=6201  median +0.37  61.1%
 *   C  liquid + flow turning                  n=1617         +0.45  63.0%
 *   B  C + hedgers at the mirror              n= 987         +0.56  64.2%
 *   A  B + open interest rising               n= 564         +0.57  66.5%
 *   (excluded) illiquid + turning + mirror    n= 437         +0.26  57.2%
 *
 * The liquidity cut is the single biggest effect in the whole exercise and the
 * reason for the exclusion list: below 50k contracts of open interest a
 * percentile extreme is mostly noise in a market too small to mean much. Two
 * candidate refinements were tested and rejected — clustering by category
 * (62.3% against 62.2%, no effect) and position concentration, which turned out
 * to work backwards: past 15% of open interest the unwind got slower, not
 * faster, so it rides along as a caution mark rather than a filter.
 */

const SHORTLIST_MIN_OI = 50000;
const SHORTLIST_CONCENTRATED = 15;
const SHORTLIST_OI_LOOKBACK = 4;
const TIER_ORDER = { A: 0, B: 1, C: 2 };



// One entry per contract, not per report: the same CFTC market code appears in
// up to three report types, and three of them flagging it at once is a sturdier
// reading than any single one. The best tier wins, the rest ride along as chips.
function shortlistCandidates(date) {
  const byMarket = new Map();
  const excluded = [];

  state.index.reports.forEach((meta) => {
    const source = storeFor(meta.key);
    const idx = source.dates.indexOf(date);
    if (idx < 0) return;

    source.markets.forEach((market, marketIdx) => {
      const signal = marketSignal(meta, idx, marketIdx, source);
      if (!signal || signal.level < 1) return;

      const oi = oiCell("open_interest", idx, marketIdx, source);
      if (oi === null) return;
      if (oi < SHORTLIST_MIN_OI) {
        excluded.push({ symbol: market.symbol, name: market.name, oi });
        return;
      }

      const back = idx - SHORTLIST_OI_LOOKBACK;
      const oiThen = back >= 0 ? oiCell("open_interest", back, marketIdx, source) : null;
      const oiRising = oiThen !== null && oi > oiThen;
      const tier = signal.level === 2 ? (oiRising ? "A" : "B") : "C";

      const stamp = { key: meta.key, label: meta.short_label, tier, marketIdx, idx };
      const existing = byMarket.get(market.symbol);
      if (!existing) {
        byMarket.set(market.symbol, {
          symbol: market.symbol, name: market.name, category: market.category,
          tier, side: signal.side, signal, oi, oiRising,
          pctOi: signal.pctOi, source: stamp, reports: [stamp],
        });
        return;
      }
      existing.reports.push(stamp);
      if (TIER_ORDER[tier] < TIER_ORDER[existing.tier]) {
        Object.assign(existing, {
          tier, side: signal.side, signal, oi, oiRising, pctOi: signal.pctOi, source: stamp,
        });
      }
    });
  });

  const rows = [...byMarket.values()].sort((a, b) =>
    TIER_ORDER[a.tier] - TIER_ORDER[b.tier]
    || b.reports.length - a.reports.length
    || Math.abs(b.signal.specPct - 50) - Math.abs(a.signal.specPct - 50)
    || b.oi - a.oi);

  const seen = new Set();
  const thin = excluded.filter((m) => !seen.has(m.symbol) && seen.add(m.symbol));
  return { rows, excluded: thin };
}

// The shortlist reads every report at once, so it needs their year files, not
// just the active tab's. Only the year in view — plus the one before it early in
// January, for the four-week open-interest lookback.
async function ensureShortlistData(date) {
  const year = Number(date.slice(0, 4));
  const week = Math.floor((Date.parse(date) - Date.parse(`${year}-01-01`)) / 6048e5);
  const wanted = week < SHORTLIST_OI_LOOKBACK + 2 ? [year, year - 1] : [year];
  await Promise.all(state.index.reports.flatMap((meta) =>
    wanted.filter((y) => meta.years.includes(y))
      .map((y) => ensureYear(meta.key, y).catch(() => {}))));
  state.shortlistDate = date;
}

function renderShortlist() {
  const section = el("shortlist");
  const body = el("shortlist-body");
  const count = el("shortlist-count");
  const note = el("shortlist-note");

  section.dataset.open = String(state.shortlistOpen);
  const toggle = el("shortlist-toggle");
  toggle.setAttribute("aria-expanded", String(state.shortlistOpen));
  toggle.onclick = () => { state.shortlistOpen = !state.shortlistOpen; renderShortlist(); };

  if (state.shortlistDate !== state.date) {
    count.textContent = t("shortlist.scanning");
    body.replaceChildren();
    note.textContent = "";
    return;
  }

  const { rows, excluded } = shortlistCandidates(state.date);
  count.textContent = rows.length
    ? t("shortlist.count", { n: rows.length })
    : t("shortlist.nothing");

  note.textContent = excluded.length
    ? t("shortlist.excluded", {
        min: numberFmt.format(SHORTLIST_MIN_OI),
        list: excluded.map((m) => `${m.name} (${m.symbol})`).join(", "),
      })
    : "";

  if (!rows.length) {
    body.replaceChildren(Object.assign(document.createElement("p"), {
      className: "shortlist__empty",
      textContent: t("shortlist.empty"),
    }));
    return;
  }

  body.replaceChildren(...rows.map(shortlistCard));
}

function shortlistCard(row) {
  const card = document.createElement("button");
  card.className = `card card--${row.tier}`;
  card.type = "button";
  card.onclick = () => selectReport(row.source.key, {
    date: state.date, market: row.symbol,
  });

  const head = document.createElement("div");
  head.className = "card__head";
  const tier = document.createElement("span");
  tier.className = `card__tier card__tier--${row.tier}`;
  tier.textContent = row.tier;
  tier.title = t(`tier.${row.tier}`);
  const name = document.createElement("span");
  name.className = "card__name";
  name.textContent = row.name;
  const symbol = document.createElement("span");
  symbol.className = "card__symbol";
  symbol.textContent = row.symbol;
  head.append(tier, name, symbol);

  // Stated as the flow that an unwind implies, because that is what was
  // measured. The takeaway line below puts a rate and a base rate on it.
  const pressure = document.createElement("p");
  pressure.className = `card__pressure card__pressure--${row.side > 0 ? "long" : "short"}`;
  pressure.textContent = t(row.side > 0 ? "card.pressureLong" : "card.pressureShort");

  const facts = document.createElement("dl");
  facts.className = "card__facts";
  const fact = (key, value, className = "") => {
    const dt = document.createElement("dt");
    dt.textContent = key;
    const dd = document.createElement("dd");
    dd.textContent = value;
    if (className) dd.className = className;
    facts.append(dt, dd);
  };
  fact(t("card.window52", { label: row.signal.spec.label }), ordinal(row.signal.specPct));
  fact(t("card.window52", { label: row.signal.comm.label }),
       row.signal.commPct === null ? "—" : ordinal(row.signal.commPct));
  fact(t("card.openInterest"), `${compact(row.oi)}${row.oiRising ? " ↑" : ""}`);
  fact(t("card.shareOfOi"), row.pctOi === null ? "—" : `${pctFmt.format(Math.abs(row.pctOi))}%`,
       row.pctOi !== null && Math.abs(row.pctOi) >= SHORTLIST_CONCENTRATED ? "warn" : "");

  const chips = document.createElement("div");
  chips.className = "card__reports";
  row.reports
    .slice()
    .sort((a, b) => TIER_ORDER[a.tier] - TIER_ORDER[b.tier])
    .forEach((stamp) => {
      const chip = document.createElement("span");
      chip.className = "card__report";
      chip.textContent = stamp.label;
      chips.append(chip);
    });

  card.append(head, pressure, facts, chips);

  if (row.pctOi !== null && Math.abs(row.pctOi) >= SHORTLIST_CONCENTRATED) {
    const warn = document.createElement("p");
    warn.className = "card__warn";
    warn.textContent = t("card.concentrated",
                         { pct: pctFmt.format(Math.abs(row.pctOi)) });
    card.append(warn);
  }

  const { tone, text } = takeawayParts(row.signal, row.tier);
  const takeaway = document.createElement("p");
  takeaway.className = `takeaway takeaway--${tone}`;
  const label = document.createElement("span");
  label.className = "takeaway__label";
  label.textContent = t("takeaway.label");
  takeaway.append(label, ` ${text}`);
  card.append(takeaway);

  return card;
}

/* ------------------------------------------------------------------ render */

function render() {
  if (!state.index) return;
  renderTabs();
  renderDescription();
  renderControls();
  renderShortlist();
  renderTable();
  renderGlossary();
  syncHash();
}

function renderTabs() {
  const nav = el("report-tabs");
  nav.replaceChildren(...state.index.reports.map((report) => {
    const button = document.createElement("button");
    button.className = "tab";
    button.type = "button";
    button.role = "tab";
    button.textContent = report.short_label;
    button.setAttribute("aria-selected", String(report.key === state.report));
    button.addEventListener("click", () => selectReport(report.key));
    return button;
  }));
}

function renderDescription() {
  const meta = reportMeta(state.report);
  // The German descriptions ride along in index.json next to the English ones;
  // an older data file that predates them falls back rather than going blank.
  el("report-description").textContent =
    (state.lang === "de" && meta.description_de) || meta.description;
  el("build-meta").textContent = state.index.latest_date
    ? t("app.dataThrough", { date: state.index.latest_date })
    : "";
}

function renderControls() {
  const meta = reportMeta(state.report);
  const dates = [...meta.dates].reverse();

  fillSelect(el("date-select"), dates.map((d) => ({ value: d, label: d })), state.date);
  el("date-select").onchange = (event) => {
    state.date = event.target.value;
    state.expanded = null;
    ensureReportData(state.report, state.date).then(render);
    ensureShortlistData(state.date).then(render);
    render();
  };

  const compareOptions = [{ value: "", label: t("toolbar.compareNone") }];
  COMPARE_OFFSETS.forEach((weeks) => compareOptions.push({
    value: `offset:${weeks}`, label: compareOptionLabel(weeks),
  }));
  dates.filter((d) => d < state.date)
    .slice(0, 260)
    .forEach((d) => compareOptions.push({ value: d, label: d }));
  fillSelect(el("compare-select"), compareOptions, state.compare);
  el("compare-select").onchange = (event) => { state.compare = event.target.value; render(); };

  const categories = [{ value: "", label: t("toolbar.allCategories") }]
    .concat(meta.categories.map((c) => ({ value: c, label: c })));
  fillSelect(el("category-select"), categories, state.category);
  el("category-select").onchange = (event) => { state.category = event.target.value; render(); };

  const search = el("search-input");
  if (search.value !== state.query) search.value = state.query;
  search.oninput = (event) => { state.query = event.target.value.trim(); renderTable(); syncHash(); };

  el("group-chips").replaceChildren(...meta.groups.map((group) => {
    const button = document.createElement("button");
    button.className = "chip";
    button.type = "button";
    button.textContent = group.label;
    button.setAttribute("aria-pressed", String(state.groups.includes(group.key)));
    button.onclick = () => toggleGroup(group.key);
    return button;
  }));

  document.querySelectorAll("#measure-chips .chip").forEach((chip) => {
    chip.setAttribute("aria-pressed", String(chip.dataset.measure === state.measure));
    chip.onclick = () => { state.measure = chip.dataset.measure; render(); };
  });

  const note = el("term-structure-note");
  const curves = state.termStructure && Object.keys(state.termStructure.curves || {}).length;
  note.textContent = t(curves ? "notes.curvesAvailable" : "notes.curvesMissing");

  el("flags-baseline").textContent = t("notes.flags6", { base: TAKEAWAY_BASE });
}

function fillSelect(select, options, value) {
  select.replaceChildren(...options.map((option) => {
    const node = document.createElement("option");
    node.value = option.value;
    node.textContent = option.label;
    return node;
  }));
  select.value = value ?? "";
}

function toggleGroup(key) {
  const next = new Set(state.groups);
  if (next.has(key)) next.delete(key); else next.add(key);
  if (!next.size) return;                       // never leave the table column-less
  const order = reportMeta(state.report).groups.map((g) => g.key);
  state.groups = order.filter((k) => next.has(k));
  render();
}

/* ------------------------------------------------------------------- table */

function visibleMarkets() {
  const s = store();
  const idx = dateIndex(state.date);
  const query = state.query.toLowerCase();

  let rows = s.markets.map((market, i) => ({ market, i }))
    .filter(({ market, i }) => {
      if (state.category && market.category !== state.category) return false;
      if (query && !`${market.name} ${market.symbol}`.toLowerCase().includes(query)) return false;
      return oiCell("open_interest", idx, i) !== null;
    });

  if (state.sort) {
    const { column, direction } = state.sort;
    const value = (entry) => sortValue(column, idx, entry.i);
    rows.sort((a, b) => {
      const av = value(a), bv = value(b);
      if (av === null) return 1;
      if (bv === null) return -1;
      return direction === "asc" ? av - bv : bv - av;
    });
  }
  return rows;
}

function sortValue(column, idx, marketIdx) {
  if (column === "oi") return oiCell("open_interest", idx, marketIdx);
  if (column === "oi_chg") return oiCell("open_interest_change", idx, marketIdx);
  const [groupKey, field] = column.split("|");
  if (field === "delta") {
    const cmp = compareDateIndex();
    const now = cell(groupKey, "net", idx, marketIdx);
    const then = cell(groupKey, "net", cmp, marketIdx);
    return now === null || then === null ? null : now - then;
  }
  return cell(groupKey, field, idx, marketIdx);
}

function renderTable() {
  unpinTooltip();
  const meta = reportMeta(state.report);
  const groups = activeGroups();
  const cmp = compareDateIndex();
  const showDelta = cmp >= 0;
  const idx = dateIndex(state.date);

  const metrics = ["net", "chg", ...(showDelta ? ["delta"] : []), "p25w", "p52w", "p156w"];
  const metricLabels = {
    net: t(state.measure === "pct_oi" ? "table.pctOi" : "table.net"),
    chg: t("table.deltaWeek"),
    delta: t("table.deltaCompare"),
    p25w: t("table.w25"),
    p52w: t("table.w52"),
    p156w: t("table.y3"),
  };

  renderHead(groups, metrics, metricLabels);

  const rows = visibleMarkets();
  const body = el("table-body");
  const status = el("status");

  if (idx < 0 || !rows.length) {
    body.replaceChildren();
    status.hidden = false;
    status.textContent = t(idx < 0 ? "table.loading" : "table.noMatch");
    return;
  }
  status.hidden = true;

  const nodes = [];
  let currentCategory = null;
  const grouped = !state.sort;
  const columnCount = 3 + groups.length * metrics.length;

  rows.forEach(({ market, i }) => {
    if (grouped && market.category !== currentCategory) {
      currentCategory = market.category;
      nodes.push(categoryRow(market.category, columnCount));
    }
    nodes.push(marketRow(market, i, idx, cmp, groups, metrics, meta));
    if (state.expanded === market.symbol) {
      nodes.push(detailRow(market, i, idx, columnCount, meta));
    }
  });

  body.replaceChildren(...nodes);
}

function renderHead(groups, metrics, metricLabels) {
  const head = el("table-head");
  const top = document.createElement("tr");
  top.append(th("", { className: "col-market" }));
  top.append(th(t("table.openInterest"), { colSpan: 2, className: "group-head" }));
  groups.forEach((group) => {
    top.append(th(group.label, { colSpan: metrics.length, className: "group-head" }));
  });

  const bottom = document.createElement("tr");
  bottom.append(th(t("table.market"), { className: "col-market" }));
  bottom.append(sortableTh(t("table.total"), "oi"));
  bottom.append(sortableTh(t("table.deltaWeek"), "oi_chg"));
  groups.forEach((group) => {
    metrics.forEach((metric, position) => {
      const cellEl = sortableTh(metricLabels[metric], `${group.key}|${metric}`);
      if (position === 0) cellEl.classList.add("group-start");
      bottom.append(cellEl);
    });
  });

  head.replaceChildren(top, bottom);
}

function th(text, { colSpan = 1, className = "" } = {}) {
  const node = document.createElement("th");
  node.textContent = text;
  node.colSpan = colSpan;
  node.scope = colSpan > 1 ? "colgroup" : "col";
  if (className) node.className = className;
  return node;
}

function sortableTh(label, column) {
  const node = th(label);
  node.classList.add("sortable");
  const active = state.sort && state.sort.column === column;
  if (active) {
    node.setAttribute("aria-sort", state.sort.direction === "asc" ? "ascending" : "descending");
    const mark = document.createElement("span");
    mark.className = "sort-mark";
    mark.textContent = state.sort.direction === "asc" ? "↑" : "↓";
    node.append(mark);
  }
  node.onclick = () => {
    if (active && state.sort.direction === "desc") state.sort = { column, direction: "asc" };
    else if (active) state.sort = null;
    else state.sort = { column, direction: "desc" };
    renderTable();
  };
  return node;
}

function categoryRow(category, columnCount) {
  const row = document.createElement("tr");
  row.className = "category-row";
  const cellEl = document.createElement("td");
  cellEl.colSpan = columnCount;
  cellEl.textContent = category;
  row.append(cellEl);
  return row;
}

function marketRow(market, marketIdx, idx, cmp, groups, metrics, meta) {
  const row = document.createElement("tr");
  row.className = "market-row";

  const nameCell = document.createElement("td");
  nameCell.className = "col-market";
  const toggle = document.createElement("button");
  toggle.className = "disclose";
  toggle.type = "button";
  toggle.textContent = state.expanded === market.symbol ? "▾" : "▸";
  toggle.setAttribute("aria-expanded", String(state.expanded === market.symbol));
  toggle.setAttribute("aria-label", t("detail.detailsFor", { name: market.name }));
  toggle.onclick = () => {
    state.expanded = state.expanded === market.symbol ? null : market.symbol;
    renderTable();
    syncHash();
  };
  const label = document.createElement("span");
  label.className = "market-name";
  label.append(document.createTextNode(market.name));
  const symbol = document.createElement("span");
  symbol.className = "market-name__symbol";
  symbol.textContent = market.symbol;
  label.append(symbol);
  nameCell.append(toggle, label);

  const signal = marketSignal(meta, idx, marketIdx);
  if (signal && signal.level > 0) {
    nameCell.append(signalBadge(signal));
    row.classList.add(`has-signal-${signal.level}`);
  }
  nameCell.append(infoButton(market, marketIdx, idx, meta));
  row.append(nameCell);

  row.append(td(fmtInt(oiCell("open_interest", idx, marketIdx))));
  row.append(td(fmtSigned(oiCell("open_interest_change", idx, marketIdx)),
                deltaClass(oiCell("open_interest_change", idx, marketIdx))));

  groups.forEach((group) => {
    metrics.forEach((metric, position) => {
      const cellEl = groupCell(group.key, metric, idx, cmp, marketIdx);
      if (position === 0) cellEl.classList.add("group-start");
      row.append(cellEl);
    });
  });

  return row;
}

function groupCell(groupKey, metric, idx, cmp, marketIdx) {
  if (metric === "net") return td(fmtMeasure(groupKey, idx, marketIdx));

  if (metric === "chg") {
    const value = cell(groupKey, "chg", idx, marketIdx);
    return td(fmtSigned(value), deltaClass(value));
  }

  if (metric === "delta") {
    const now = cell(groupKey, "net", idx, marketIdx);
    const then = cell(groupKey, "net", cmp, marketIdx);
    const value = now === null || then === null ? null : now - then;
    return td(fmtSigned(value), deltaClass(value));
  }

  const value = cell(groupKey, metric, idx, marketIdx);
  const cellEl = document.createElement("td");
  const chip = document.createElement("span");
  chip.className = value === null ? "pct pct--na" : "pct";
  chip.textContent = value === null ? "—" : String(value);
  if (value !== null) chip.setAttribute("style", percentileStyle(value));
  cellEl.append(chip);
  return cellEl;
}

function infoButton(market, marketIdx, idx, meta) {
  const button = document.createElement("button");
  button.className = "info";
  button.type = "button";
  button.textContent = "\u24d8";
  button.setAttribute("aria-label", t("detail.infoFor", { name: market.name }));
  attachTooltip(button, () => situationMarkup(market, marketIdx, idx, meta), { pin: true });
  return button;
}

function td(text, className = "") {
  const node = document.createElement("td");
  node.textContent = text;
  if (className) node.className = className;
  return node;
}

/* ------------------------------------------------------------------ detail */

function detailRow(market, marketIdx, idx, columnCount, meta) {
  const row = document.createElement("tr");
  row.className = "detail-row";
  const holder = document.createElement("td");
  holder.colSpan = columnCount;

  const wrap = document.createElement("div");
  wrap.className = "detail";
  wrap.append(historyPanel(market, marketIdx, meta), sidePanel(market, marketIdx, idx, meta));
  holder.append(wrap);
  row.append(holder);
  return row;
}

function historyPanel(market, marketIdx, meta) {
  const panel = document.createElement("div");
  panel.className = "panel";

  const head = document.createElement("div");
  head.className = "panel__head";
  const title = document.createElement("h3");
  title.className = "panel__title";
  title.textContent = t("detail.netHistory", { name: market.name });
  const ranges = document.createElement("div");
  ranges.className = "range-buttons chips";
  RANGES.forEach((range) => {
    const button = document.createElement("button");
    button.className = "chip";
    button.type = "button";
    button.textContent = t(`range.${range}`);
    button.setAttribute("aria-pressed", String(state.detailRange === range));
    button.onclick = () => { state.detailRange = range; renderTable(); };
    ranges.append(button);
  });
  head.append(title, ranges);
  panel.append(head);

  const groups = activeGroups().filter((g) => g.key !== "gap");
  const s = store();
  const window = state.detailRange || s.dates.length;
  const end = dateIndex(state.date) + 1;
  const start = Math.max(0, end - window);
  const dates = s.dates.slice(start, end);

  const series = groups.map((group, i) => ({
    key: group.key,
    label: group.label,
    color: SERIES_COLORS[meta.groups.findIndex((g) => g.key === group.key) % SERIES_COLORS.length],
    values: dates.map((_, k) => cell(group.key, "net", start + k, marketIdx)),
  }));

  panel.append(lineChart(dates, series));
  panel.append(legend(series));
  return panel;
}

function sidePanel(market, marketIdx, idx, meta) {
  const wrap = document.createElement("div");
  wrap.style.display = "grid";
  wrap.style.gap = "18px";
  wrap.style.alignContent = "start";

  const composition = document.createElement("div");
  composition.className = "panel";
  const head = document.createElement("div");
  head.className = "panel__head";
  const title = document.createElement("h3");
  title.className = "panel__title";
  title.textContent = t("detail.longShortSplit");
  const note = document.createElement("span");
  note.className = "panel__note";
  note.textContent = state.date;
  head.append(title, note);
  composition.append(head);

  meta.groups.filter((g) => !g.derived).forEach((group) => {
    const long = cell(group.key, "long", idx, marketIdx) || 0;
    const short = cell(group.key, "short", idx, marketIdx) || 0;
    const spread = cell(group.key, "spread", idx, marketIdx) || 0;
    if (!long && !short && !spread) return;
    composition.append(splitBar(group.label, long, short, spread));
  });
  wrap.append(composition);

  const curve = (state.termStructure?.curves || {})[market.symbol];
  const curvePanel = document.createElement("div");
  curvePanel.className = "panel";
  const curveHead = document.createElement("div");
  curveHead.className = "panel__head";
  const curveTitle = document.createElement("h3");
  curveTitle.className = "panel__title";
  curveTitle.textContent = t("detail.termStructure");
  const curveNote = document.createElement("span");
  curveNote.className = "panel__note";
  curveNote.textContent = curve ? `${curve.overall ?? ""} · ${curve.report_date}`
                                : t("detail.noData");
  curveHead.append(curveTitle, curveNote);
  curvePanel.append(curveHead);
  curvePanel.append(curve ? curveChart(curve) : emptyNote(t("detail.noCurve")));
  wrap.append(curvePanel);

  return wrap;
}

function emptyNote(text) {
  const node = document.createElement("p");
  node.className = "panel__note";
  node.textContent = text;
  return node;
}

function splitBar(label, long, short, spread) {
  const total = long + short + spread;
  const row = document.createElement("div");
  row.className = "bar-row";
  const name = document.createElement("span");
  name.className = "bar-row__label";
  name.textContent = label;
  const track = document.createElement("div");
  track.className = "bar-track";

  [[t("detail.long"), long, "var(--pos-400)"],
   [t("detail.short"), short, "var(--neg-400)"],
   [t("detail.spread"), spread, "var(--surface-3)"]].forEach(([key, value, color]) => {
    if (!value) return;
    const seg = document.createElement("div");
    seg.className = "bar-seg";
    seg.style.flex = String(value);
    seg.style.background = color;
    seg.tabIndex = 0;
    const share = total ? Math.round((value / total) * 100) : 0;
    attachTooltip(seg, () => `<div class="tooltip__date">${label}</div>
      <div class="tooltip__row"><span class="tooltip__key">${key}</span>
      <span class="tooltip__value">${numberFmt.format(value)} · ${share}%</span></div>`);
    track.append(seg);
  });

  row.append(name, track);
  return row;
}

function legend(series) {
  const box = document.createElement("div");
  box.className = "legend";
  series.forEach((entry) => {
    const item = document.createElement("span");
    item.className = "legend__item";
    const swatch = document.createElement("span");
    swatch.className = "legend__swatch";
    swatch.style.setProperty("--swatch", entry.color);
    item.append(swatch, document.createTextNode(entry.label));
    box.append(item);
  });
  return box;
}

/* ------------------------------------------------------------------ charts */

const SVG_NS = "http://www.w3.org/2000/svg";
const svgEl = (name, attrs = {}) => {
  const node = document.createElementNS(SVG_NS, name);
  Object.entries(attrs).forEach(([key, value]) => node.setAttribute(key, value));
  return node;
};

function lineChart(dates, series) {
  const width = 720, height = 240;
  const pad = { top: 12, right: 62, bottom: 22, left: 58 };
  const svg = svgEl("svg", {
    class: "chart", viewBox: `0 0 ${width} ${height}`,
    preserveAspectRatio: "none", role: "img",
    "aria-label": "Net position history",
  });

  const values = series.flatMap((s) => s.values).filter((v) => v !== null);
  if (!dates.length || !values.length) return emptyNote("Not enough history loaded yet.");

  let min = Math.min(0, ...values);
  let max = Math.max(0, ...values);
  if (min === max) { min -= 1; max += 1; }
  const padY = (max - min) * 0.08;
  min -= padY; max += padY;

  const x = (i) => pad.left + (dates.length === 1 ? 0
    : (i / (dates.length - 1)) * (width - pad.left - pad.right));
  const y = (v) => pad.top + (1 - (v - min) / (max - min)) * (height - pad.top - pad.bottom);

  [0, 0.25, 0.5, 0.75, 1].forEach((t) => {
    const value = min + t * (max - min);
    const yy = y(value);
    svg.append(svgEl("line", {
      class: "grid-line", x1: pad.left, x2: width - pad.right, y1: yy, y2: yy,
    }));
    const label = svgEl("text", { x: pad.left - 8, y: yy + 3, "text-anchor": "end" });
    label.textContent = compact(value);
    svg.append(label);
  });

  if (min < 0 && max > 0) {
    svg.append(svgEl("line", {
      class: "zero-line", x1: pad.left, x2: width - pad.right, y1: y(0), y2: y(0),
    }));
  }

  [0, dates.length - 1].forEach((i) => {
    if (i < 0) return;
    const label = svgEl("text", {
      x: x(i), y: height - 6,
      "text-anchor": i === 0 ? "start" : "end",
    });
    label.textContent = dates[i];
    svg.append(label);
  });

  series.forEach((entry) => {
    const points = entry.values.map((v, i) => (v === null ? null : [x(i), y(v)]));
    const path = points.reduce((acc, point, i) => {
      if (!point) return acc;
      const previous = i > 0 && points[i - 1];
      return acc + `${previous ? "L" : "M"}${point[0].toFixed(1)} ${point[1].toFixed(1)}`;
    }, "");
    if (!path) return;
    svg.append(svgEl("path", { class: "series-line", d: path, stroke: entry.color }));

    const lastIndex = points.reduce((acc, p, i) => (p ? i : acc), -1);
    if (lastIndex >= 0) {
      const [px, py] = points[lastIndex];
      svg.append(svgEl("circle", {
        class: "series-end", cx: px, cy: py, r: 3.5, fill: entry.color,
      }));
      const label = svgEl("text", {
        class: "series-label", x: px + 8, y: py + 3.5,
      });
      label.textContent = compact(entry.values[lastIndex]);
      svg.append(label);
    }
  });

  attachCrosshair(svg, { dates, series, x, pad, width, height });
  return svg;
}

function attachCrosshair(svg, { dates, series, x, pad, width, height }) {
  const crosshair = svgEl("line", {
    class: "crosshair", y1: pad.top, y2: height - pad.bottom, x1: 0, x2: 0, opacity: 0,
  });
  svg.append(crosshair);

  const overlay = svgEl("rect", {
    x: pad.left, y: pad.top,
    width: Math.max(1, width - pad.left - pad.right),
    height: Math.max(1, height - pad.top - pad.bottom),
    fill: "transparent",
  });
  svg.append(overlay);

  const nearest = (event) => {
    const box = svg.getBoundingClientRect();
    const scale = width / box.width;
    const local = (event.clientX - box.left) * scale;
    let best = 0, bestDistance = Infinity;
    for (let i = 0; i < dates.length; i += 1) {
      const distance = Math.abs(x(i) - local);
      if (distance < bestDistance) { bestDistance = distance; best = i; }
    }
    return best;
  };

  overlay.addEventListener("pointermove", (event) => {
    const i = nearest(event);
    crosshair.setAttribute("x1", x(i));
    crosshair.setAttribute("x2", x(i));
    crosshair.setAttribute("opacity", 1);
    showTooltip(event, tooltipMarkup(dates[i], series, i));
  });
  overlay.addEventListener("pointerleave", () => {
    crosshair.setAttribute("opacity", 0);
    hideTooltip();
  });
}

function tooltipMarkup(date, series, i) {
  const rows = series.map((entry) => {
    const value = entry.values[i];
    return `<div class="tooltip__row">
      <span class="tooltip__key"><span class="legend__swatch" style="--swatch:${entry.color}"></span>${entry.label}</span>
      <span class="tooltip__value">${value === null ? "—" : numberFmt.format(value)}</span>
    </div>`;
  }).join("");
  return `<div class="tooltip__date">${date}</div>${rows}`;
}

function curveChart(curve) {
  const points = (curve.points || []).slice(0, 18);
  if (points.length < 2) return emptyNote("Curve too short to plot.");

  const width = 380, height = 170;
  const pad = { top: 10, right: 14, bottom: 24, left: 52 };
  const svg = svgEl("svg", {
    class: "chart", viewBox: `0 0 ${width} ${height}`,
    preserveAspectRatio: "none", role: "img",
    "aria-label": "Futures term structure",
  });

  const prices = points.map((p) => p[1]);
  let min = Math.min(...prices), max = Math.max(...prices);
  if (min === max) { min -= 1; max += 1; }
  const padY = (max - min) * 0.12;
  min -= padY; max += padY;

  const x = (i) => pad.left + (i / (points.length - 1)) * (width - pad.left - pad.right);
  const y = (v) => pad.top + (1 - (v - min) / (max - min)) * (height - pad.top - pad.bottom);

  [0, 0.5, 1].forEach((t) => {
    const value = min + t * (max - min);
    svg.append(svgEl("line", {
      class: "grid-line", x1: pad.left, x2: width - pad.right, y1: y(value), y2: y(value),
    }));
    const label = svgEl("text", { x: pad.left - 8, y: y(value) + 3, "text-anchor": "end" });
    label.textContent = compact(value);
    svg.append(label);
  });

  const path = points.map(([, price], i) =>
    `${i ? "L" : "M"}${x(i).toFixed(1)} ${y(price).toFixed(1)}`).join("");
  svg.append(svgEl("path", { class: "series-line", d: path, stroke: "var(--series-1)" }));

  points.forEach(([month, price], i) => {
    const dot = svgEl("circle", {
      class: "series-end", cx: x(i), cy: y(price), r: 3, fill: "var(--series-1)",
    });
    attachTooltip(dot, () => `<div class="tooltip__date">${month.slice(0, 7)}</div>
      <div class="tooltip__row"><span class="tooltip__key">${t("detail.settlement")}</span>
      <span class="tooltip__value">${pctFmt.format(price)}</span></div>`);
    svg.append(dot);
  });

  [0, points.length - 1].forEach((i) => {
    const label = svgEl("text", {
      x: x(i), y: height - 6, "text-anchor": i === 0 ? "start" : "end",
    });
    label.textContent = points[i][0].slice(0, 7);
    svg.append(label);
  });

  return svg;
}

function compact(value) {
  const abs = Math.abs(value);
  if (abs >= 1e6) return `${(value / 1e6).toFixed(1)}M`;
  if (abs >= 1e3) return `${Math.round(value / 1e3)}k`;
  return String(Math.round(value * 100) / 100);
}

/* ----------------------------------------------------------------- tooltip */

const tooltipNode = () => el("tooltip");

// A pinned tooltip survives the pointer leaving its trigger, so the row summary
// can be read at leisure — and on a touch screen at all.
let tooltipPinned = false;

function showTooltip(event, markup, force = false) {
  if (tooltipPinned && !force) return;
  const node = tooltipNode();
  node.innerHTML = markup;
  node.dataset.visible = "true";
  const box = node.getBoundingClientRect();
  const left = Math.min(event.clientX + 14, window.innerWidth - box.width - 10);
  const top = Math.min(event.clientY + 14, window.innerHeight - box.height - 10);
  node.style.left = `${Math.max(8, left)}px`;
  node.style.top = `${Math.max(8, top)}px`;
}

function hideTooltip() {
  if (tooltipPinned) return;
  tooltipNode().dataset.visible = "false";
}

function unpinTooltip() {
  tooltipPinned = false;
  const node = tooltipNode();
  node.dataset.pinned = "false";
  node.dataset.visible = "false";
}

function attachTooltip(node, markup, { pin = false } = {}) {
  const place = (event) => showTooltip(event, markup());
  node.addEventListener("pointerenter", place);
  node.addEventListener("pointermove", place);
  node.addEventListener("pointerleave", hideTooltip);
  node.addEventListener("focus", () => {
    const box = node.getBoundingClientRect();
    place({ clientX: box.left, clientY: box.bottom });
  });
  node.addEventListener("blur", hideTooltip);

  if (!pin) return;
  node.addEventListener("click", (event) => {
    event.stopPropagation();
    if (tooltipPinned) { unpinTooltip(); return; }
    showTooltip(event, markup(), true);
    tooltipPinned = true;
    tooltipNode().dataset.pinned = "true";
  });
}

/* ---------------------------------------------------------------- glossary */

function renderGlossary() {
  const list = el("group-glossary");
  list.replaceChildren(...reportMeta(state.report).groups.map((group) => {
    const item = document.createElement("li");
    const name = document.createElement("strong");
    name.textContent = `${group.label}: `;
    item.append(name, document.createTextNode(
      t(`glossary.${group.key}`) === `glossary.${group.key}`
        ? (group.formula || "")
        : t(`glossary.${group.key}`)));
    return item;
  }));
}

/* ------------------------------------------------------------- language */

/* Text that lives in index.html rather than being generated. Marked up with
 * data-i18n on the element, so adding a string to the page means adding one
 * attribute rather than another line in a render function. */
function renderStatic() {
  document.querySelectorAll("[data-i18n]").forEach((node) => {
    node.textContent = t(node.dataset.i18n);
  });
  document.querySelectorAll("[data-i18n-html]").forEach((node) => {
    node.innerHTML = t(node.dataset.i18nHtml);
  });
  document.querySelectorAll("[data-i18n-placeholder]").forEach((node) => {
    node.placeholder = t(node.dataset.i18nPlaceholder);
  });
  document.querySelectorAll("[data-i18n-aria]").forEach((node) => {
    node.setAttribute("aria-label", t(node.dataset.i18nAria));
  });
}

function applyLanguage(lang) {
  state.lang = LANGUAGES.includes(lang) ? lang : DEFAULT_LANGUAGE;
  const locale = t("meta.locale");
  numberFmt = new Intl.NumberFormat(locale);
  signedFmt = new Intl.NumberFormat(locale, { signDisplay: "always" });
  pctFmt = new Intl.NumberFormat(locale, { maximumFractionDigits: 1 });
  document.documentElement.lang = state.lang;
  renderStatic();
}

function initLanguage() {
  let stored = null;
  try { stored = localStorage.getItem("cot-lang"); } catch { /* private mode */ }
  const guess = (navigator.language || "").slice(0, 2).toLowerCase();
  applyLanguage(stored || (LANGUAGES.includes(guess) ? guess : DEFAULT_LANGUAGE));

  const select = el("language-select");
  select.replaceChildren(...LANGUAGES.map((lang) => {
    const option = document.createElement("option");
    option.value = lang;
    option.textContent = LANGUAGE_NAMES[lang];
    option.selected = lang === state.lang;
    return option;
  }));
  select.onchange = (event) => {
    applyLanguage(event.target.value);
    try { localStorage.setItem("cot-lang", state.lang); } catch { /* ignore */ }
    if (state.index) render();
  };
}

/* ------------------------------------------------------------ url + theme */

function syncHash() {
  const params = new URLSearchParams();
  params.set("report", state.report);
  if (state.date) params.set("date", state.date);
  if (state.compare) params.set("cmp", state.compare);
  if (state.category) params.set("cat", state.category);
  if (state.query) params.set("q", state.query);
  if (state.expanded) params.set("market", state.expanded);
  if (state.measure !== "net") params.set("measure", state.measure);
  params.set("groups", state.groups.join(","));
  history.replaceState(null, "", `#${params.toString()}`);
}

function readHash() {
  return new URLSearchParams(location.hash.replace(/^#/, ""));
}

function applyTheme(theme) {
  if (theme) document.documentElement.setAttribute("data-theme", theme);
  else document.documentElement.removeAttribute("data-theme");
}

function initTheme() {
  let stored = null;
  try { stored = localStorage.getItem("cot-theme"); } catch { /* private mode */ }
  applyTheme(stored);

  el("theme-toggle").onclick = () => {
    const current = document.documentElement.getAttribute("data-theme");
    const prefersDark = window.matchMedia("(prefers-color-scheme: dark)").matches;
    const next = current ? (current === "dark" ? "light" : "dark")
                         : (prefersDark ? "light" : "dark");
    applyTheme(next);
    try { localStorage.setItem("cot-theme", next); } catch { /* ignore */ }
  };
}

/* -------------------------------------------------------------------- boot */

async function selectReport(key, options = {}) {
  state.report = key;
  const meta = reportMeta(key);
  state.groups = options.groups
    || (DEFAULT_GROUPS[key] || meta.groups.slice(0, 3).map((g) => g.key))
       .filter((k) => meta.groups.some((g) => g.key === k));
  state.date = options.date && meta.dates.includes(options.date)
    ? options.date : meta.latest_date;
  state.sort = null;
  state.expanded = options.market || null;
  render();
  await ensureReportData(key, state.date);
  render();
  ensureShortlistData(state.date).then(render);
}

async function boot() {
  initTheme();
  initLanguage();
  document.addEventListener("click", () => { if (tooltipPinned) unpinTooltip(); });
  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape" && tooltipPinned) unpinTooltip();
  });
  await resolveDataRoot();
  try {
    state.index = await loadJson(`${DATA_ROOT}/index.json`);
  } catch (error) {
    el("status").hidden = false;
    el("status").textContent = `Could not load data/index.json — ${error.message}`;
    return;
  }

  loadJson(`${DATA_ROOT}/term_structure.json`)
    .then((payload) => { state.termStructure = payload; render(); })
    .catch(() => { state.termStructure = { curves: {} }; });

  const params = readHash();
  const requested = params.get("report");
  const known = state.index.reports.some((r) => r.key === requested);
  state.compare = params.get("cmp") || "";
  state.category = params.get("cat") || "";
  state.query = params.get("q") || "";
  state.measure = params.get("measure") === "pct_oi" ? "pct_oi" : "net";

  await selectReport(known ? requested : state.index.reports[0].key, {
    date: params.get("date"),
    market: params.get("market"),
    groups: params.get("groups") ? params.get("groups").split(",").filter(Boolean) : null,
  });
}

boot();
