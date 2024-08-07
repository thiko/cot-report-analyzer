CREATE TABLE IF NOT EXISTS cftc_reports_disag_fut(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        Market_Symbol TEXT,
        Market_and_Exchange_Names TEXT,
        Commodity_Name TEXT,
        Commodity_Category TEXT,
        Report_Date DATE,
        CFTC_Contract_Market_Code TEXT,
        CFTC_Market_Code TEXT,
        CFTC_Region_Code INTEGER,
        CFTC_Commodity_Code INTEGER,
        Open_Interest_All INTEGER,
        Prod_Merc_Positions_Long_All INTEGER,
        Prod_Merc_Positions_Short_All INTEGER,
        M_Money_Positions_Long_All INTEGER,
        M_Money_Positions_Short_All INTEGER,
        M_Money_Positions_Spread_All INTEGER,
        Other_Rept_Positions_Long_All INTEGER,
        Other_Rept_Positions_Short_All INTEGER,
        Other_Rept_Positions_Spread_All INTEGER,
        Open_Interest_Other INTEGER,
        Change_in_Open_Interest_All INTEGER,
        Change_in_Prod_Merc_Long_All INTEGER,
        Change_in_Prod_Merc_Short_All INTEGER,
        Change_in_Swap_Long_All INTEGER,
        Change_in_Swap_Short_All INTEGER,
        Change_in_Swap_Spread_All INTEGER,
        Change_in_M_Money_Long_All INTEGER,
        Change_in_M_Money_Short_All INTEGER,
        Change_in_M_Money_Spread_All INTEGER,
        Pct_of_OI_Prod_Merc_Long_All REAL,
        Pct_of_OI_Prod_Merc_Short_All REAL,
        Pct_of_OI_Swap_Long_All REAL,
        Pct_of_OI_Swap_Short_All REAL,
        Pct_of_OI_Swap_Spread_All REAL,
        Pct_of_OI_M_Money_Long_All REAL,
        Pct_of_OI_M_Money_Short_All REAL,
        Pct_of_OI_M_Money_Spread_All REAL,
        Pct_of_OI_Tot_Rept_Long_All REAL,
        Pct_of_OI_Tot_Rept_Short_All REAL,
        UNIQUE(Market_and_Exchange_Names, Report_Date))