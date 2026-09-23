#!/usr/bin/env python3
import argparse
import configparser
import os
import psycopg2
import sys
import time


if __name__ == '__main__':
    arg_parser = argparse.ArgumentParser()
    arg_parser.add_argument('--db_host')
    arg_parser.add_argument('--db_port')
    arg_parser.add_argument('--db_user')
    arg_parser.add_argument('--db_password')
    arg_parser.add_argument('--timeout', type=int, default=5)

    args = arg_parser.parse_args()

    config_options = {}
    rc_file_path = os.environ.get('ODOO_RC')
    if rc_file_path:
        config = configparser.RawConfigParser()
        config.read(rc_file_path)
        config_options = { k:v for k,v in config.items('options')}

    db_host = config_options.get('db_host') or args.db_host or os.environ.get('PGHOST')
    db_port = config_options.get('db_port') or args.db_port or os.environ.get('PGPORT')
    db_user = config_options.get('db_user') or args.db_user or os.environ.get('PGUSER')
    db_password = config_options.get('db_password') or args.db_password or os.environ.get('PGPASSWORD')

    params = {'db_host': db_host, 'db_port': db_port, 'db_user': db_user, 'db_password': db_password}
    missing_params = [k for k, v in params.items() if v is None]
    if missing_params:
        print(f"Missing required database parameters: {', '.join(missing_params)}", file=sys.stderr)
        sys.exit(1)

    start_time = time.time()
    while (time.time() - start_time) < args.timeout:
        try:
            conn = psycopg2.connect(user=db_user, host=db_host, port=db_port, password=db_password, dbname='postgres')
            error = ''
            break
        except psycopg2.OperationalError as e:
            error = e
        else:
            conn.close()
        time.sleep(1)

    if error:
        print("Database connection failure: %s" % error, file=sys.stderr)
        sys.exit(1)
