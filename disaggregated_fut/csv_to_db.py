import csv
import sqlite3
from datetime import datetime

from disaggregated_fut.commodity_data import CommodityData

# Database file name
DB_FILE = 'cftc_data.db'

# Table name
TABLE_NAME = 'cftc_reports_disag_fut'

# Create the database schema
def create_schema(conn):
    cursor = conn.cursor()
    cursor.execute(f'''
    CREATE TABLE IF NOT EXISTS {TABLE_NAME} (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
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
        UNIQUE(Market_and_Exchange_Names, Report_Date)
    )
    ''')
    conn.commit()

# Insert data into the database
def insert_data(conn, data):
    cursor = conn.cursor()
    try:
        cursor.execute(f'''
        INSERT INTO {TABLE_NAME} (
            Market_and_Exchange_Names, 
            Commodity_Name, 
            Commodity_Category, 
            Report_Date,
            CFTC_Contract_Market_Code, 
            CFTC_Market_Code, 
            CFTC_Region_Code, 
            CFTC_Commodity_Code,
            Open_Interest_All, 
            Prod_Merc_Positions_Long_All, 
            Prod_Merc_Positions_Short_All,
            M_Money_Positions_Long_All, 
            M_Money_Positions_Short_All, 
            M_Money_Positions_Spread_All,
            Other_Rept_Positions_Long_All, 
            Other_Rept_Positions_Short_All, 
            Other_Rept_Positions_Spread_All,
            Open_Interest_Other, 
            Change_in_Open_Interest_All, 
            Change_in_Prod_Merc_Long_All,
            Change_in_Prod_Merc_Short_All, 
            Change_in_Swap_Long_All, 
            Change_in_Swap_Short_All,
            Change_in_Swap_Spread_All, 
            Change_in_M_Money_Long_All, 
            Change_in_M_Money_Short_All,
            Change_in_M_Money_Spread_All, 
            Pct_of_OI_Prod_Merc_Long_All, 
            Pct_of_OI_Prod_Merc_Short_All,
            Pct_of_OI_Swap_Long_All, 
            Pct_of_OI_Swap_Short_All, 
            Pct_of_OI_Swap_Spread_All,
            Pct_of_OI_M_Money_Long_All, 
            Pct_of_OI_M_Money_Short_All, 
            Pct_of_OI_M_Money_Spread_All,
            Pct_of_OI_Tot_Rept_Long_All, 
            Pct_of_OI_Tot_Rept_Short_All
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', data)
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        # Skip if the entry already exists
        return False

# Process the CSV file
def process_csv(csv_file, db_conn: sqlite3.Connection):
    commodity_data = CommodityData()
    create_schema(db_conn)

    with open(csv_file, 'r') as csvfile:
        #csv_reader = csv.reader(csvfile)
        csv_reader = csv.DictReader(csvfile)
        #next(csv_reader)  # Skip header row

        for row in csv_reader:
            
            row = {key: value.strip() if value is not None else value for key, value in row.items()}
            if not commodity_data.is_commodity_allowed(row):
                continue

            cftc_code = int(row['CFTC_Commodity_Code'])
            name = commodity_data.get_commodity_name(cftc_code)
            category = commodity_data.get_commodity_category(cftc_code)

            data = (
                row['Market_and_Exchange_Names'], 
                name, 
                category,  
                row['Report_Date_as_YYYY-MM-DD'], 
                row['CFTC_Contract_Market_Code'], 
                row['CFTC_Market_Code'], 
                row['CFTC_Region_Code'], 
                row['CFTC_Commodity_Code'],
                row['Open_Interest_All'], 
                row['Prod_Merc_Positions_Long_All'], 
                row['Prod_Merc_Positions_Short_All'], 
                row['M_Money_Positions_Long_All'], 
                row['M_Money_Positions_Short_All'],
                row['M_Money_Positions_Spread_All'], 
                row['Other_Rept_Positions_Long_All'], 
                row['Other_Rept_Positions_Short_All'], 
                row['Other_Rept_Positions_Spread_All'], 
                row['Open_Interest_Other'], 
                row['Change_in_Open_Interest_All'], 
                row['Change_in_Prod_Merc_Long_All'], 
                row['Change_in_Prod_Merc_Short_All'],
                row['Change_in_Swap_Long_All'], 
                row['Change_in_Swap_Short_All'], 
                row['Change_in_Swap_Spread_All'], 
                row['Change_in_M_Money_Long_All'], 
                row['Change_in_M_Money_Short_All'], 
                row['Change_in_M_Money_Spread_All'], 
                row['Pct_of_OI_Prod_Merc_Long_All'], 
                row['Pct_of_OI_Prod_Merc_Short_All'],
                row['Pct_of_OI_Swap_Long_All'], 
                row['Pct_of_OI_Swap_Short_All'], 
                row['Pct_of_OI_Swap_Spread_All'], 
                row['Pct_of_OI_M_Money_Long_All'], 
                row['Pct_of_OI_M_Money_Short_All'], 
                row['Pct_of_OI_M_Money_Spread_All'], 
                row['Pct_of_OI_Tot_Rept_Long_All'],
                row['Pct_of_OI_Tot_Rept_Short_All']
            )

            if insert_data(db_conn, data):
                print(f"Inserted data for {name} on {category}")
            else:
                print(f"Skipped existing data for {name} on {category}")


# Main execution
if __name__ == "__main__":
    csv_file_path = "2024_disaggregated_fut.csv"  # Replace with your actual file path
    process_csv(csv_file_path)