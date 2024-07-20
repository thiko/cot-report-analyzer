import argparse
import configparser
import sqlite3
from datetime import datetime, timedelta

from disaggregated_fut.disaggregated_fut import load_data_and_generate_report

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
    parser.add_argument('-d', '--date', nargs='?', help='Optional parameter if you want to generate the report for one specific date (format: YYYY-mm-dd). Default: Last Friday (or today, if its Friday)', default=get_last_tuesday().strftime(DATETIME_FOMRAT))
    args = parser.parse_args()

    # Konfiguration laden
    config = load_config(args.config)
    target_date = datetime.strptime(args.date, DATETIME_FOMRAT)

    # Beispiel für den Zugriff auf Konfigurationswerte
    
    tmp_output_dir = config['App']['output_tmp_directory']
    reports_output_dir = config['App']['output_reports_directory']
    database_file = config['App']['database_filename']

    debug_mode = config['DEFAULT'].getboolean('debug')
    
    print(f"Debug-Mode: {'On' if debug_mode else 'Off'}")

    db_connection = sqlite3.connect(f'{tmp_output_dir}/{database_file}')
    try:    
        load_data_and_generate_report(tmp_output_dir, reports_output_dir, db_connection, target_date)
    finally:
        db_connection.close()

if __name__ == "__main__":
    main()