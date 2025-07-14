"""
MinIO configuration settings for Django.
Add these settings to your Django settings.py file.
"""

# MinIO Configuration
MINIO_SETTINGS = {
    'ENDPOINT': 'localhost:9000',  # MinIO server endpoint
    'ACCESS_KEY': 'minioadmin',     # MinIO access key
    'SECRET_KEY': 'minioadmin',     # MinIO secret key  
    'BUCKET_NAME': 'deepsight-storage',  # Bucket name for file storage
    'SECURE': False,                # Use HTTPS (set to True for production)
    'REGION': 'us-east-1',         # AWS region (for compatibility)
}

# Storage Backend Selection
STORAGE_BACKEND = 'minio'  # Options: 'minio', 'local' (for backward compatibility)

# For production deployment, these should be environment variables:
"""
import os

MINIO_SETTINGS = {
    'ENDPOINT': os.getenv('MINIO_ENDPOINT', 'localhost:9000'),
    'ACCESS_KEY': os.getenv('MINIO_ACCESS_KEY', 'minioadmin'),
    'SECRET_KEY': os.getenv('MINIO_SECRET_KEY', 'minioadmin'),
    'BUCKET_NAME': os.getenv('MINIO_BUCKET_NAME', 'deepsight-storage'),
    'SECURE': os.getenv('MINIO_SECURE', 'False').lower() == 'true',
    'REGION': os.getenv('MINIO_REGION', 'us-east-1'),
}

STORAGE_BACKEND = os.getenv('STORAGE_BACKEND', 'minio')
"""

# Example environment variables for docker-compose:
"""
environment:
  - MINIO_ENDPOINT=minio:9000
  - MINIO_ACCESS_KEY=deepsight_access_key
  - MINIO_SECRET_KEY=deepsight_secret_key_123
  - MINIO_BUCKET_NAME=deepsight-storage
  - MINIO_SECURE=false
  - MINIO_REGION=us-east-1
  - STORAGE_BACKEND=minio
"""