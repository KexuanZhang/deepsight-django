#!/bin/bash

set -e  # Exit on any error

echo "🚀 Starting DeepSight Production Services..."

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

# Check for required environment variables
if [ ! -f ".env" ]; then
    echo "⚠️  .env file not found. Creating from template..."
    if [ -f "backend/env.template" ]; then
        cp backend/env.template .env
        echo "📝 Please configure .env file with your production settings before running again."
        exit 1
    else
        echo "❌ No env.template found. Please create .env file manually."
        exit 1
    fi
fi

# Function to start services with proper compose command
start_compose() {
    local compose_file=$1
    local service_name=$2
    local services=$3
    
    if command_exists docker-compose; then
        if [ -n "$services" ]; then
            docker-compose -f "$compose_file" up -d $services
        else
            docker-compose -f "$compose_file" up -d
        fi
    else
        if [ -n "$services" ]; then
            docker compose -f "$compose_file" up -d $services
        else
            docker compose -f "$compose_file" up -d
        fi
    fi
    
    echo "✅ $service_name services started"
}

# Start Milvus ecosystem (etcd, minio, milvus)
echo "📦 Starting Milvus ecosystem (etcd, minio, milvus)..."
cd milvus
start_compose "docker-compose.yml" "Milvus"
cd ..

# Wait a moment for Milvus services to initialize
echo "⏳ Waiting for Milvus services to initialize..."
sleep 10

# Start Redis and PostgreSQL services
echo "📦 Starting Redis and PostgreSQL services..."
start_compose "docker-compose.yml" "Redis and PostgreSQL" "redis db"

# Wait for services to be ready
echo "⏳ Waiting for all services to be ready..."
sleep 15

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
    
    # Check Redis
    check_service "Redis" 6379
    
    # Check PostgreSQL
    check_service "PostgreSQL" 5432
    
    # Check etcd
    check_service "etcd" 2379
    
    # Check MinIO
    check_service "MinIO API" 9000
    check_service "MinIO Console" 9001
    
    # Check Milvus
    check_service "Milvus" 19530
    
    echo "🎉 All production services are up and running!"
else
    echo "⚠️  netcat (nc) not found. Skipping health checks."
    echo "🎉 Services started. Please verify manually if needed."
fi

echo ""
echo "📋 Production Service Summary:"
echo "  - Redis:           localhost:6379"
echo "  - PostgreSQL:      localhost:5432"
echo "  - etcd:            localhost:2379"
echo "  - MinIO API:       localhost:9000"
echo "  - MinIO Console:   localhost:9001"
echo "  - Milvus:          localhost:19530"
echo ""
echo "🔧 Next steps for production:"
echo "  1. Start backend services: docker-compose up -d backend celery celery-beat"
echo "  2. Start frontend service: docker-compose up -d frontend"
echo "  3. Or manually: cd backend && python manage.py runserver (for dev mode)"
echo ""
echo "⚠️  Production Notes:"
echo "  - Ensure .env file is properly configured"
echo "  - Check all environment variables are set"
echo "  - Monitor logs: docker-compose logs -f [service_name]"
echo ""
echo "📖 For more commands, see CLAUDE.md"