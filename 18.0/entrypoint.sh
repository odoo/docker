#!/bin/bash

set -e

# Setup default configuration values
export ADDONS_PATH=${ADDONS_PATH:-/mnt/extra-addons}
export DATA_DIR=${DATA_DIR:-/var/lib/odoo}
export DB_HOST=${DB_HOST:=${HOST:=${DB_PORT_5432_TCP_ADDR:='db'}}}
export DB_PORT=${DB_PORT:=${PORT:=${DB_PORT_5432_TCP_PORT:=5432}}}
export DB_USER=${DB_USER:=${USER:=${DB_ENV_POSTGRES_USER:=${POSTGRES_USER:='odoo'}}}}
export DB_PASSWORD=${DB_PASSWORD:=${PASSWORD:=${DB_ENV_POSTGRES_PASSWORD:=${POSTGRES_PASSWORD:='odoo'}}}}
export DB_NAME=${DB_NAME:-'postgres'}
export ADMIN_PASSWD=${ADMIN_PASSWD:-admin}
export CSV_INTERNAL_SEP=${CSV_INTERNAL_SEP:-,}
export DB_MAXCONN=${DB_MAXCONN:-64}
export DB_TEMPLATE=${DB_TEMPLATE:-template1}
export DBFILTER=${DBFILTER:-.*}
export DEBUG_MODE=${DEBUG_MODE:-False}
export EMAIL_FROM=${EMAIL_FROM:-False}
export LIMIT_MEMORY_HARD=${LIMIT_MEMORY_HARD:-2684354560}
export LIMIT_MEMORY_SOFT=${LIMIT_MEMORY_SOFT:-2147483648}
export LIMIT_REQUEST=${LIMIT_REQUEST:-8192}
export LIMIT_TIME_CPU=${LIMIT_TIME_CPU:-60}
export LIMIT_TIME_REAL=${LIMIT_TIME_REAL:-120}
export LIST_DB=${LIST_DB:-True}
export LOG_DB=${LOG_DB:-False}
export LOG_HANDLER=${LOG_HANDLER:-[:INFO]}
export LOG_LEVEL=${LOG_LEVEL:-info}
export LOGFILE=${LOGFILE:-None}
export LONGPOLLING_PORT=${LONGPOLLING_PORT:-8072}
export MAX_CRON_THREADS=${MAX_CRON_THREADS:-2}
export OSV_MEMORY_AGE_LIMIT=${OSV_MEMORY_AGE_LIMIT:-1.0}
export OSV_MEMORY_COUNT_LIMIT=${OSV_MEMORY_COUNT_LIMIT:-False}
export SMTP_PASSWORD=${SMTP_PASSWORD:-False}
export SMTP_PORT=${SMTP_PORT:-25}
export SMTP_SERVER=${SMTP_SERVER:-localhost}
export SMTP_SSL=${SMTP_SSL:-False}
export SMTP_USER=${SMTP_USER:-False}
export WORKERS=${WORKERS:-0}
export XMLRPC=${XMLRPC:-True}
export XMLRPC_INTERFACE=${XMLRPC_INTERFACE:-}
export XMLRPC_PORT=${XMLRPC_PORT:-8069}
export XMLRPCS=${XMLRPCS:-True}
export XMLRPCS_INTERFACE=${XMLRPCS_INTERFACE:-}
export XMLRPCS_PORT=${XMLRPCS_PORT:-8071}

echo $DB_HOST

# Set the password file environment variable
if [ -v PASSWORD_FILE ]; then
    DB_PASSWORD="$(< $PASSWORD_FILE)"
fi

# Substitute environment variables into the config file
# and write them back to the Odoo config
envsubst < /etc/odoo/odoo.conf > "${ODOO_RC}"

case "$1" in
    -- | odoo)
        shift
        if [[ "$1" == "scaffold" ]] ; then
            exec odoo "$@"
        else
            wait-for-psql.py --timeout=30
            exec odoo "$@"
        fi
        ;;
    -*)
        wait-for-psql.py --timeout=30
        exec odoo "$@"
        ;;
    *)
        exec "$@"
esac

exit 1
