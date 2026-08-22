"""Declarative description of the CFTC COT report types we process.

Every report type ships the same seven identifying columns and then a set of
trader-category columns that differ per report. Describing those categories
declaratively keeps download, ingest, metrics and export generic.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class TraderGroup:
    """One trader category inside a COT report (e.g. "Managed Money")."""

    key: str
    label: str
    long_col: str
    short_col: str
    spread_col: str | None = None
    change_long_col: str | None = None
    change_short_col: str | None = None
    # Commercials hedge, speculators chase trends. A high net percentile is a
    # bullish signal for commercials and a crowding warning for speculators.
    stance: str = "speculator"  # "commercial" | "speculator" | "neutral"

    @property
    def columns(self) -> list[str]:
        cols = [self.long_col, self.short_col, self.spread_col,
                self.change_long_col, self.change_short_col]
        return [c for c in cols if c]


@dataclass(frozen=True)
class ReportSpec:
    """A CFTC report type: where to download it and how to read it."""

    key: str
    label: str
    short_label: str
    description: str
    archive_prefix: str
    member: str
    date_col: str
    oi_change_col: str
    universe: str  # "commodities" | "financials"
    groups: tuple[TraderGroup, ...]
    first_year: int = 2010

    @property
    def table(self) -> str:
        return f"cot_{self.key}"

    @property
    def value_columns(self) -> list[str]:
        cols = ["Open_Interest_All", self.oi_change_col]
        for group in self.groups:
            cols.extend(group.columns)
        return list(dict.fromkeys(cols))


ID_COLUMNS = [
    "Market_and_Exchange_Names",
    "CFTC_Contract_Market_Code",
    "CFTC_Market_Code",
    "CFTC_Region_Code",
    "CFTC_Commodity_Code",
]

_DISAGGREGATED_GROUPS = (
    TraderGroup("producer", "Producer / Merchant",
                "Prod_Merc_Positions_Long_All", "Prod_Merc_Positions_Short_All",
                change_long_col="Change_in_Prod_Merc_Long_All",
                change_short_col="Change_in_Prod_Merc_Short_All",
                stance="commercial"),
    TraderGroup("swap", "Swap Dealers",
                "Swap_Positions_Long_All", "Swap_Positions_Short_All",
                spread_col="Swap_Positions_Spread_All",
                change_long_col="Change_in_Swap_Long_All",
                change_short_col="Change_in_Swap_Short_All",
                stance="commercial"),
    TraderGroup("managed_money", "Managed Money",
                "M_Money_Positions_Long_All", "M_Money_Positions_Short_All",
                spread_col="M_Money_Positions_Spread_All",
                change_long_col="Change_in_M_Money_Long_All",
                change_short_col="Change_in_M_Money_Short_All",
                stance="speculator"),
    TraderGroup("other_reportable", "Other Reportable",
                "Other_Rept_Positions_Long_All", "Other_Rept_Positions_Short_All",
                spread_col="Other_Rept_Positions_Spread_All",
                change_long_col="Change_in_Other_Rept_Long_All",
                change_short_col="Change_in_Other_Rept_Short_All",
                stance="neutral"),
    TraderGroup("nonreportable", "Non-Reportable",
                "NonRept_Positions_Long_All", "NonRept_Positions_Short_All",
                change_long_col="Change_in_NonRept_Long_All",
                change_short_col="Change_in_NonRept_Short_All",
                stance="speculator"),
)

_LEGACY_GROUPS = (
    TraderGroup("commercial", "Commercial",
                "Commercial_Positions_Long_All", "Commercial_Positions_Short_All",
                change_long_col="Change_in_Commercial_Long_All",
                change_short_col="Change_in_Commercial_Short_All",
                stance="commercial"),
    TraderGroup("noncommercial", "Non-Commercial",
                "Noncommercial_Positions_Long_All", "Noncommercial_Positions_Short_All",
                spread_col="Noncommercial_Positions_Spreading_All",
                change_long_col="Change_in_Noncommercial_Long_All",
                change_short_col="Change_in_Noncommercial_Short_All",
                stance="speculator"),
    TraderGroup("nonreportable", "Non-Reportable",
                "Nonreportable_Positions_Long_All", "Nonreportable_Positions_Short_All",
                change_long_col="Change_in_Nonreportable_Long_All",
                change_short_col="Change_in_Nonreportable_Short_All",
                stance="speculator"),
)

_TFF_GROUPS = (
    TraderGroup("dealer", "Dealer / Intermediary",
                "Dealer_Positions_Long_All", "Dealer_Positions_Short_All",
                spread_col="Dealer_Positions_Spread_All",
                change_long_col="Change_in_Dealer_Long_All",
                change_short_col="Change_in_Dealer_Short_All",
                stance="commercial"),
    TraderGroup("asset_manager", "Asset Manager",
                "Asset_Mgr_Positions_Long_All", "Asset_Mgr_Positions_Short_All",
                spread_col="Asset_Mgr_Positions_Spread_All",
                change_long_col="Change_in_Asset_Mgr_Long_All",
                change_short_col="Change_in_Asset_Mgr_Short_All",
                stance="neutral"),
    TraderGroup("leveraged_money", "Leveraged Funds",
                "Lev_Money_Positions_Long_All", "Lev_Money_Positions_Short_All",
                spread_col="Lev_Money_Positions_Spread_All",
                change_long_col="Change_in_Lev_Money_Long_All",
                change_short_col="Change_in_Lev_Money_Short_All",
                stance="speculator"),
    TraderGroup("other_reportable", "Other Reportable",
                "Other_Rept_Positions_Long_All", "Other_Rept_Positions_Short_All",
                spread_col="Other_Rept_Positions_Spread_All",
                change_long_col="Change_in_Other_Rept_Long_All",
                change_short_col="Change_in_Other_Rept_Short_All",
                stance="neutral"),
    TraderGroup("nonreportable", "Non-Reportable",
                "NonRept_Positions_Long_All", "NonRept_Positions_Short_All",
                change_long_col="Change_in_NonRept_Long_All",
                change_short_col="Change_in_NonRept_Short_All",
                stance="speculator"),
)

_SUPPLEMENTAL_GROUPS = (
    TraderGroup("commercial", "Commercial (ex CIT)",
                "Comm_Positions_Long_All_NoCIT", "Comm_Positions_Short_All_NoCIT",
                change_long_col="Change_Comm_Long_All_NoCIT",
                change_short_col="Change_Comm_Short_All_NoCIT",
                stance="commercial"),
    TraderGroup("noncommercial", "Non-Commercial (ex CIT)",
                "NComm_Positions_Long_All_NoCIT", "NComm_Positions_Short_All_NoCIT",
                spread_col="NComm_Postions_Spread_All_NoCIT",
                change_long_col="Change_NonComm_Long_All_NoCIT",
                change_short_col="Change_NonComm_Short_All_NoCIT",
                stance="speculator"),
    TraderGroup("index_trader", "Index Traders (CIT)",
                "CIT_Positions_Long_All", "CIT_Positions_Short_All",
                change_long_col="Change_CIT_Long_All",
                change_short_col="Change_CIT_Short_All",
                stance="neutral"),
    TraderGroup("nonreportable", "Non-Reportable",
                "NonRept_Positions_Long_All", "NonRept_Positions_Short_All",
                change_long_col="Change_NonRept_Long_All",
                change_short_col="Change_NonRept_Short_All",
                stance="speculator"),
)

REPORTS: dict[str, ReportSpec] = {
    spec.key: spec
    for spec in (
        ReportSpec(
            key="disaggregated_fut",
            label="Disaggregated — Futures only",
            short_label="Disaggregated",
            description="Commodity positions split into producers, swap dealers, "
                        "managed money and other reportables. Futures only.",
            archive_prefix="fut_disagg_txt_",
            member="f_year.txt",
            date_col="Report_Date_as_YYYY_MM_DD",
            oi_change_col="Change_in_Open_Interest_All",
            universe="commodities",
            groups=_DISAGGREGATED_GROUPS,
        ),
        ReportSpec(
            key="disaggregated_futopt",
            label="Disaggregated — Futures & Options",
            short_label="Disaggregated F&O",
            description="Same breakdown as the futures-only disaggregated report, "
                        "but including options positions on a delta-adjusted basis.",
            archive_prefix="com_disagg_txt_",
            member="c_year.txt",
            date_col="Report_Date_as_YYYY_MM_DD",
            oi_change_col="Change_in_Open_Interest_All",
            universe="commodities",
            groups=_DISAGGREGATED_GROUPS,
        ),
        ReportSpec(
            key="legacy_fut",
            label="Legacy — Futures only",
            short_label="Legacy",
            description="The classic COT split into commercial, non-commercial and "
                        "non-reportable traders. Futures only.",
            archive_prefix="deacot",
            member="annual.txt",
            date_col="As_of_Date_in_Form_YYYY_MM_DD",
            oi_change_col="Change_in_Open_Interest_All",
            universe="commodities",
            groups=_LEGACY_GROUPS,
        ),
        ReportSpec(
            key="traders_in_financial_futures_fut",
            label="Traders in Financial Futures",
            short_label="Financials",
            description="Rates, currencies, equity indices and crypto split into "
                        "dealers, asset managers and leveraged funds. Futures only.",
            archive_prefix="fut_fin_txt_",
            member="FinFutYY.txt",
            date_col="Report_Date_as_YYYY_MM_DD",
            oi_change_col="Change_in_Open_Interest_All",
            universe="financials",
            groups=_TFF_GROUPS,
        ),
        ReportSpec(
            key="supplemental_futopt",
            label="Supplemental — Index Traders",
            short_label="Supplemental",
            description="Thirteen agricultural markets with commodity index traders "
                        "broken out separately. Futures and options.",
            archive_prefix="dea_cit_txt_",
            member="annualci.txt",
            date_col="As_of_Date_In_Form_YYYY_MM_DD",
            oi_change_col="Change_Open_Interest_All",
            universe="commodities",
            groups=_SUPPLEMENTAL_GROUPS,
        ),
    )
}
