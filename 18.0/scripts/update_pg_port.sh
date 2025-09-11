
#!/bin/bash

# Script: update_postgres_port.sh
# Purpose: Dynamically update PostgreSQL port inside a Docker container
# Author: Jasper-ready 😊

# Prompt for container name
echo "📦 Available running containers:"
docker ps --format "table {{.Names}}\t{{.Image}}\t{{.Status}}" 

echo ""
read -rp "Enter the PostgreSQL container name: " container_name
if [[ -z "$container_name" ]]; then
  echo "❌ ERROR: Container name cannot be empty."
  exit 1
fi

# Prompt for new port
read -rp "Enter the new PostgreSQL port (default 5434): " new_port
new_port=${new_port:-5434}

# Paths inside the container
pg_config_file="/var/lib/postgresql/data/pgdata/postgresql.conf"
pg_data_dir="/var/lib/postgresql/data/pgdata"

# Check if container is runnings
if ! docker ps --format '{{.Names}}' | grep -q "^${container_name}$"; then
    echo "❌ ERROR: Container '${container_name}' is not running."
    exit 1
fi

echo ""
echo "📄 Updating PostgreSQL to use port ${new_port} in container '${container_name}'..."

# Update port in postgresql.conf inside the container
docker exec "$container_name" sed -i "s/^#*port = .*/port = ${new_port}/" "$pg_config_file"

# Reload PostgreSQL configuration
echo "🔄 Reloading PostgreSQL configuration..."
docker exec -u postgres "$container_name" pg_ctl reload -D "$pg_data_dir"

echo ""
echo "✅ PostgreSQL port updated to ${new_port} and reloaded successfully."
