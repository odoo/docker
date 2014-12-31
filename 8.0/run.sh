#!/bin/bash

# set variables in openerp-server.conf
sed -i "s/^db_host.*/db_host = $DB_PORT_5432_TCP_ADDR/" /etc/odoo/openerp-server.conf
sed -i "s/^db_port.*/db_port = $DB_PORT_5432_TCP_PORT/" /etc/odoo/openerp-server.conf
sed -i "s/^db_user.*/db_user = $DB_ENV_POSTGRES_USER/" /etc/odoo/openerp-server.conf
sed -i "s/^db_password.*/db_password = $DB_ENV_POSTGRES_PASSWORD/" /etc/odoo/openerp-server.conf
sed -i "\$adata_dir = /var/lib/odoo" /etc/odoo/openerp-server.conf

# start Odoo
exec gosu odoo /usr/bin/openerp-server --config /etc/odoo/openerp-server.conf
