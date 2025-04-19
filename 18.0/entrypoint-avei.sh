#!/bin/bash

set -e

if [ -v PASSWORD_FILE ]; then
    PASSWORD="$(< $PASSWORD_FILE)"
fi

# set the postgres database host, port, user and password according to the environment
: ${HOST:=${DB_PORT_5432_TCP_ADDR:='db'}}
: ${DB_PORT:=${DB_PORT_5432_TCP_PORT:=5432}}
: ${USER:=${DB_ENV_POSTGRES_USER:=${POSTGRES_USER:='odoo'}}}
: ${PASSWORD:=${DB_ENV_POSTGRES_PASSWORD:=${POSTGRES_PASSWORD:='odoo'}}}
: ${DB_NAME:=${DB_ENV_POSTGRES_DB:=${POSTGRES_DB:='odoo'}}}
: ${HTTP_PORT:=${PORT:=8069}}  # Use PORT env var if available, otherwise default to 8069

DB_ARGS=()
function check_config() {
    param="$1"
    value="$2"
    if grep -q -E "^\s*\b${param}\b\s*=" "$ODOO_RC" ; then
        value=$(grep -E "^\s*\b${param}\b\s*=" "$ODOO_RC" |cut -d " " -f3|sed 's/["\n\r]//g')
    fi;
    DB_ARGS+=("--${param}")
    DB_ARGS+=("${value}")
}
check_config "db_host" "$HOST"
check_config "db_port" "$DB_PORT"
check_config "db_user" "$USER"
check_config "db_password" "$PASSWORD"
# check_config "db_name" "$DB_NAME"  # Explicitly include the database name

# Wait for PostgreSQL to be available
echo "Waiting for PostgreSQL to be available..."
wait-for-psql.py ${DB_ARGS[@]} --timeout=60

# Check if the database exists and is initialized
echo "Checking if database needs initialization..."
DB_EXISTS=$(PGPASSWORD=$PASSWORD psql -h $HOST -p $DB_PORT -U $USER -lqt | cut -d \| -f 1 | grep -qw $DB_NAME && echo "yes" || echo "no")

if [ "$DB_EXISTS" = "no" ]; then
    echo "Database does not exist, creating and initializing it..."
    createdb -h $HOST -p $DB_PORT -U $USER $DB_NAMEl
    echo "Database initialization complete"
fi

/init-odoo.sh

# Now run Odoo normally
case "$1" in
    -- | odoo)
        shift
        if [[ "$1" == "scaffold" ]] ; then
            exec odoo "$@" --http-port $HTTP_PORT
        else
            echo "Starting Odoo server..."
            exec odoo "$@" "${DB_ARGS[@]}" --http-port $HTTP_PORT
        fi
        ;;
    -*)
        echo "Starting Odoo server with custom options..."
        exec odoo "$@" "${DB_ARGS[@]}" --http-port $HTTP_PORT
        ;;
    *)
        echo "Starting custom command..."
        exec "$@" --http-port $HTTP_PORT
esac

exit 1
