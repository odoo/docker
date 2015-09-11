#!/bin/bash

set -e

# set odoo database host, port, user and password
: ${PGHOST:=${RDS_HOSTNAME:=${PGHOST:=${DB_PORT_5432_TCP_ADDR:='localhost'}}}}
: ${PGPORT:=${RDS_PORT:=${PGPORT:=${DB_PORT_5432_TCP_PORT:=5432}}}}
: ${PGUSER:=${RDS_USERNAME:=${PGUSER:=${DB_ENV_POSTGRES_USER:='postgres'}}}}
: ${PGPASSWORD:=${RDS_PASSWORD:=${PGPASSWORD:=$DB_ENV_POSTGRES_PASSWORD}}}
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
