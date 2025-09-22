#!/bin/bash
# init-db.sh
# Usage: ./init-db.sh <db_name> [modules]
# Example: ./init-db.sh testdb "base,web,mail"

set -e

# Database name from args
DB_NAME=$1
if [ -z "$DB_NAME" ]; then
    echo "❌ Please provide a database name"
    echo "👉 Example: ./init-db.sh testdb \"base,web,mail\""
    exit 1
fi

# Modules to install (default: base,web)
MODULES=${2:-"base,web"}

echo "🚀 Initializing Odoo database: $DB_NAME"
echo "📦 Installing modules: $MODULES"

# Run Odoo container to init the DB
docker-compose run --rm web \
    odoo -c /etc/odoo/odoo.conf \
    -d "$DB_NAME" \
    -i "$MODULES" \
    --stop-after-init

echo "✅ Database '$DB_NAME' initialized with modules: $MODULES"
