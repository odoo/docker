#!/usr/bin/env python3
import argparse
import configparser
import logging
import os
import subprocess

logging.basicConfig(
    format="%(asctime)s - %(levelname)s - %(message)s",
    level=logging.INFO
)


class DatabaseConnectionError(Exception):
    pass


def check_postgres_status(host="localhost", port=5432, user="postgres", timeout=30):
    result = subprocess.run(
        ["pg_isready", "-h", host, "-p", str(port), "-U", user, "-t", str(timeout)],
        capture_output=True,
        text=True
    )

    return result.stdout.strip(), result.returncode


if __name__ == '__main__':
    default_config_path = os.getenv('ODOO_RC', '/etc/odoo/odoo_docker.conf')
    default_psql_wait_timeout = os.getenv('PSQL_WAIT_TIMEOUT', 30)

    arg_parser = argparse.ArgumentParser()
    arg_parser.add_argument('--config', type=str, default=default_config_path)
    arg_parser.add_argument('--timeout', type=int, default=default_psql_wait_timeout)

    args = arg_parser.parse_args()

    config = configparser.ConfigParser()
    config.read(args.config)

    db_host = config.get('options', 'db_host', fallback='localhost')
    db_port = config.get('options', 'db_port', fallback=5432)
    db_user = config.get('options', 'db_user', fallback='odoo')

    logging.info("Waiting for database(s) to be ready ...")
    logging.info(f"Host: {db_user}@{db_host}:{db_port}")
    logging.info(f"Timeout: {args.timeout} seconds")

    status, exit_code = check_postgres_status(
        host=db_host,
        port=db_port,
        user=db_user,
        timeout=args.timeout
    )

    if exit_code != 0:
        raise DatabaseConnectionError(f"Unable to connect to the database. Exit code: {exit_code} - Message: {status}")

    logging.info("🚀 Database(s) are ready.")
