import os
import sys
from datetime import datetime
from sqlite3 import Connection

import pandas as pd

from cot_reports import cot_reports as cot
from disaggregated_fut.csv_to_db import process_csv
from disaggregated_fut.report_generator import generate_report

# append the path of the
# parent directory
#sys.path.append("..")


target_date = datetime(2023, 1, 3)
target_date_str = target_date.strftime('%Y-%m-%d')

def load_data_and_generate_report(tmp_output_dir: str, report_output_dir: str, db_connection: Connection):

    for year in range(target_date.year, target_date.year - 5, -1):

        adjusted_target_date = target_date.replace(year=year)

        csv_file = f'{tmp_output_dir}/{year}_disaggregated_fut.csv'

        if not os.path.exists(csv_file):
            df = cot.cot_year(output_tmp_dir=tmp_output_dir, year = year, cot_report_type = 'disaggregated_fut')
            df.to_csv(csv_file)
            
        process_csv(csv_file, db_connection)

    generate_report(db_connection, report_output_dir, target_date_str)