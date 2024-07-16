import argparse
import configparser
import sqlite3

from disaggregated_fut.disaggregated_fut import load_data_and_generate_report


def load_config(config_file='config.ini'):
    config = configparser.ConfigParser()
    config.read(config_file)
    return config


def main():
    
    parser = argparse.ArgumentParser(description='')
    parser.add_argument('-c', '--config', help='Pfad zur Konfigurationsdatei', default='config.ini')
    args = parser.parse_args()

    # Konfiguration laden
    config = load_config(args.config)

    # Beispiel für den Zugriff auf Konfigurationswerte
    
    tmp_output_dir = config['App']['output_tmp_directory']
    reports_output_dir = config['App']['output_reports_directory']
    database_file = config['App']['database_filename']

    debug_mode = config['DEFAULT'].getboolean('debug')
    
    print(f"Debug-Modus: {'An' if debug_mode else 'Aus'}")

    db_connection = sqlite3.connect(f'{tmp_output_dir}/{database_file}')
    
    load_data_and_generate_report(tmp_output_dir, reports_output_dir, db_connection)

    db_connection.close()

if __name__ == "__main__":
    main()