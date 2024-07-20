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


#target_date = datetime(2023, 1, 3)
#target_date_str = target_date.strftime('%Y-%m-%d')

REPORT_NAME_POSTFIX = 'disaggregated_fut.csv'

def load_data_and_generate_report(tmp_output_dir: str, report_output_dir: str, db_connection: Connection, target_date: datetime):
    
    target_date_str = target_date.strftime('%Y-%m-%d')

    # download the COT data for this year in any case
    csv_file = download_to_csv(tmp_output_dir=tmp_output_dir, year=target_date.year)
    process_csv(csv_file, db_connection)

    # download COT data for previous years only if its not present alreay
    for year in range(target_date.year - 1, target_date.year - 5, -1):

        csv_file = f'{tmp_output_dir}/{year}_{REPORT_NAME_POSTFIX}'

        if not os.path.exists(csv_file):
            csv_file = download_to_csv(tmp_output_dir=tmp_output_dir, year=year)
            
        process_csv(csv_file, db_connection)

    generate_report(db_connection, report_output_dir, target_date_str)


def download_to_csv(tmp_output_dir: str, year: int) -> str:
    csv_file = f'{tmp_output_dir}/{year}_{REPORT_NAME_POSTFIX}'
    df = cot.cot_year(output_tmp_dir=tmp_output_dir, year = year, cot_report_type = 'disaggregated_fut')
    df.to_csv(csv_file)

    return csv_file
    