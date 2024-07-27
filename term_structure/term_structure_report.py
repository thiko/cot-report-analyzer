import base64
import io
import logging
import sqlite3
from datetime import datetime

import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import pandas as pd

logger = logging.getLogger(__name__)

# Function to generate diagram for a Market_Symbol
def generate_diagram(conn: sqlite3.Connection, market_symbol: str):    
    
    query = f"""
    SELECT Settlement_Date, Settlement_Price
    FROM commodity_term_structure
    WHERE Market_Symbol = '{market_symbol}'
    AND Report_Date = (SELECT MAX(Report_Date) FROM commodity_term_structure WHERE Market_Symbol = '{market_symbol}')
    ORDER BY Settlement_Date asc
    limit 12
    """
    df = pd.read_sql_query(query, conn)
    
    if df.empty:
        logger.info(f"No data found for {market_symbol}")
        return None
    
    df['Settlement_Date'] = pd.to_datetime(df['Settlement_Date'])
    
    # Debug information
    logger.debug(f"Total data points for {market_symbol}: {len(df)}")
    logger.debug(f"Date range: {df['Settlement_Date'].min()} to {df['Settlement_Date'].max()}")
    
    plt.figure(figsize=(12, 6))
    ax = plt.gca()
    
    # Plot the main line using all data
    plt.plot(df['Settlement_Date'], df['Settlement_Price'], color='darkblue')
    
    # Add vertical lines for each month in the data
    for date in df['Settlement_Date']:
        plt.axvline(x=date, color='gray', linestyle='--', alpha=0.3)
    
    plt.title(f'Term Structure for {market_symbol}')
    plt.xlabel('Settlement Date')
    plt.ylabel('Settlement Price')
    
    # Format x-axis to show month/year
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%m/%Y'))
    ax.xaxis.set_major_locator(mdates.MonthLocator(interval=1))  # Show every month
    
    plt.xticks(rotation=45)
    plt.grid(True, axis='y', linestyle='--', alpha=0.7)
    plt.tight_layout()
    
    buffer = io.BytesIO()
    plt.savefig(buffer, format='png', dpi=100)
    buffer.seek(0)
    image_base64 = base64.b64encode(buffer.getvalue()).decode()
    plt.close()

    return image_base64
