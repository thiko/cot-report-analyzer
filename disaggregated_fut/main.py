import os
import sys
from datetime import datetime

import pandas as pd
from csv_to_db import process_csv
from report_generator import generate_report

# append the path of the
# parent directory
sys.path.append("..")

from cot_reports import cot_reports as cot

target_date = datetime(2023, 1, 3)
target_date_str = target_date.strftime('%Y-%m-%d')


for year in range(target_date.year, target_date.year - 5, -1):

    adjusted_target_date = target_date.replace(year=year)

    csv_file = f'{year}_disaggregated_fut.csv'

    if not os.path.exists(csv_file):
        df = cot.cot_year(year = year, cot_report_type = 'disaggregated_fut')
        df.to_csv(csv_file)
        
    process_csv(csv_file)


generate_report(target_date_str)