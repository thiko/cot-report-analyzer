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

const GROUP_GLOSSARY = {
  producer: "Physical hedgers — they own or need the commodity and sell into strength.",
  swap: "Swap dealers hedging over-the-counter exposure, largely index-related flow.",
  managed_money: "CTAs and hedge funds. Trend followers, and the crowd that gets squeezed.",
  other_reportable: "Large traders that fit no other bucket.",
  nonreportable: "Everyone below the reporting threshold — small speculators.",
  commercial: "Hedgers with a business in the underlying market.",
  noncommercial: "Large speculators without a commercial hedging need.",
  index_trader: "Commodity index funds tracking a long-only benchmark.",
  dealer: "Sell-side intermediaries. Their book is the mirror of client flow.",
  asset_manager: "Pensions, insurers and mutual funds holding long-term exposure.",
  leveraged_money: "Hedge funds and levered accounts — the fast money in financials.",
  gap: "Speculators minus hedgers. Extremes flag crowded, one-sided positioning.",
};

const RANGES = [
  { key: 25, label: "25w" },
  { key: 52, label: "52w" },
  { key: 156, label: "3y" },
  { key: 0, label: "Max" },
];

const COMPARE_OFFSETS = [
  { weeks: 1, label: "Previous week" },
  { weeks: 4, label: "4 weeks ago" },
  { weeks: 13, label: "13 weeks ago" },
  { weeks: 26, label: "26 weeks ago" },
  { weeks: 52, label: "52 weeks ago" },
];

const numberFmt = new Intl.NumberFormat("en-US");
const signedFmt = new Intl.NumberFormat("en-US", { signDisplay: "always" });
const pctFmt = new Intl.NumberFormat("en-US", { maximumFractionDigits: 1 });

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

function store() { return state.stores.get(state.report) || emptyStore(); }

function dateIndex(date) { return store().dates.indexOf(date); }

function cell(groupKey, field, dateIdx, marketIdx) {
  const group = store().groups[groupKey];
  if (!group || !group[field] || dateIdx < 0) return null;
  const row = group[field][dateIdx];
  return row ? row[marketIdx] ?? null : null;
}

function oiCell(field, dateIdx, marketIdx) {
  const rows = store()[field];
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

function percentileStyle(value) {
  if (value === null || value === undefined) return "";
  if (value >= 90) return "background: var(--pos-300)";
  if (value >= 75) return "background: var(--pos-200)";
  if (value >= 60) return "background: var(--pos-100)";
  if (value <= 10) return "background: var(--neg-300)";
  if (value <= 25) return "background: var(--neg-200)";
  if (value <= 40) return "background: var(--neg-100)";
  return "";
}

/* ------------------------------------------------------------------ render */

function render() {
  if (!state.index) return;
  renderTabs();
  renderDescription();
  renderControls();
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
  el("report-description").textContent = meta.description;
  el("build-meta").textContent = state.index.latest_date
    ? `data through ${state.index.latest_date}`
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
    render();
  };

  const compareOptions = [{ value: "", label: "— none —" }];
  COMPARE_OFFSETS.forEach((o) => compareOptions.push({ value: `offset:${o.weeks}`, label: o.label }));
  dates.filter((d) => d < state.date)
    .slice(0, 260)
    .forEach((d) => compareOptions.push({ value: d, label: d }));
  fillSelect(el("compare-select"), compareOptions, state.compare);
  el("compare-select").onchange = (event) => { state.compare = event.target.value; render(); };

  const categories = [{ value: "", label: "All categories" }]
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
  note.textContent = curves
    ? "Term structure curves come from CME settlement data stored alongside the positions."
    : "Term structure curves are unavailable — CME Group blocks automated access to its settlement endpoint.";
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
  const meta = reportMeta(state.report);
  const groups = activeGroups();
  const cmp = compareDateIndex();
  const showDelta = cmp >= 0;
  const idx = dateIndex(state.date);

  const metrics = ["net", "chg", ...(showDelta ? ["delta"] : []), "p25w", "p52w", "p156w"];
  const metricLabels = {
    net: state.measure === "pct_oi" ? "% OI" : "Net",
    chg: "Δ week",
    delta: "Δ vs cmp",
    p25w: "25w",
    p52w: "52w",
    p156w: "3y",
  };

  renderHead(groups, metrics, metricLabels);

  const rows = visibleMarkets();
  const body = el("table-body");
  const status = el("status");

  if (idx < 0 || !rows.length) {
    body.replaceChildren();
    status.hidden = false;
    status.textContent = idx < 0 ? "Loading…" : "No markets match these filters.";
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
    nodes.push(marketRow(market, i, idx, cmp, groups, metrics));
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
  top.append(th("Open Interest", { colSpan: 2, className: "group-head" }));
  groups.forEach((group) => {
    top.append(th(group.label, { colSpan: metrics.length, className: "group-head" }));
  });

  const bottom = document.createElement("tr");
  bottom.append(th("Market", { className: "col-market" }));
  bottom.append(sortableTh("Total", "oi"));
  bottom.append(sortableTh("Δ week", "oi_chg"));
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

function marketRow(market, marketIdx, idx, cmp, groups, metrics) {
  const row = document.createElement("tr");
  row.className = "market-row";

  const nameCell = document.createElement("td");
  nameCell.className = "col-market";
  const toggle = document.createElement("button");
  toggle.className = "disclose";
  toggle.type = "button";
  toggle.textContent = state.expanded === market.symbol ? "▾" : "▸";
  toggle.setAttribute("aria-expanded", String(state.expanded === market.symbol));
  toggle.setAttribute("aria-label", `Details for ${market.name}`);
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
  title.textContent = `${market.name} — net position history`;
  const ranges = document.createElement("div");
  ranges.className = "range-buttons chips";
  RANGES.forEach((range) => {
    const button = document.createElement("button");
    button.className = "chip";
    button.type = "button";
    button.textContent = range.label;
    button.setAttribute("aria-pressed", String(state.detailRange === range.key));
    button.onclick = () => { state.detailRange = range.key; renderTable(); };
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
  title.textContent = "Long / short split";
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
  curveTitle.textContent = "Term structure";
  const curveNote = document.createElement("span");
  curveNote.className = "panel__note";
  curveNote.textContent = curve ? `${curve.overall ?? ""} · ${curve.report_date}` : "no data";
  curveHead.append(curveTitle, curveNote);
  curvePanel.append(curveHead);
  curvePanel.append(curve ? curveChart(curve) : emptyNote(
    "No settlement curve stored for this market."));
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

  [["Long", long, "var(--pos-400)"],
   ["Short", short, "var(--neg-400)"],
   ["Spread", spread, "var(--surface-3)"]].forEach(([key, value, color]) => {
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
      <div class="tooltip__row"><span class="tooltip__key">Settlement</span>
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

function showTooltip(event, markup) {
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
  tooltipNode().dataset.visible = "false";
}

function attachTooltip(node, markup) {
  node.addEventListener("pointerenter", (event) => showTooltip(event, markup()));
  node.addEventListener("pointermove", (event) => showTooltip(event, markup()));
  node.addEventListener("pointerleave", hideTooltip);
  node.addEventListener("focus", (event) => showTooltip(
    { clientX: node.getBoundingClientRect().left, clientY: node.getBoundingClientRect().bottom },
    markup()));
  node.addEventListener("blur", hideTooltip);
}

/* ---------------------------------------------------------------- glossary */

function renderGlossary() {
  const list = el("group-glossary");
  list.replaceChildren(...reportMeta(state.report).groups.map((group) => {
    const item = document.createElement("li");
    const name = document.createElement("strong");
    name.textContent = `${group.label}: `;
    item.append(name, document.createTextNode(
      GROUP_GLOSSARY[group.key] || group.formula || ""));
    return item;
  }));
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
}

async function boot() {
  initTheme();
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
