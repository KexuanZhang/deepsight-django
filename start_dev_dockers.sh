#!/bin/bash

set -e  # Exit on any error

echo "🚀 Starting DeepSight Development Services..."

# Function to check if a command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Check if Docker and Docker Compose are installed
if ! command_exists docker; then
    echo "❌ Docker is not installed. Please install Docker first."
    exit 1
fi

if ! command_exists docker-compose && ! docker compose version >/dev/null 2>&1; then
    echo "❌ Docker Compose is not installed. Please install Docker Compose first."
    exit 1
fi

# Function to start services with proper compose command
start_compose() {
    local compose_file=$1
    local service_name=$2
    local services=$3
    
    if command_exists docker-compose; then
        if [ -n "$services" ]; then
            docker-compose -f "$compose_file" up -d --remove-orphans $services
        else
            docker-compose -f "$compose_file" up -d --remove-orphans
        fi
    else
        if [ -n "$services" ]; then
            docker compose -f "$compose_file" up -d --remove-orphans $services
        else
            docker compose -f "$compose_file" up -d --remove-orphans
        fi
    fi
    
    echo "✅ $service_name services started"
}

# Start Milvus ecosystem (etcd, minio, milvus)
echo "📦 Starting Milvus ecosystem (etcd, minio, milvus)..."
start_compose "docker/development/docker-compose.yml" "Milvus"

# Wait a moment for Milvus services to initialize
echo "⏳ Waiting for Milvus services to initialize..."
sleep 10

# (No additional root-level Docker Compose file; all services are under milvus/)

# Wait for services to be ready
echo "⏳ Waiting for all services to be ready..."
sleep 10

# Health check function
check_service() {
    local service_name=$1
    local port=$2
    local host=${3:-localhost}
    
    echo "🔍 Checking $service_name on $host:$port..."
    if nc -z "$host" "$port" 2>/dev/null; then
        echo "✅ $service_name is ready"
        return 0
    else
        echo "❌ $service_name is not ready"
        return 1
    fi
}

# Check if netcat is available for health checks
if command_exists nc; then
    echo "🏥 Running health checks..."
    
    # Check etcd
    check_service "etcd" 2379
    
    # Check MinIO
    check_service "MinIO API" 9000
    check_service "MinIO Console" 9001
    
    # Check Milvus
    check_service "Milvus" 19530
    
    echo "🎉 All development services are up and running!"
else
    echo "⚠️  netcat (nc) not found. Skipping health checks."
    echo "🎉 Services started. Please verify manually if needed."
fi

echo ""
echo "📋 Development Service Summary:"
echo "  - etcd:            localhost:2379"
echo "  - MinIO API:       localhost:9000"
echo "  - MinIO Console:   localhost:9001"
echo "  - Milvus:          localhost:19530"
echo ""
echo "💾 Database: SQLite (no PostgreSQL in dev mode)"