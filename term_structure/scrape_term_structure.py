import logging
from datetime import datetime, timedelta
from random import randint
from sqlite3 import Connection
from time import sleep

import pandas as pd
import requests

from term_structure.market_symbol_cme_mapping import MarketSymbolCmeMapping

logger = logging.getLogger(__name__)

def get_last_business_day():
    today = datetime.now()
    offset = max(1, (today.weekday() + 6) % 7 - 3)
    last_business_day = today - timedelta(days=offset)
    return last_business_day.strftime("%m/%d/%Y")

def fetch_data(future_key: str):
    trade_date = get_last_business_day()
    timestamp = int(datetime.now().timestamp() * 1000)
    
    url = f"https://www.cmegroup.com/CmeWS/mvc/Settlements/Futures/Settlements/{future_key}/FUT?strategy=DEFAULT&tradeDate={trade_date}&pageSize=500&isProtected&_t={timestamp}"
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Accept': 'application/json, text/plain, */*',
        'Accept-Language': 'en-US,en;q=0.5',
        'Referer': 'https://www.cmegroup.com/markets/agriculture/livestock/lean-hogs.settlements.html',
        'Origin': 'https://www.cmegroup.com',
        'DNT': '1',
        'Connection': 'keep-alive',
        'Sec-Fetch-Dest': 'empty',
        'Sec-Fetch-Mode': 'cors',
        'Sec-Fetch-Site': 'same-origin',
        'Pragma': 'no-cache',
        'Cache-Control': 'no-cache',
    }

    response = requests.get(url, headers=headers)
    
    if response.status_code != 200:
        logger.info(f"Failed to fetch the data. Status code: {response.status_code}")
        return None

    return response.json()


def parse_custom_date(date_string):
    month_map = {
        'JAN': 1, 'FEB': 2, 'MAR': 3, 'APR': 4, 'MAY': 5, 'JUN': 6,
        'JLY': 7, 'AUG': 8, 'SEP': 9, 'OCT': 10, 'NOV': 11, 'DEC': 12
    }
    
    month, year = date_string.split()
    month_num = month_map[month]
    year_num = int('20' + year)
    
    return datetime(year_num, month_num, 1)

def parse_settle_price(settle_price: str):

    if settle_price is None:
        return None

    settle_price = settle_price.replace("'", ".")
    return float(settle_price)

def _insert_into_db(conn, market_symbol, data):
    cursor = conn.cursor()
    
    # Prepare the SQL statement
    sql = '''
    INSERT OR REPLACE INTO commodity_term_structure
    (Market_Symbol, Report_Date, Settlement_Date, Settlement_Price)
    VALUES (?, ?, ?, ?)
    '''
    
    # Get the report date (last business day)
    report_date = datetime.strptime(get_last_business_day(), "%m/%d/%Y").date()
    
    # Insert each row of data
    for _, row in data.iterrows():
        settlement_date = row['Date'].date()
        settlement_price = row['settle']
        #logger.info(f"Store term-structure for {market_symbol} report date: {settlement_date}")
        
        cursor.execute(sql, (market_symbol, report_date, settlement_date, settlement_price))
    
    # Commit the changes
    conn.commit()

def analyze_and_save_data(json_data, conn, market_symbol):
    if not json_data or 'settlements' not in json_data:
        logger.info("No settlement data found in the response.")
        return

    # Convert to DataFrame
    df = pd.DataFrame(json_data['settlements'])
    
    # Remove the 'Total' row
    df = df[df['month'] != 'Total']

    # Convert Month to datetime and Settle to float
    df['Date'] = df['month'].apply(parse_custom_date)
    df['settle'] = df['settle'].apply(parse_settle_price)

    # Sort by date
    df = df.sort_values('Date')

    # Insert data into the database
    _insert_into_db(conn, market_symbol, df)


def analyze_data_from_db(conn, market_symbol):
    cursor = conn.cursor()
    
    # Get the latest report date for the given market symbol
    cursor.execute('''
    SELECT MAX(Report_Date) FROM commodity_term_structure 
    WHERE Market_Symbol = ?
    ''', (market_symbol,))
    latest_report_date = cursor.fetchone()[0]
    
    if not latest_report_date:
        logger.info(f"No data found for {market_symbol}")
        return None  # Return None if no data is found
    
    # Fetch the data for the latest report date
    cursor.execute('''
    SELECT Settlement_Date, Settlement_Price 
    FROM commodity_term_structure 
    WHERE Market_Symbol = ? AND Report_Date = ?
    ORDER BY Settlement_Date
    ''', (market_symbol, latest_report_date))
    
    data = cursor.fetchall()
    
    # Convert to DataFrame
    df = pd.DataFrame(data, columns=['Date', 'Price'])
    
    # Calculate the price difference between consecutive months
    df['Price_Diff'] = df['Price'].diff()

    # Analyze market structure
    overall_structure = "Contango" if df['Price_Diff'].iloc[1:].mean() > 0 else "Backwardation"
    near_term_structure = "Contango" if df['Price_Diff'].iloc[1:4].mean() > 0 else "Backwardation"
    long_term_structure = "Contango" if df['Price_Diff'].iloc[4:].mean() > 0 else "Backwardation"

    # Prepare term structure data
    term_structure_data = [
        (date, f"{price:.2f}") 
        for date, price in zip(df['Date'], df['Price'])
    ]

    # Create the result dictionary
    result = {
        'Market_Symbol': market_symbol,
        'Report_Date': latest_report_date,
        'Short_Term_Structure': near_term_structure,
        'Long_Term_Structure': long_term_structure,
        'Overall_Term_Structure': overall_structure,
        'term_structure_data': term_structure_data
    }

    return result

def scrape_all_known_term_structures(conn):
    market_symbols = MarketSymbolCmeMapping()
    valid_commodities = {key: value for key, value in market_symbols.commodities.items() if value[0] and value[1]}
    
        # Get the report date (last business day)
    target_date = datetime.strptime(get_last_business_day(), "%m/%d/%Y").date()
    all_results = []
    
    for market_symbol, (future_key, url) in valid_commodities.items():
        cursor = conn.cursor()
        
        # Check if data for the current date already exists
        cursor.execute('''
        SELECT COUNT(*) FROM commodity_term_structure 
        WHERE Market_Symbol = ? AND Report_Date = ?
        ''', (market_symbol, target_date))
        
        count = cursor.fetchone()[0]
        
        if count == 0:
            logger.info(f"Did not found term structure data for {market_symbol} with report date: {target_date}. Going to scrape...")
            # Data for today doesn't exist, so scrape and save
            json_data = fetch_data(future_key)
            if json_data:
                analyze_and_save_data(json_data, conn, market_symbol)
            sleep(randint(1, 5))
        else:
            logger.info(f"Data for {market_symbol} on {target_date} already exists. Skipping scrape.")
        
        # Analyze data from the database and append to results
        result = analyze_data_from_db(conn, market_symbol)
        if result:
            all_results.append(result)
    
    return all_results
