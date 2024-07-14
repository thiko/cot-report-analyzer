class CommodityData:
    def __init__(self):
        self.commodities = {
            1: ("Wheat", "Grains", lambda row: row['CFTC_Market_Code'].lower() == "cbt" and row['Market_and_Exchange_Names'] == "WHEAT-SRW - CHICAGO BOARD OF TRADE"), 
            2: ("Corn", "Grains", lambda row: row['CFTC_Market_Code'].lower() == "cbt"),
            4: ("Oats", "Grains", lambda row: row['CFTC_Market_Code'].lower() == "cbt"),
            5: ("Soybeans", "Grains", lambda row: row['CFTC_Market_Code'].lower() == "cbt"),
            6: ("Low Carbon Energy", "Energy", lambda row: row['CFTC_Market_Code'].lower() == "nyme" and row['Market_and_Exchange_Names'] == "CBL NATURE GLOBAL EMISSIONS - NEW YORK MERCANTILE EXCHANGE"), # CBL NATURE GLOBAL EMISSIONS - NEW YORK MERCANTILE EXCHANGE
            7: ("Soybean Oil", "Grains", lambda row: row['CFTC_Market_Code'].lower() == "cbt"),
            21: ("Fuel Oil", "Energy", lambda row: row['CFTC_Market_Code'].lower() == "nyme"),
            22: ("ULSD NY Harbor", "Energy", lambda row: row['CFTC_Market_Code'].lower() == "nyme" and row['Market_and_Exchange_Names'] == "NY HARBOR ULSD - NEW YORK MERCANTILE EXCHANGE"),
            23: ("Natural Gas", "Energy", lambda row: row['CFTC_Market_Code'].lower() == "nyme" and row['Market_and_Exchange_Names'] == "NAT GAS NYME - NEW YORK MERCANTILE EXCHANGE"), #  NAT GAS NYME - NEW YORK MERCANTILE EXCHANGE
            25: ("Ethanol", "Energy", lambda row: row['CFTC_Market_Code'].lower() == "nyme" and row['Market_and_Exchange_Names'] == "ETHANOL - NEW YORK MERCANTILE EXCHANGE"), # ETHANOL - NEW YORK MERCANTILE EXCHANGE
            26: ("Soybean Meal", "Grains", lambda row: row['CFTC_Market_Code'].lower() == "cbt"),
            33: ("Cotton", "Soft", lambda row: row['CFTC_Market_Code'].lower() == "icus"),
            37: ("Palm Oil", "Soft", lambda row: row['CFTC_Market_Code'].lower() == "cme"),
            39: ("Rough Rice", "Grains", lambda row: row['CFTC_Market_Code'].lower() == "cbt"),
            40: ("Orange Juice", "Soft", lambda row: row['CFTC_Market_Code'].lower() == "icus"),
            50: ("Butter", "Soft", lambda row: row['CFTC_Market_Code'].lower() == "cme"),
            52: ("Milk", "Soft", lambda row: row['CFTC_Market_Code'].lower() == "cme" and row['CFTC_Contract_Market_Code'] == "052641"), #MILK, Class III - CHICAGO MERCANTILE EXCHANGE
            54: ("Lean Hogs", "Meats", lambda row: row['CFTC_Market_Code'].lower() == "cme"),
            57: ("Live Cattle", "Meats", lambda row: row['CFTC_Market_Code'].lower() == "cme"),
            58: ("Lumber", "Soft", lambda row: row['CFTC_Market_Code'].lower() == "cme"),
            61: ("Feeder Cattle", "Meats", lambda row: row['CFTC_Market_Code'].lower() == "cme"),
            63: ("Dry Whey", "Grains", lambda row: row['CFTC_Market_Code'].lower() == "cbt"),
            64: ("Electricity", "Energy", lambda row: row['CFTC_Market_Code'].lower() == "nyme"),
            66: ("Propane Gas", "Energy", lambda row: row['CFTC_Market_Code'].lower() == "nyme" and row['Market_and_Exchange_Names'] == "DONT KNOW WHICH ONE"), # weglassen? kennt barchart nicht
            67: ("Crude Oil", "Energy", lambda row: row['CFTC_Market_Code'].lower() == "nyme" and row['Market_and_Exchange_Names'] == "WTI-PHYSICAL - NEW YORK MERCANTILE EXCHANGE"),
            73: ("Cocoa", "Soft", lambda row: row['CFTC_Market_Code'].lower() == "icus"),
            75: ("Palladium", "Metal", lambda row: row['CFTC_Market_Code'].lower() == "nyme"),
            76: ("Platinum", "Metal", lambda row: row['CFTC_Market_Code'].lower() == "nyme"),
            80: ("Sugar", "Soft", lambda row: row['CFTC_Market_Code'].lower() == "icus"),
            83: ("Coffee", "Soft", lambda row: row['CFTC_Market_Code'].lower() == "icus"),
            84: ("Silver", "Metal", lambda row: row['CFTC_Market_Code'].lower() == "cmx"),
            85: ("Copper", "Metal", lambda row: row['CFTC_Market_Code'].lower() == "cmx"),
            88: ("Gold", "Metal", lambda row: row['CFTC_Market_Code'].lower() == "cmx" and row['Market_and_Exchange_Names'] == "GOLD - COMMODITY EXCHANGE INC."), #GOLD - COMMODITY EXCHANGE INC.
            111: ("Gasoline", "Energy", lambda row: row['CFTC_Market_Code'].lower() == "nyme" and row['Market_and_Exchange_Names'] == "GASOLINE RBOB - NEW YORK MERCANTILE EXCHANGE"),
            135: ("Canola", "Grains", lambda row: row['CFTC_Market_Code'].lower() == "nyme"),
            188: ("Cobalt", "Metal", lambda row: row['CFTC_Market_Code'].lower() == "cmx"),
            189: ("Lithium", "Metal", lambda row: row['CFTC_Market_Code'].lower() == "cmx"),
            191: ("Aluminium", "Metal", lambda row: row['CFTC_Market_Code'].lower() == "cmx" and row['Market_and_Exchange_Names'] == "ALUMINUM MWP - COMMODITY EXCHANGE INC."),
            192: ("Steel", "Metal", lambda row: row['CFTC_Market_Code'].lower() == "cmx" and row['Market_and_Exchange_Names'] == "STEEL-HRC - COMMODITY EXCHANGE INC."),
            257: ("Steel Scrap", "Metal", lambda row: row['CFTC_Market_Code'].lower() == "cmx"),  # TODO: Check specific conditions
            864: ("Unknown", "Energy", lambda row: row['CFTC_Market_Code'].lower() == "nyme" and row['Market_and_Exchange_Names'] == "PLACEHOLDER"),
            865: ("Fuel Oil Crack", "Energy", lambda row: row['CFTC_Market_Code'].lower() == "nyme")        
        }

    def get_commodity_name(self, cftc_code):
        """
        Get the commodity name for a given CFTC Commodity Code.
        
        :param cftc_code: int, CFTC Commodity Code
        :return: str, Commodity Name or None if not found
        """
        commodity = self.commodities.get(cftc_code)
        return commodity[0] if commodity else None


    def get_commodity_category(self, cftc_code):
        """
        Get the commodity category for a given CFTC Commodity Code.
        
        :param cftc_code: int, CFTC Commodity Code
        :return: str, Commodity Category or None if not found
        """
        commodity = self.commodities.get(cftc_code)
        return commodity[1] if commodity else None

    def is_commodity_allowed(self, row):
        """
        Check if the commodity is allowed based on the lambda condition.
        :param row: list, CSV row data
        :return: bool, True if allowed, False otherwise
        """
        cftc_code = int(row['CFTC_Commodity_Code'])
        commodity = self.commodities.get(cftc_code)
        return commodity[2](row) if commodity else False