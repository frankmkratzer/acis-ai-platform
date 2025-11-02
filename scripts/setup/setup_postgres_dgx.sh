#!/bin/bash
# Install and configure PostgreSQL on DGX Spark

echo "=========================================="
echo "PostgreSQL Installation on DGX Spark"
echo "=========================================="

# Update packages
echo ""
echo "1. Updating package lists..."
sudo apt update

# Install PostgreSQL
echo ""
echo "2. Installing PostgreSQL..."
sudo apt install -y postgresql postgresql-contrib

# Start PostgreSQL service
echo ""
echo "3. Starting PostgreSQL service..."
sudo systemctl start postgresql
sudo systemctl enable postgresql

# Check status
echo ""
echo "4. PostgreSQL service status:"
sudo systemctl status postgresql | head -10

# Create database and user
echo ""
echo "5. Creating database and user..."
sudo -u postgres psql <<EOF
CREATE DATABASE "acis-ai";
CREATE USER postgres WITH PASSWORD '$@nJose420';
ALTER USER postgres WITH SUPERUSER;
GRANT ALL PRIVILEGES ON DATABASE "acis-ai" TO postgres;
\q
EOF

# Allow local connections
echo ""
echo "6. Configuring PostgreSQL for local access..."
PG_HBA="/etc/postgresql/*/main/pg_hba.conf"
sudo bash -c "echo 'host    all      all      127.0.0.1/32      md5' >> $PG_HBA"

# Restart PostgreSQL
echo ""
echo "7. Restarting PostgreSQL..."
sudo systemctl restart postgresql

# Test connection
echo ""
echo "8. Testing PostgreSQL connection..."
PGPASSWORD="${DB_PASSWORD}" psql -h localhost -U postgres -d acis-ai -c "SELECT version();"

echo ""
echo "=========================================="
echo "PostgreSQL installation complete!"
echo "=========================================="
echo ""
echo "Connection string:"
echo "postgresql://postgres:\$@nJose420@localhost:5432/acis-ai"
echo ""
