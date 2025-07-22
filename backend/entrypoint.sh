#!/bin/bash
set -e

echo "🚀 Starting Django application setup..."

# Function to wait for database
wait_for_db() {
    echo "⏳ Waiting for database connection..."
    python << END
import os
import time
import sys

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')

import django
django.setup()

from django.db import connections
from django.db.utils import OperationalError

db_conn = connections['default']
retries = 30

for i in range(retries):
    try:
        db_conn.ensure_connection()
        print("✅ Database connection successful!")
        break
    except OperationalError as e:
        print(f"❌ Database unavailable ({i+1}/{retries}): {e}")
        if i == retries - 1:
            print("💥 Database connection failed after maximum retries")
            sys.exit(1)
        time.sleep(1)
END
}

# Function to wait for Redis
wait_for_redis() {
    echo "⏳ Waiting for Redis connection..."
    python << END
import redis
import time
import sys
import os

redis_url = os.environ.get('REDIS_URL', 'redis://redis:6379/0')
retries = 30

for i in range(retries):
    try:
        r = redis.from_url(redis_url)
        r.ping()
        print("✅ Redis connection successful!")
        break
    except Exception as e:
        print(f"❌ Redis unavailable ({i+1}/{retries}): {e}")
        if i == retries - 1:
            print("💥 Redis connection failed after maximum retries")
            sys.exit(1)
        time.sleep(1)
END
}

# Function to run migrations and setup
run_django_setup() {
    echo "🔄 Running database migrations..."
    python manage.py migrate --noinput
    echo "✅ Migrations completed!"

    echo "📦 Collecting static files..."
    python manage.py collectstatic --noinput --clear
    echo "✅ Static files collected!"

    if [ "$DJANGO_SUPERUSER_USERNAME" ] && [ "$DJANGO_SUPERUSER_EMAIL" ] && [ "$DJANGO_SUPERUSER_PASSWORD" ]; then
        echo "👤 Creating superuser..."
        python manage.py shell << END
from django.contrib.auth import get_user_model
User = get_user_model()
if not User.objects.filter(username='$DJANGO_SUPERUSER_USERNAME').exists():
    User.objects.create_superuser('$DJANGO_SUPERUSER_USERNAME', '$DJANGO_SUPERUSER_EMAIL', '$DJANGO_SUPERUSER_PASSWORD')
    print("✅ Superuser created!")
else:
    print("ℹ️  Superuser already exists")
END
    fi
}

# Main logic: only two types of services
case "$1" in
    # Backend services: Django web server and management commands
    "gunicorn")
        echo "🔧 Setting up Django web server..."
        wait_for_db
        run_django_setup
        echo "🎉 Django setup completed! Starting Gunicorn..."
        exec gunicorn backend.wsgi:application \
            --bind 0.0.0.0:8000 \
            --workers ${GUNICORN_WORKERS:-2} \
            --timeout ${GUNICORN_TIMEOUT:-600} \
            --max-requests ${GUNICORN_MAX_REQUESTS:-1000} \
            --max-requests-jitter ${GUNICORN_MAX_REQUESTS_JITTER:-100} \
            --access-logfile - \
            --error-logfile -
        ;;
    
    "python"|"django-admin"|"manage.py")
        echo "🔧 Setting up Django management command..."
        wait_for_db
        run_django_setup
        echo "🎉 Django setup completed! Starting: $1"
        exec "$@"
        ;;
    
    # Celery services: worker and beat scheduler  
    "celery-worker"|"celery-beat"|"celery")
        echo "🔧 Setting up Celery service..."
        wait_for_db
        wait_for_redis
        echo "🎉 Celery setup completed!"
        
        # Handle specific celery commands
        if [ "$1" = "celery-worker" ]; then
            echo "🔄 Starting Celery worker..."
            exec celery -A backend worker \
                --loglevel=info \
                --concurrency=${CELERY_CONCURRENCY:-4} \
                --queues=${CELERY_QUEUES:-notebook_processing,podcast,reports,maintenance,validation} \
                --max-tasks-per-child=${CELERY_MAX_TASKS_PER_CHILD:-100} \
                --time-limit=${CELERY_TASK_TIME_LIMIT:-3600} \
                --soft-time-limit=${CELERY_TASK_SOFT_TIME_LIMIT:-3300}
        elif [ "$1" = "celery-beat" ]; then
            echo "📅 Starting Celery beat scheduler..."
            mkdir -p /tmp
            exec celery -A backend beat \
                --loglevel=info \
                --pidfile=/tmp/celerybeat.pid
        else
            echo "🔧 Starting Celery command: $*"
            exec "$@"
        fi
        ;;
    
    # Everything else: no setup needed
    *)
        echo "ℹ️  Running command without setup: $*"
        exec "$@"
        ;;
esac