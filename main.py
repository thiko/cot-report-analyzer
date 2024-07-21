import argparse
import configparser
import logging
import sqlite3
from datetime import datetime, timedelta

from database.migrate import execute_sql_files
from disaggregated_fut.disaggregated_fut import load_data_and_generate_report
from summary_report.generate_summary import generate_output_summary

DATETIME_FOMRAT = "%Y-%m-%d"

def load_config(config_file='config.ini'):
    config = configparser.ConfigParser()
    config.read(config_file)
    return config

def get_last_tuesday():
    today = datetime.now().date()
    days_since_tuesday = (today.weekday() - 1) % 7
    last_tuesday = today - timedelta(days=days_since_tuesday)
    return last_tuesday


def main():
    
    parser = argparse.ArgumentParser(description='')
    parser.add_argument('-c', '--config', help='Path to config file', default='config.ini')
    parser.add_argument('-d', '--date', nargs='?', help='Optional parameter if you want to generate the report for one specific date (format: YYYY-mm-dd). Default: Last Tuesday (or today, if its Tuesday)', default=get_last_tuesday().strftime(DATETIME_FOMRAT))
    args = parser.parse_args()

    # load config
    config = load_config(args.config)
    target_date = datetime.strptime(args.date, DATETIME_FOMRAT)

    tmp_output_dir = config['App']['output_tmp_directory']
    reports_output_dir = config['App']['output_reports_directory']
    database_file = config['App']['database_filename']

    debug_mode = config['DEFAULT'].getboolean('debug')
    log_level = logging.DEBUG if debug_mode == True else logging.INFO
    logging.basicConfig(format='%(asctime)s - %(levelname)s - %(message)s', level=log_level)
    
    print(f"Debug-Mode: {'On' if debug_mode else 'Off'}")

    db_connection = sqlite3.connect(f'{tmp_output_dir}/{database_file}')
    execute_sql_files('database/resources', db_connection)

    try:    
        load_data_and_generate_report(tmp_output_dir, reports_output_dir, db_connection, target_date)
        generate_output_summary(reports_output_dir)
    finally:
        db_connection.close()

if __name__ == "__main__":
    main()