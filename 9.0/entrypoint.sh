#!/bin/bash

set -e

# set odoo database host, port, user and password
: ${PGHOST:=${DB_PORT_5432_TCP_ADDR:='db'}}
: ${PGPORT:=${DB_PORT_5432_TCP_PORT:=5432}}
: ${PGUSER:=${DB_ENV_POSTGRES_USER:=${POSTGRES_USER:='postgres'}}}
: ${PGPASSWORD:=${DB_ENV_POSTGRES_PASSWORD:=$POSTGRES_PASSWORD}}
export PGHOST PGPORT PGUSER PGPASSWORD

case "$1" in
	--)
		shift
		exec openerp-server "$@"
		;;
	-*)
		exec openerp-server "$@"
		;;
	*)
		exec "$@"
esac

exit 1
