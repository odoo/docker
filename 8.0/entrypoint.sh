#!/bin/bash

set -e

# set odoo database host, port, user and password
: ${PGHOST:=$DB_PORT_5432_TCP_ADDR}
: ${PGPORT:=$DB_PORT_5432_TCP_PORT}
: ${PGUSER:=${DB_ENV_POSTGRES_USER:='postgres'}}
: ${PGPASSWORD:=$DB_ENV_POSTGRES_PASSWORD}
export PGHOST PGPORT PGUSER PGPASSWORD

if [[ ! -f /var/lib/odoo/etc/openerp-server.conf ]]; then
   mkdir -p /var/lib/odoo/etc
   mv /etc/odoo/openerp-server.conf /var/lib/odoo/etc/openerp-server.conf
else
    rm -f /etc/odoo/openerp-server.conf
fi
ln -s /var/lib/odoo/etc/openerp-server.conf /etc/odoo/openerp-server.conf
chown -R odoo /var/lib/odoo


case "$1" in
	--)
		shift
		exec gosu odoo openerp-server "$@"
		;;
	-*)
		exec gosu odoo openerp-server "$@"
		;;
	*)
		exec gosu odoo "$@"
esac

exit 1
