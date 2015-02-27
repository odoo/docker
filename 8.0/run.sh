#!/bin/bash

[ "$1" != "--" ] && exec "$@" || shift

CONFIG_FILE=/etc/odoo/openerp-server.conf

# sets a configuration variable in openerp-server.conf
# $1: key, $2: value
function set_config {
  if grep -q "^$1.*" $CONFIG_FILE
  then
    sed -i "s/^$1.*$/$1 = $2/" $CONFIG_FILE
  else
    sed -i "$ a$1 = $2" $CONFIG_FILE
  fi
}

# set odoo data directory and database host, port, user and password
set_config "data_dir" "\/var\/lib\/odoo"
set_config "db_host" $DB_PORT_5432_TCP_ADDR
set_config "db_port" $DB_PORT_5432_TCP_PORT
set_config "db_user" $DB_ENV_POSTGRES_USER
set_config "db_password" $DB_ENV_POSTGRES_PASSWORD

# start Odoo
exec gosu odoo /usr/bin/openerp-server --config $CONFIG_FILE "$@"
