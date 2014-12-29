#!/bin/bash

# set openerp-server.conf
echo "[options]
; This is the password that allows database operations:
; admin_passwd = admin
db_host = $DB_PORT_5432_TCP_ADDR
db_port = $DB_PORT_5432_TCP_PORT
db_user = odoo
db_password = odoo
data_dir = /var/lib/odoo
addons_path = /usr/lib/python2.7/dist-packages/openerp/addons" > /etc/odoo/openerp-server.conf

# start Odoo
exec gosu odoo /usr/bin/openerp-server --config /etc/odoo/openerp-server.conf
