#!/bin/bash

set -e

# set the postgres database host, port, user and password
: ${HOST:=${DB_PORT_5432_TCP_ADDR:='db'}}
: ${PORT:=${DB_PORT_5432_TCP_PORT:=5432}}
: ${USER:=${DB_ENV_POSTGRES_USER:=${POSTGRES_USER:='odoo'}}}
: ${PASSWORD:=${DB_ENV_POSTGRES_PASSWORD:=${POSTGRES_PASSWORD:='odoo'}}}

# pass them as arguments to the odoo process if not present in the config file
DB_ARGS=("--db_user" $USER "--db_password" $PASSWORD "--db_host" $HOST "--db_port" $PORT)

function is_in_config_file() {
    if [[ ! -f ${ODOO_RC} ]] ; then
        return 1
    fi

    while read -r line ; do
        if [[ ${line} == ${1}* ]] ; then
            return 0
        fi
    done < "${ODOO_RC}"
    return 1
}

for i in "${!DB_ARGS[@]}" ; do
    # postgres credentials begins by `--` when used as odoo argument but it's not the
    # case when they're set in the config file
    if  [[ "${DB_ARGS[$i]}" == --* ]] && is_in_config_file "${DB_ARGS[$i]:2}" ; then
        unset "DB_ARGS[$i]" ; unset "DB_ARGS[$i+1]"
    fi
done

case "$1" in
	-- | odoo)
		shift
		exec odoo "${DB_ARGS[@]}" "$@"
		;;
	-*)
		exec odoo "${DB_ARGS[@]}" "$@"
		;;
	*)
		exec "$@"
esac

exit 1
