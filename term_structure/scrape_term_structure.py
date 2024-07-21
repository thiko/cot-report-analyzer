import logging
from datetime import datetime, timedelta

import pandas as pd
import requests

logger = logging.getLogger(__name__)

def get_last_business_day():
    today = datetime.now()
    offset = max(1, (today.weekday() + 6) % 7 - 3)
    last_business_day = today - timedelta(days=offset)
    return last_business_day.strftime("%m/%d/%Y")

def fetch_data():
    trade_date = get_last_business_day()
    timestamp = int(datetime.now().timestamp() * 1000)
    
    url = f"https://www.cmegroup.com/CmeWS/mvc/Settlements/Futures/Settlements/19/FUT?strategy=DEFAULT&tradeDate={trade_date}&pageSize=500&isProtected&_t={timestamp}"
    
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

def analyze_data(json_data):
    if not json_data or 'settlements' not in json_data:
        logger.info("No settlement data found in the response.")
        return

    # Convert to DataFrame
    df = pd.DataFrame(json_data['settlements'])
    
    # Remove the 'Total' row
    df = df[df['month'] != 'Total']

    # Convert Month to datetime and Settle to float
    df['Date'] = df['month'].apply(parse_custom_date)
    df['settle'] = df['settle'].astype(float)

    # Sort by date
    df = df.sort_values('Date')

    # Calculate the price difference between consecutive months
    df['Price_Diff'] = df['settle'].diff()

    # Analyze market structure
    overall_structure = "Contango" if df['Price_Diff'].iloc[1:].mean() > 0 else "Backwardation"
    near_term_structure = "Contango" if df['Price_Diff'].iloc[1:4].mean() > 0 else "Backwardation"
    long_term_structure = "Contango" if df['Price_Diff'].iloc[4:].mean() > 0 else "Backwardation"

    logger.info(df[['month', 'settle', 'Price_Diff']])
    logger.info(f"\nOverall market structure: {overall_structure}")
    logger.info(f"Near-term market structure (next 3 months): {near_term_structure}")
    logger.info(f"Long-term market structure (beyond 3 months): {long_term_structure}")

    # Detailed analysis
    logger.info("\nDetailed analysis:")
    if overall_structure != near_term_structure or overall_structure != long_term_structure:
        logger.info("The market shows a mixed structure:")
        logger.info(f"- Near-term (next 3 months): {near_term_structure}")
        logger.info(f"- Long-term (beyond 3 months): {long_term_structure}")
    else:
        logger.info(f"The market consistently shows {overall_structure} across all time frames.")


def main():
    json_data = fetch_data()
    if json_data:
        analyze_data(json_data)

if __name__ == "__main__":
    main()