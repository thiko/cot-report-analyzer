"""Whitelist of the markets we report on.

Keyed by CFTC contract market code, which identifies a single futures contract
across every COT report type. Earlier versions keyed on the commodity code and
disambiguated with ad-hoc predicates on the exchange and market name; the
contract code makes that unnecessary and keeps ambiguous markets (natural gas
basis swaps, power hubs) out of the report by construction.

`cme_key` is the CME Group settlements API product id used to pull the term
structure. None means no term structure is available for that market.

Price tickers are derived rather than stored per market: see
PRICE_SOURCES below.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class Market:
    symbol: str
    name: str
    category: str
    cme_key: str | None = None


COMMODITY_MARKETS: dict[str, Market] = {
    # Grains & oilseeds
    "001602": Market("ZW", "Wheat SRW", "Grains", "323"),
    "001612": Market("KE", "Wheat HRW", "Grains"),
    "001626": Market("MW", "Wheat HRSpring", "Grains"),
    "002602": Market("ZC", "Corn", "Grains", "300"),
    "005602": Market("ZS", "Soybeans", "Grains", "320"),
    "007601": Market("ZL", "Soybean Oil", "Grains", "312"),
    "026603": Market("ZM", "Soybean Meal", "Grains", "310"),
    "039601": Market("ZR", "Rough Rice", "Grains", "336"),
    "135731": Market("RS", "Canola", "Grains"),
    "037021": Market("PO", "Palm Oil", "Grains", "2457"),
    # Softs
    "033661": Market("CT", "Cotton No. 2", "Softs", "460"),
    "080732": Market("SB", "Sugar No. 11", "Softs", "470"),
    "083731": Market("KC", "Coffee C", "Softs", "440"),
    "073732": Market("CC", "Cocoa", "Softs", "423"),
    "040701": Market("OJ", "Orange Juice", "Softs"),
    "058644": Market("LBR", "Lumber", "Softs", "10191"),
    # Livestock & dairy
    "054642": Market("HE", "Lean Hogs", "Livestock", "19"),
    "057642": Market("LE", "Live Cattle", "Livestock", "22"),
    "061641": Market("GF", "Feeder Cattle", "Livestock", "34"),
    "050642": Market("CBQ", "Butter", "Dairy", "26"),
    "052641": Market("DCQ", "Milk Class III", "Dairy", "27"),
    "063642": Market("CSC", "Cheese", "Dairy"),
    # Energy
    "067651": Market("CL", "Crude Oil WTI", "Energy", "425"),
    "06765T": Market("BZ", "Brent Last Day", "Energy"),
    "023651": Market("NG", "Natural Gas", "Energy", "444"),
    "022651": Market("HO", "ULSD NY Harbor", "Energy", "426"),
    "111659": Market("RB", "Gasoline RBOB", "Energy", "429"),
    "025651": Market("EH", "Ethanol", "Energy", "338"),
    "86565A": Market("FOC", "Gulf #6 Fuel Oil Crack", "Energy"),
    # Metals
    "088691": Market("GC", "Gold", "Metals", "437"),
    "084691": Market("SI", "Silver", "Metals", "458"),
    "085692": Market("HG", "Copper", "Metals", "438"),
    "076651": Market("PL", "Platinum", "Metals", "446"),
    "075651": Market("PA", "Palladium", "Metals", "445"),
    "191693": Market("ALI", "Aluminium MWP", "Metals", "7440"),
    "192651": Market("HRC", "Steel HRC", "Metals", "487"),
    "188691": Market("CB", "Cobalt", "Metals"),
    "189691": Market("LTH", "Lithium Hydroxide", "Metals"),
}

FINANCIAL_MARKETS: dict[str, Market] = {
    # Short-term rates
    "134741": Market("SR3", "SOFR 3M", "Rates"),
    "134742": Market("SR1", "SOFR 1M", "Rates"),
    "045601": Market("ZQ", "Fed Funds 30D", "Rates"),
    # Treasuries
    "042601": Market("ZT", "UST 2Y Note", "Rates"),
    "044601": Market("ZF", "UST 5Y Note", "Rates"),
    "043602": Market("ZN", "UST 10Y Note", "Rates"),
    "043607": Market("TN", "Ultra UST 10Y", "Rates"),
    "020601": Market("ZB", "UST Bond", "Rates"),
    "020604": Market("UB", "Ultra UST Bond", "Rates"),
    # Currencies
    "099741": Market("6E", "Euro FX", "Currencies"),
    "097741": Market("6J", "Japanese Yen", "Currencies"),
    "096742": Market("6B", "British Pound", "Currencies"),
    "092741": Market("6S", "Swiss Franc", "Currencies"),
    "090741": Market("6C", "Canadian Dollar", "Currencies"),
    "232741": Market("6A", "Australian Dollar", "Currencies"),
    "112741": Market("6N", "New Zealand Dollar", "Currencies"),
    "095741": Market("6M", "Mexican Peso", "Currencies"),
    "102741": Market("6L", "Brazilian Real", "Currencies"),
    "098662": Market("DX", "US Dollar Index", "Currencies"),
    # Equity indices
    "13874A": Market("ES", "E-mini S&P 500", "Equity Indices"),
    "13874+": Market("SPX", "S&P 500 Consolidated", "Equity Indices"),
    "209742": Market("NQ", "E-mini Nasdaq-100", "Equity Indices"),
    "20974+": Market("NDX", "Nasdaq-100 Consolidated", "Equity Indices"),
    "239742": Market("RTY", "E-mini Russell 2000", "Equity Indices"),
    "124603": Market("YM", "DJIA x $5", "Equity Indices"),
    "240743": Market("NKD", "Nikkei 225 (Yen)", "Equity Indices"),
    "244042": Market("MME", "MSCI Emerging Markets", "Equity Indices"),
    "244041": Market("MFS", "MSCI EAFE", "Equity Indices"),
    "1170E1": Market("VX", "VIX Futures", "Volatility"),
    # Crypto
    "133741": Market("BTC", "Bitcoin", "Crypto"),
    "146021": Market("ETH", "Ether Cash Settled", "Crypto"),
    # Commodity index
    "221602": Market("AW", "Bloomberg Commodity Index", "Commodity Index"),
}

UNIVERSES: dict[str, dict[str, Market]] = {
    "commodities": COMMODITY_MARKETS,
    "financials": FINANCIAL_MARKETS,
}

CATEGORY_ORDER = [
    "Grains", "Softs", "Livestock", "Dairy", "Energy", "Metals",
    "Rates", "Currencies", "Equity Indices", "Volatility", "Crypto",
    "Commodity Index",
]


def markets_for(universe: str) -> dict[str, Market]:
    return UNIVERSES[universe]


def category_rank(category: str) -> int:
    try:
        return CATEGORY_ORDER.index(category)
    except ValueError:
        return len(CATEGORY_ORDER)


# Where each market's price series comes from.
#
# Two providers, split by what they can actually deliver. FRED serves rates,
# exchange rates, the equity indices, the energy benchmarks, crypto and the VIX
# daily, with no key and no request limit. Alpha Vantage covers what FRED has
# only monthly — agriculture, softs and metals — through weekly ETF closes; its
# own commodity endpoints return one point a month whatever interval is asked
# for, which is useless against a weekly report.
#
# `kind` is the honest part. A benchmark is the thing the contract is written
# on: DGS10 *is* the ten-year yield, SP500 *is* the index the E-mini settles
# against. A proxy is an ETF standing in for a contract it does not track
# exactly — its own fees, roll schedule and, for the international funds,
# currency exposure all sit between it and the futures return. Earlier this
# file refused proxies outright on those grounds. That was right about the
# distortion and wrong about the remedy: a labelled proxy is worth more than a
# blank column, and an unlabelled one is what actually misleads. So they are
# carried, and every consumer is told which is which.
#
# A market with no entry has no series. Those are contracts with no free source
# at all — dairy, canola, palm oil, ethanol, the fuel-oil crack, the specialty
# metals — not ones waiting to be filled in.
@dataclass(frozen=True)
class PriceSource:
    provider: str          # "fred" | "alphavantage"
    series: str            # FRED series id, or an Alpha Vantage ETF ticker
    kind: str              # "benchmark" | "proxy"
    invert: bool = False   # series moves opposite to the contract


def _fred(series: str, kind: str = "benchmark", invert: bool = False) -> PriceSource:
    return PriceSource("fred", series, kind, invert)


def _av(ticker: str, kind: str = "proxy") -> PriceSource:
    return PriceSource("alphavantage", ticker, kind)


PRICE_SOURCES: dict[str, PriceSource] = {
    # Rates — the constant-maturity yield the contract is written against.
    # These are yields. A note contract's price moves opposite to its yield, so
    # a test that reads the series as a price gets every rates market backwards.
    "ZT": _fred("DGS2", invert=True), "ZF": _fred("DGS5", invert=True),
    "ZN": _fred("DGS10", invert=True), "TN": _fred("DGS10", invert=True),
    "ZB": _fred("DGS30", invert=True), "UB": _fred("DGS30", invert=True),
    "ZQ": _fred("DFF", invert=True), "SR1": _fred("SOFR", invert=True),
    "SR3": _fred("SOFR", invert=True),
    # Currencies. FRED names these source-to-target: DEXUSEU is dollars per
    # euro, which is the way the 6E contract is quoted, but DEXJPUS is yen per
    # dollar, which is the reverse of 6J. The five reversed ones are marked.
    "6A": _fred("DEXUSAL"), "6B": _fred("DEXUSUK"), "6E": _fred("DEXUSEU"),
    "6N": _fred("DEXUSNZ"),
    "6C": _fred("DEXCAUS", invert=True), "6J": _fred("DEXJPUS", invert=True),
    "6S": _fred("DEXSZUS", invert=True), "6L": _fred("DEXBZUS", invert=True),
    "6M": _fred("DEXMXUS", invert=True),
    "DX": _fred("DTWEXBGS", "proxy"),   # broad dollar index, not the ICE basket
    # Equity indices — the index itself for the three FRED carries.
    "ES": _fred("SP500"), "SPX": _fred("SP500"),
    "NQ": _fred("NASDAQ100"), "NDX": _fred("NASDAQ100"),
    "YM": _fred("DJIA"),
    "RTY": _av("IWM"), "MFS": _av("EFA"), "MME": _av("EEM"), "NKD": _av("EWJ"),
    # Energy — the spot benchmarks the contracts settle around.
    "CL": _fred("DCOILWTICO"), "BZ": _fred("DCOILBRENTEU"),
    "NG": _fred("DHHNGSP"), "RB": _fred("DGASNYH"),
    # Crypto and volatility.
    "BTC": _fred("CBBTCUSD"), "ETH": _fred("CBETHUSD"), "VX": _fred("VIXCLS"),
    # Grains, softs, metals — ETF proxies, the only weekly free series going.
    "ZC": _av("CORN"), "ZW": _av("WEAT"), "ZS": _av("SOYB"), "SB": _av("CANE"),
    "GC": _av("GLD"), "SI": _av("SLV"), "HG": _av("CPER"),
    "PL": _av("PPLT"), "PA": _av("PALL"), "AW": _av("DBC"),
}


def price_sources() -> dict[str, PriceSource]:
    """Market symbol -> price source, for every market that has one."""
    known = {market.symbol for universe in UNIVERSES.values()
             for market in universe.values()}
    return {symbol: source for symbol, source in PRICE_SOURCES.items()
            if symbol in known}


def term_structure_targets() -> dict[str, str]:
    """Market symbol -> CME settlements product id, for every market that has one."""
    return {
        market.symbol: market.cme_key
        for market in COMMODITY_MARKETS.values()
        if market.cme_key
    }
