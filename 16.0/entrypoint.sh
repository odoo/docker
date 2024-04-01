#!/bin/bash

set -e

if [ -v PASSWORD_FILE ]; then
    PASSWORD="$(< $PASSWORD_FILE)"
fi

# set the postgres database host, port, user and password according to the environment
# and pass them as arguments to the odoo process if not present in the config file
: ${HOST:=${DB_PORT_5432_TCP_ADDR:='db'}}
: ${PORT:=${DB_PORT_5432_TCP_PORT:=5432}}
: ${NAME:=${DB_ENV_POSTGRES_NAME:=${POSTGRES_NAME:='postgres'}}}
: ${USER:=${DB_ENV_POSTGRES_USER:=${POSTGRES_USER:='odoo'}}}
: ${PASSWORD:=${DB_ENV_POSTGRES_PASSWORD:=${POSTGRES_PASSWORD:='odoo'}}}

ODOO_ARGS=()
DB_ARGS=()

function check_config() {
    param="$1"
    value="$2"
    pg_flag="$3"

    if grep -q -E "^\s*\b${param}\b\s*=" "$ODOO_RC" ; then       
        value=$(grep -E "^\s*\b${param}\b\s*=" "$ODOO_RC" |cut -d " " -f3|sed 's/["\n\r]//g')
    fi;

    ODOO_ARGS+=("--${param}")
    ODOO_ARGS+=("${value}")

    DB_ARGS+=("${pg_flag}")
    DB_ARGS+=("${value}")
}

check_config "db_name" "$NAME" "-d"
check_config "db_host" "$HOST" "-h"
check_config "db_port" "$PORT" "-p"
check_config "db_user" "$USER" "-U"
# check_config "db_password" "$PASSWORD"

case "$1" in
    -- | odoo)
        shift
        if [[ "$1" == "scaffold" ]] ; then
            exec odoo "$@"
        else
            pg_isready ${DB_ARGS[@]} --timeout=30
            exec odoo "$@" "${ODOO_ARGS[@]}"
        fi
        ;;
    -*)
        pg_isready ${DB_ARGS[@]} --timeout=30
        exec odoo "$@" "${ODOO_ARGS[@]}"
        ;;
    *)
        exec "$@"
esac

exit 1
