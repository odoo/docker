#!/bin/bash
set -e

export PGPASSWORD=$PASSWORD

# Wait for PostgreSQL
sleep 10

query="SELECT latest_version FROM ir_module_module WHERE name = 'base'"

result=$(psql -h $HOST -p $DB_PORT -U $USER -d $DB_NAME -c "$query" -t)

unset PGPASSWORD

# If the query returns a value, then exit
if [ -n "$result" ]; then
    echo "Database already initialized"
    exit 0
fi

# Initialize the database with base module
odoo --db_host $HOST --db_port $DB_PORT --db_user $USER --db_password $PASSWORD \
     --database $DB_NAME -i base --stop-after-init

echo "Database initialization complete"
