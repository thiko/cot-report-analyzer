class MarketSymbolCmeMapping:
    def __init__(self):
        self.commodities = {
            "ZW": ("323", "https://www.cmegroup.com/markets/agriculture/grains/wheat.settlements.html"),
            "ZC": ("300", "https://www.cmegroup.com/markets/agriculture/grains/corn.settlements.html"),
            "ZO": ("331", "https://www.cmegroup.com/markets/agriculture/grains/oats.settlements.html"),
            "ZS": ("320", "https://www.cmegroup.com/markets/agriculture/oilseeds/soybean.settlements.html"),
            "CLEX": (None, None),
            "ZL": ("312", "https://www.cmegroup.com/markets/agriculture/oilseeds/soybean-oil.settlements.html"),
            "FO": (None, None),
            "HO": ("426", "https://www.cmegroup.com/markets/energy/refined-products/heating-oil.settlements.html"),
            "NG": ("444", "https://www.cmegroup.com/markets/energy/natural-gas/natural-gas.settlements.html"),
            "EH": ("338", "https://www.cmegroup.com/markets/energy/biofuels/cbot-ethanol.settlements.html"),
            "ZM": ("310", "https://www.cmegroup.com/markets/agriculture/oilseeds/soybean-meal.settlements.html"),
            "CT": ("460", "https://www.cmegroup.com/markets/agriculture/lumber-and-softs/cotton.settlements.html"),
            "PO": ("2457", "https://www.cmegroup.com/markets/agriculture/oilseeds/usd-malaysian-crude-palm-oil-calendar.settlements.html"),
            "ZR": ("336", "https://www.cmegroup.com/markets/agriculture/grains/rough-rice.settlements.html"),
            "OJ": (None, None),
            "CBQ": ("26", "https://www.cmegroup.com/markets/agriculture/dairy/cash-settled-butter.settlements.html"),
            "DCQ": ("27", "https://www.cmegroup.com/markets/agriculture/dairy/class-iii-milk.settlements.html"),
            "HE": ("19", "https://www.cmegroup.com/markets/agriculture/livestock/lean-hogs.contractSpecs.html"),
            "LE": ("22", "https://www.cmegroup.com/markets/agriculture/livestock/live-cattle.settlements.html"),
            "LBR": ("10191", "https://www.cmegroup.com/markets/agriculture/lumber-and-softs/lumber.settlements.html"),
            "GFV": ("34", "https://www.cmegroup.com/markets/agriculture/livestock/feeder-cattle.settlements.html"),
            "DYQ": ("36", "https://www.cmegroup.com/markets/agriculture/dairy/dry-whey.settlements.html"),
            "EW": (None, None),
            "PG": (None, None),
            "CL": ("425", "https://www.cmegroup.com/markets/energy/crude-oil/light-sweet-crude.settlements.html"),
            "CJ": ("423", "https://www.cmegroup.com/markets/agriculture/lumber-and-softs/cocoa.settlements.html"),
            "PA": ("445", "https://www.cmegroup.com/markets/metals/precious/palladium.settlements.html"),
            "PL": ("446", "https://www.cmegroup.com/markets/metals/precious/platinum.settlements.html"),
            "SB": ("470", "https://www.cmegroup.com/markets/agriculture/lumber-and-softs/sugar-no11.settlements.html"),
            "KC": ("440", "https://www.cmegroup.com/markets/agriculture/lumber-and-softs/coffee.settlements.html"),
            "SI": ("458", "https://www.cmegroup.com/markets/metals/precious/silver.settlements.html"),
            "HG": ("438", "https://www.cmegroup.com/markets/metals/base/copper.settlements.html"),
            "GC": ("437", "https://www.cmegroup.com/markets/metals/precious/gold.settlements.html"),
            "RB": ("429", "https://www.cmegroup.com/markets/energy/refined-products/rbob-gasoline.settlements.html"),
            "RS": (None, None),
            "CB": (None, None),
            "LTH": (None, None),
            "ALI": ("7440", "https://www.cmegroup.com/markets/metals/base/aluminum.settlements.html"),
            "HRC": ("487", "https://www.cmegroup.com/markets/metals/base/steel.settlements.html"),
            "SSC": ("2508", "https://www.cmegroup.com/markets/metals/ferrous/hrc-steel.settlements.html"),
            "UNK": (None, None),
            "FOC": (None, None),
        }

    def get_cboe_api_commodity_code(self, symbol):
        """
        Get the commodity name for a given CFTC Commodity Code.
        
        :param cftc_code: int, CFTC Commodity Code
        :return: str, Commodity Name or None if not found
        """
        commodity = self.commodities.get(symbol)
        return commodity[0] if commodity else None