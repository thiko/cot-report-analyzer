import bisect
import logging
import sqlite3
from datetime import datetime, timedelta

import numpy as np
import pandas as pd
from jinja2 import Environment, FileSystemLoader

from term_structure.scrape_term_structure import analyze_data_from_db
from term_structure.term_structure_report import generate_diagram

logger = logging.getLogger(__name__)

# Function to calculate percentiles
def calculate_percentile(data, current_value):
    clean_data = [float(x) for x in data if x is not None and x != 'N/A']
    if not clean_data or current_value is None or current_value == 'N/A':
        return 'N/A'
    sorted_data = sorted(clean_data)
    current_value = float(current_value)
    position = bisect.bisect_left(sorted_data, current_value)
    percentile = (position / len(sorted_data)) * 100
    return round(percentile)

# Function to get historical data and calculate percentiles
def get_historical_data_and_percentiles(conn, commodity_code, column_type, current_date):
    end_date = current_date
    start_date_25w = end_date - timedelta(weeks=25)
    start_date_52w = end_date - timedelta(weeks=52)
    start_date_3yr = end_date - timedelta(weeks=156)

    query = f"""
    SELECT Report_Date, 
           SUM(CASE 
               WHEN ? = 'Producer' THEN Prod_Merc_Positions_Long_All - Prod_Merc_Positions_Short_All
               WHEN ? = 'Money_Manager' THEN M_Money_Positions_Long_All - M_Money_Positions_Short_All
               WHEN ? = 'Total' THEN (Prod_Merc_Positions_Long_All - Prod_Merc_Positions_Short_All) + (M_Money_Positions_Long_All - M_Money_Positions_Short_All)
               WHEN ? = 'Gap' THEN (M_Money_Positions_Long_All - M_Money_Positions_Short_All) - (Prod_Merc_Positions_Long_All - Prod_Merc_Positions_Short_All)          
           END) AS Net_Position
    FROM cftc_reports_disag_fut
    WHERE CFTC_Commodity_Code = ? AND Report_Date BETWEEN ? AND ?
    GROUP BY Report_Date
    ORDER BY Report_Date
    """
    
    df_25w = pd.read_sql_query(query, conn, params=(column_type, column_type, column_type, column_type, commodity_code, start_date_25w, end_date))
    df_52w = pd.read_sql_query(query, conn, params=(column_type, column_type, column_type, column_type, commodity_code, start_date_52w, end_date))
    df_3yr = pd.read_sql_query(query, conn, params=(column_type, column_type, column_type, column_type, commodity_code, start_date_3yr, end_date))

    current_value = df_25w['Net_Position'].iloc[-1] if not df_25w.empty else 'N/A'
    
    percentile_25w = calculate_percentile(df_25w['Net_Position'].tolist(), current_value)
    percentile_52w = calculate_percentile(df_52w['Net_Position'].tolist(), current_value)
    percentile_3yr = calculate_percentile(df_3yr['Net_Position'].tolist(), current_value)

    return current_value, percentile_25w, percentile_52w, percentile_3yr

def generate_report(db_connection: sqlite3.Connection, report_output_dir: str, date_str: str = None): 

    # Get the most recent date in the database
    latest_date_string = date_str
    
    if date_str is None:
        latest_date_string = pd.read_sql_query("SELECT MAX(Report_Date) as max_date FROM cftc_reports_disag_fut", db_connection).iloc[0]['max_date']
    
    latest_date = datetime.strptime(latest_date_string, '%Y-%m-%d')

    logger.info(f'last date: {latest_date}')

    # Query to get the main data
    query = """
    SELECT 
        Commodity_Name,
        Market_Symbol,
        Commodity_Category,
        CFTC_Commodity_Code,
        SUM(Open_Interest_All) as Open_Interest_All,
        SUM(Prod_Merc_Positions_Long_All) as Prod_Merc_Positions_Long_All,
        SUM(Prod_Merc_Positions_Short_All) as Prod_Merc_Positions_Short_All,
        SUM(M_Money_Positions_Long_All) as M_Money_Positions_Long_All,
        SUM(M_Money_Positions_Short_All) as M_Money_Positions_Short_All,
        SUM(Change_in_Open_Interest_All) as Change_in_Open_Interest_All,
        SUM(Change_in_Prod_Merc_Long_All) as Change_in_Prod_Merc_Long_All,
        SUM(Change_in_Prod_Merc_Short_All) as Change_in_Prod_Merc_Short_All,
        SUM(Change_in_M_Money_Long_All) as Change_in_M_Money_Long_All,
        SUM(Change_in_M_Money_Short_All) as Change_in_M_Money_Short_All
    FROM cftc_reports_disag_fut
    WHERE Report_Date = ?
    GROUP BY CFTC_Commodity_Code
    ORDER BY Commodity_Category, Commodity_Name
    """

    df = pd.read_sql_query(query, db_connection, params=(latest_date_string,))
    logger.info(f'dataframe size: {df.size}')

    # Calculate additional columns
    df['Producer_Net'] = df['Prod_Merc_Positions_Long_All'] - df['Prod_Merc_Positions_Short_All']
    df['Change_Producer_Net'] = df['Change_in_Prod_Merc_Long_All'] - df['Change_in_Prod_Merc_Short_All']

    df['Money_Manager_Net'] = df['M_Money_Positions_Long_All'] - df['M_Money_Positions_Short_All']
    df['Change_Money_Manager_Net'] = df['Change_in_M_Money_Long_All'] - df['Change_in_Prod_Merc_Short_All']
    
    df['Total_Net'] = df['Producer_Net'] + df['Money_Manager_Net']
    df['Gap'] = df['Money_Manager_Net'] - df['Producer_Net'] 

    # Calculate percentiles for each commodity
    for index, row in df.iterrows():
        commodity_code = row['CFTC_Commodity_Code']
        market_symbol = row['Market_Symbol']
        term_curve_data = analyze_data_from_db(db_connection, market_symbol)
        
        _, df.loc[index, 'Producer_25w'], df.loc[index, 'Producer_52w'], df.loc[index, 'Producer_3yr'] = get_historical_data_and_percentiles(db_connection, commodity_code, 'Producer', latest_date)
        _, df.loc[index, 'Money_Manager_25w'], df.loc[index, 'Money_Manager_52w'], df.loc[index, 'Money_Manager_3yr'] = get_historical_data_and_percentiles(db_connection, commodity_code, 'Money_Manager', latest_date)
        
        _, df.loc[index, 'Total_25w'], df.loc[index, 'Total_52w'], df.loc[index, 'Total_3yr'] = get_historical_data_and_percentiles(db_connection, commodity_code, 'Total', latest_date)
        _, df.loc[index, 'Gap_25w'], df.loc[index, 'Gap_52w'], df.loc[index, 'Gap_3yr'] = get_historical_data_and_percentiles(db_connection, commodity_code, 'Gap', latest_date)

        if term_curve_data:
                df.loc[index, 'short_term_structure'] = term_curve_data['Short_Term_Structure']
                df.loc[index, 'long_term_structure'] = term_curve_data['Long_Term_Structure']
                df.loc[index, 'overall_term_structure'] = term_curve_data['Overall_Term_Structure']
                # Assuming df is the DataFrame you are working with:
                if term_curve_data is not None:
                    # Ensure that 'term_structure_data' column can hold objects
                    if 'term_structure_data' not in df.columns:
                        df['term_structure_data'] = pd.Series([None]*len(df), index=df.index, dtype='object')
                    else:
                        df['term_structure_data'] = df['term_structure_data'].astype('object')

                    # Assign the value
                    df.at[index, 'term_structure_data'] = term_curve_data['term_structure_data']
                else:
                    df.at[index, 'term_structure_data'] = None

        try:
            df.loc[index, 'term_structure_diagram'] = generate_diagram(db_connection, market_symbol)
        except Exception as e:
            logger.error(f"Failed to generate term structure diagram for {market_symbol}: {str(e)}")
            df.loc[index, 'term_structure_diagram'] = None

    # Group data by category
    grouped_data = df.groupby('Commodity_Category')

    # Prepare data for HTML template
    data = [
        {
            'category': category,
            'commodities': group.to_dict('records')
        }
        for category, group in grouped_data
    ]

    # Set up Jinja2 environment
    env = Environment(loader=FileSystemLoader('.'))
    template = env.get_template('templates/disagregated_fut_template.html')

    # Render HTML
    html_output = template.render(data=data, report_date=latest_date.strftime('%Y-%m-%d'))

    # Save HTML file
    outputfile = f'{report_output_dir}/{latest_date.strftime("%Y-%m-%d")}_cot_analysis.html'
    with open(outputfile, 'w') as f:
        f.write(html_output)


if __name__ == "__main__":
    target_date = None # datetime(2009, 10, 5).date
    generate_report(target_date)