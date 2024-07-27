CREATE TABLE IF NOT EXISTS commodity_term_structure (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        Market_Symbol TEXT,
        Report_Date DATE,
        Settlement_Date DATE,
        Settlement_Price REAL,
        UNIQUE(Market_Symbol, Report_Date, Settlement_Date))