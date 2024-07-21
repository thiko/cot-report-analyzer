import csv
import logging
import sqlite3
from datetime import datetime

from disaggregated_fut.commodity_data import CommodityData

# Table name
TABLE_NAME = 'cftc_reports_disag_fut'
logger = logging.getLogger(__name__)

# Insert data into the database
def insert_data(conn, data):
    cursor = conn.cursor()
    try:
        cursor.execute(f'''
        INSERT INTO {TABLE_NAME} (
            Market_and_Exchange_Names,
            Market_Symbol,
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
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', data)
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        # Skip if the entry already exists
        return False

# Process the CSV file
def process_csv(csv_file, db_conn: sqlite3.Connection):
    commodity_data = CommodityData()

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
            marketSymbol = commodity_data.get_market_symbol(cftc_code)
            category = commodity_data.get_commodity_category(cftc_code)

            data = (
                row['Market_and_Exchange_Names'], 
                marketSymbol, 
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
                logger.debug(f"Inserted data for {name} on {category}")
            else:
                logger.debug(f"Skipped existing data for {name} on {category}")


# Main execution
if __name__ == "__main__":
    csv_file_path = "2024_disaggregated_fut.csv"  # Replace with your actual file path
    process_csv(csv_file_path)