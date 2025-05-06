#!/bin/bash
set -e

export PGPASSWORD=$PASSWORD

# Wait for PostgreSQL
sleep 10

table_check_query="SELECT to_regclass('public.ir_module_module')"
table_exists=$(psql -h $HOST -p $DB_PORT -U $USER -d $DB_NAME -t -c "$table_check_query" | xargs)

unset PGPASSWORD

# If the query returns a value, then exit
if [ "$table_exists" = "ir_module_module" ]; then
    echo "Database already initialized"
    exit 0
fi

echo "Database is not initialized. Starting initialization..."

# Initialize the database with base module
odoo --db_host $HOST --db_port $DB_PORT --db_user $USER --db_password $PASSWORD \
     --database $DB_NAME -i base --stop-after-init

echo "Database initialization complete"
