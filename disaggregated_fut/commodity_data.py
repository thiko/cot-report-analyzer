class CommodityData:
    def __init__(self):
        self.commodities = {
            1: ("Wheat", "ZW", "Grains", lambda row: row['CFTC_Market_Code'].lower() == "cbt" and row['Market_and_Exchange_Names'] == "WHEAT-SRW - CHICAGO BOARD OF TRADE"),
            2: ("Corn", "ZC", "Grains", lambda row: row['CFTC_Market_Code'].lower() == "cbt"),
            4: ("Oats", "ZO", "Grains", lambda row: row['CFTC_Market_Code'].lower() == "cbt"),
            5: ("Soybeans", "ZS", "Grains", lambda row: row['CFTC_Market_Code'].lower() == "cbt"),
            6: ("Low Carbon Energy", "CLEX", "Energy", lambda row: row['CFTC_Market_Code'].lower() == "nyme" and row['Market_and_Exchange_Names'] == "CBL NATURE GLOBAL EMISSIONS - NEW YORK MERCANTILE EXCHANGE"), # CBL NATURE GLOBAL EMISSIONS - NEW YORK MERCANTILE EXCHANGE
            7: ("Soybean Oil", "ZL", "Grains", lambda row: row['CFTC_Market_Code'].lower() == "cbt"),
            21: ("Fuel Oil", "FO", "Energy", lambda row: row['CFTC_Market_Code'].lower() == "nyme"),
            22: ("ULSD NY Harbor", "HO", "Energy", lambda row: row['CFTC_Market_Code'].lower() == "nyme" and row['Market_and_Exchange_Names'] == "NY HARBOR ULSD - NEW YORK MERCANTILE EXCHANGE"),
            23: ("Natural Gas", "NG", "Energy", lambda row: row['CFTC_Market_Code'].lower() == "nyme" and row['Market_and_Exchange_Names'] == "NAT GAS NYME - NEW YORK MERCANTILE EXCHANGE"),
            25: ("Ethanol", "EH", "Energy", lambda row: row['CFTC_Market_Code'].lower() == "nyme" and row['Market_and_Exchange_Names'] == "ETHANOL - NEW YORK MERCANTILE EXCHANGE"), # ETHANOL - NEW YORK MERCANTILE EXCHANGE
            26: ("Soybean Meal", "ZM", "Grains", lambda row: row['CFTC_Market_Code'].lower() == "cbt"),
            33: ("Cotton", "CT", "Soft", lambda row: row['CFTC_Market_Code'].lower() == "icus"),
            37: ("Palm Oil", "PO", "Soft", lambda row: row['CFTC_Market_Code'].lower() == "cme"),
            39: ("Rough Rice", "ZR", "Grains", lambda row: row['CFTC_Market_Code'].lower() == "cbt"),
            40: ("Orange Juice", "OJ", "Soft", lambda row: row['CFTC_Market_Code'].lower() == "icus"),
            50: ("Butter", "CBQ", "Soft", lambda row: row['CFTC_Market_Code'].lower() == "cme"),
            52: ("Milk", "DCQ", "Soft", lambda row: row['CFTC_Market_Code'].lower() == "cme" and row['CFTC_Contract_Market_Code'] == "052641"), # MILK, Class III - CHICAGO MERCANTILE EXCHANGE
            54: ("Lean Hogs", "HE", "Meats", lambda row: row['CFTC_Market_Code'].lower() == "cme"),
            57: ("Live Cattle", "LE", "Meats", lambda row: row['CFTC_Market_Code'].lower() == "cme"),
            58: ("Lumber", "LBR", "Soft", lambda row: row['CFTC_Market_Code'].lower() == "cme"),
            61: ("Feeder Cattle", "GFV", "Meats", lambda row: row['CFTC_Market_Code'].lower() == "cme"),
            63: ("Dry Whey", "DYQ", "Grains", lambda row: row['CFTC_Market_Code'].lower() == "cbt"),
            64: ("Electricity", "EW", "Energy", lambda row: row['CFTC_Market_Code'].lower() == "nyme"),
            66: ("Propane Gas", "PG", "Energy", lambda row: row['CFTC_Market_Code'].lower() == "nyme" and row['Market_and_Exchange_Names'] == "DONT KNOW WHICH ONE"), # weglassen? kennt barchart nicht
            67: ("Crude Oil", "CL", "Energy", lambda row: row['CFTC_Market_Code'].lower() == "nyme" and row['Market_and_Exchange_Names'] == "WTI-PHYSICAL - NEW YORK MERCANTILE EXCHANGE"),
            73: ("Cocoa", "CC", "Soft", lambda row: row['CFTC_Market_Code'].lower() == "icus"),
            75: ("Palladium", "PA", "Metal", lambda row: row['CFTC_Market_Code'].lower() == "nyme"),
            76: ("Platinum", "PL", "Metal", lambda row: row['CFTC_Market_Code'].lower() == "nyme"),
            80: ("Sugar No. 11", "SB", "Soft", lambda row: row['CFTC_Market_Code'].lower() == "icus"),
            83: ("Coffee C", "KC", "Soft", lambda row: row['CFTC_Market_Code'].lower() == "icus"),
            84: ("Silver", "SI", "Metal", lambda row: row['CFTC_Market_Code'].lower() == "cmx"),
            85: ("Copper", "HG", "Metal", lambda row: row['CFTC_Market_Code'].lower() == "cmx"),
            88: ("Gold", "GC", "Metal", lambda row: row['CFTC_Market_Code'].lower() == "cmx" and row['Market_and_Exchange_Names'] == "GOLD - COMMODITY EXCHANGE INC."), # GOLD - COMMODITY EXCHANGE INC.
            111: ("Gasoline", "RB", "Energy", lambda row: row['CFTC_Market_Code'].lower() == "nyme" and row['Market_and_Exchange_Names'] == "GASOLINE RBOB - NEW YORK MERCANTILE EXCHANGE"),
            135: ("Canola", "RS", "Grains", lambda row: row['CFTC_Market_Code'].lower() == "nyme"),
            188: ("Cobalt", "CB", "Metal", lambda row: row['CFTC_Market_Code'].lower() == "cmx"),
            189: ("Lithium", "LTH", "Metal", lambda row: row['CFTC_Market_Code'].lower() == "cmx"),
            191: ("Aluminium", "ALI", "Metal", lambda row: row['CFTC_Market_Code'].lower() == "cmx" and row['Market_and_Exchange_Names'] == "ALUMINUM MWP - COMMODITY EXCHANGE INC."),
            192: ("Steel HRC", "HRC", "Metal", lambda row: row['CFTC_Market_Code'].lower() == "cmx" and row['Market_and_Exchange_Names'] == "STEEL-HRC - COMMODITY EXCHANGE INC."),
            257: ("Steel Scrap", "SSC", "Metal", lambda row: row['CFTC_Market_Code'].lower() == "cmx"), # TODO: Check specific conditions
            864: ("Unknown", "UNK", "Energy", lambda row: row['CFTC_Market_Code'].lower() == "nyme" and row['Market_and_Exchange_Names'] == "PLACEHOLDER"),
            865: ("Fuel Oil Crack", "FOC", "Energy", lambda row: row['CFTC_Market_Code'].lower() == "nyme")
        }

    def get_commodity_name(self, cftc_code):
        """
        Get the commodity name for a given CFTC Commodity Code.
        
        :param cftc_code: int, CFTC Commodity Code
        :return: str, Commodity Name or None if not found
        """
        commodity = self.commodities.get(cftc_code)
        return commodity[0] if commodity else None
    
    def get_market_symbol(self, cftc_code):
        """
        Get the market symbol for a given CFTC Commodity Code.
        
        :param cftc_code: int, CFTC Commodity Code
        :return: str, Market Symbol or None if not found
        """
        commodity = self.commodities.get(cftc_code)
        return commodity[1] if commodity else None


    def get_commodity_category(self, cftc_code):
        """
        Get the commodity category for a given CFTC Commodity Code.
        
        :param cftc_code: int, CFTC Commodity Code
        :return: str, Commodity Category or None if not found
        """
        commodity = self.commodities.get(cftc_code)
        return commodity[2] if commodity else None

    def is_commodity_allowed(self, row):
        """
        Check if the commodity is allowed based on the lambda condition.
        :param row: list, CSV row data
        :return: bool, True if allowed, False otherwise
        """
        cftc_code = int(row['CFTC_Commodity_Code'])
        commodity = self.commodities.get(cftc_code)
        return commodity[3](row) if commodity else False