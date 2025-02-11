#!/usr/bin/env python3
import argparse
import os
import psycopg2
import sys
import time
import configparser
import logging

logging.basicConfig(
    format="%(asctime)s - %(levelname)s - %(message)s",
    level=logging.INFO
)

class DatabaseConnectionError(Exception):
    pass

if __name__ == '__main__':
    default_config_path = os.getenv('ODOO_RC', '/etc/odoo/odoo_docker.conf')

    arg_parser = argparse.ArgumentParser()
    arg_parser.add_argument('--config', type=str, default=default_config_path)
    arg_parser.add_argument('--timeout', type=int, default=5)

    args = arg_parser.parse_args()

    config = configparser.ConfigParser()
    config.read(args.config)

    db_host = config.get('options', 'db_host', fallback='localhost')
    db_port = config.get('options', 'db_port', fallback=5432)
    db_user = config.get('options', 'db_user', fallback='odoo')
    db_password = config.get('options', 'db_password', fallback='odoo')
    db_name = config.get('options', 'db_name', fallback='postgres')

    start_time = time.time()

    database_list = db_name.split(',')
    logging.info("Waiting for database(s) to be ready ...")
    logging.info(f"Host: {db_user}@{db_host}:{db_port}")
    logging.info(f"Database(s): {database_list}")
    logging.info(f"Timeout: {args.timeout} seconds")

    for database in database_list:
        logging.info(f"Checking database {database} ...")
        error = None

        while (time.time() - start_time) < args.timeout:
            try:
                conn = psycopg2.connect(
                    user=db_user,
                    host=db_host,
                    port=db_port,
                    password=db_password,
                    dbname=database
                )

                error = None
                conn.close()

                logging.info(f"Database {database} is ready.")
                break
            except psycopg2.OperationalError as e:
                error = e
                time.sleep(1)

        if error:
            raise DatabaseConnectionError(f"Database {database} connection failure: {error}")

    logging.info("🚀 Database(s) are ready.")