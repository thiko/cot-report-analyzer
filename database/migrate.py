import glob
import logging
import os
import sqlite3

# Configure logger

logger = logging.getLogger(__name__)

def get_ordered_sql_files(directory):
    """
    Get a list of SQL files in the directory, sorted by their numerical prefix.
    """
    sql_files = glob.glob(os.path.join(directory, "*.sql"))
    sql_files_sorted = sorted(sql_files, key=lambda x: int(os.path.basename(x).split('_', 1)[0]))
    return sql_files_sorted

def execute_sql_files(directory, conn: sqlite3.Connection):
    """
    Execute all SQL files in the given directory in the correct order.
    """
    sql_files = get_ordered_sql_files(directory)
    
    cursor = conn.cursor()
    
    for sql_file in sql_files:
        logger.info(f"Executing {sql_file}")
        try:
            with open(sql_file, 'r') as file:
                sql_script = file.read()
            cursor.executescript(sql_script)
            conn.commit()
        except Exception as e:
            logger.error(f"Failed to execute {sql_file}: {e}")
            conn.rollback()
            break

    conn.commit()
    cursor.close()
