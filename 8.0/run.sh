#!/bin/bash

# set odoo database host, port, user and password
export PGHOST=$DB_PORT_5432_TCP_ADDR
export PGPORT=$DB_PORT_5432_TCP_PORT
export PGUSER=$DB_ENV_POSTGRES_USER
export PGPASSWORD=$DB_ENV_POSTGRES_PASSWORD

[ "$1" != "--" ] && exec "$@"

shift
exec /usr/bin/openerp-server --config=/etc/odoo/openerp-server.conf "$@"
