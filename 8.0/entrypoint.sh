#!/bin/bash

set -e

# set odoo database host, port, user and password
: ${PGHOST:=$DB_PORT_5432_TCP_ADDR}
: ${PGPORT:=$DB_PORT_5432_TCP_PORT}
: ${PGUSER:=${DB_ENV_POSTGRES_USER:='postgres'}}
: ${PGPASSWORD:=$DB_ENV_POSTGRES_PASSWORD}
export PGHOST PGPORT PGUSER PGPASSWORD

# if the first arg starts with '-', prepend 'openerp-server' to $@
if [ "${1:0:1}" = '-' ]; then
	set -- openerp-server "$@"
fi

exec "$@"
