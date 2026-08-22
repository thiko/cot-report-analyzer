"""Whitelist of the markets we report on.

Keyed by CFTC contract market code, which identifies a single futures contract
across every COT report type. Earlier versions keyed on the commodity code and
disambiguated with ad-hoc predicates on the exchange and market name; the
contract code makes that unnecessary and keeps ambiguous markets (natural gas
basis swaps, power hubs) out of the report by construction.

`cme_key` is the CME Group settlements API product id used to pull the term
structure. None means no term structure is available for that market.
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


def term_structure_targets() -> dict[str, str]:
    """Market symbol -> CME settlements product id, for every market that has one."""
    return {
        market.symbol: market.cme_key
        for market in COMMODITY_MARKETS.values()
        if market.cme_key
    }
