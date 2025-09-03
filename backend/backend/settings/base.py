"""
Base Django settings for DeepSight project.

These settings are common across all environments.
For production-specific settings, see production.py
For development-specific settings, see development.py
"""

import os
from pathlib import Path
from django.core.exceptions import ImproperlyConfigured

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent.parent


def get_env_value(env_variable):
    """Get environment variable or raise exception"""
    try:
        return os.environ[env_variable]
    except KeyError:
        error_msg = f'Set the {env_variable} environment variable'
        raise ImproperlyConfigured(error_msg)


def get_env_bool(env_variable, default=False):
    """Get environment variable as boolean"""
    value = os.getenv(env_variable, str(default)).lower()
    return value in ('true', '1', 'yes', 'on')


# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.getenv('SECRET_KEY', 'django-insecure-dev-key-change-in-production')

# Host Configuration
HOST_IP = os.getenv("HOST_IP", "localhost")
BACKEND_PORT = os.getenv("BACKEND_PORT", "8000")
FRONTEND_PORT = os.getenv("FRONTEND_PORT", "5173")

# Application definition
DJANGO_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
]

THIRD_PARTY_APPS = [
    'rest_framework',
    'corsheaders',
    'drf_yasg',
    'storages',
]

LOCAL_APPS = [
    # Core applications
    'core',
    'infrastructure',
    # Feature applications
    'users',
    'notebooks',
    'reports',
    'conferences',
    'podcast',
]

INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS

MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'backend.urls'

# Custom user model
AUTH_USER_MODEL = 'users.User'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'backend.wsgi.application'

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

# Internationalization
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

# Static files (CSS, JavaScript, Images)
STATIC_URL = 'static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'

# Default primary key field type
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Django REST Framework configuration
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework.authentication.SessionAuthentication',
        'rest_framework.authentication.BasicAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
    'DEFAULT_RENDERER_CLASSES': [
        'rest_framework.renderers.JSONRenderer',
    ],
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 20,
}

# CORS configuration
CORS_ALLOW_CREDENTIALS = True
CORS_ALLOWED_ORIGINS = [
    f"http://{HOST_IP}:{FRONTEND_PORT}",
    f"http://localhost:{FRONTEND_PORT}",
]
CSRF_TRUSTED_ORIGINS = CORS_ALLOWED_ORIGINS.copy()

# Additional CORS settings
CORS_ALLOW_HEADERS = [
    'accept',
    'accept-encoding',
    'authorization',
    'content-type',
    'dnt',
    'origin',
    'user-agent',
    'x-csrftoken',
    'x-requested-with',
    'cache-control',
]

# Storage configuration
DEFAULT_STORAGE_BACKEND = 'minio'
DEFAULT_FILE_STORAGE = 'infrastructure.storage.backends.MinIOStorage'

# MinIO Configuration
MINIO_SETTINGS = {
    'ENDPOINT': os.getenv('MINIO_ENDPOINT', 'localhost:9000'),
    'ACCESS_KEY': os.getenv('MINIO_ACCESS_KEY', 'minioadmin'),
    'SECRET_KEY': os.getenv('MINIO_SECRET_KEY', 'minioadmin'),
    'BUCKET_NAME': os.getenv('MINIO_BUCKET_NAME', 'deepsight-users'),
    'SECURE': get_env_bool('MINIO_SECURE', False),
    'REGION': os.getenv('MINIO_REGION', 'us-east-1'),
}

# AWS S3 settings configured for MinIO compatibility
AWS_ACCESS_KEY_ID = MINIO_SETTINGS['ACCESS_KEY']
AWS_SECRET_ACCESS_KEY = MINIO_SETTINGS['SECRET_KEY']
AWS_STORAGE_BUCKET_NAME = MINIO_SETTINGS['BUCKET_NAME']
AWS_S3_ENDPOINT_URL = f"{'https' if MINIO_SETTINGS['SECURE'] else 'http'}://{MINIO_SETTINGS['ENDPOINT']}"
AWS_S3_REGION_NAME = MINIO_SETTINGS['REGION']
AWS_S3_USE_SSL = MINIO_SETTINGS['SECURE']
AWS_S3_VERIFY = MINIO_SETTINGS['SECURE']

# Search configuration (Milvus)
MILVUS_SETTINGS = {
    'HOST': os.getenv('MILVUS_HOST', 'localhost'),
    'PORT': os.getenv('MILVUS_PORT', '19530'),
    'COLLECTION': os.getenv('MILVUS_COLLECTION', 'user_vectors'),
}

# RagFlow Configuration
RAGFLOW_API_KEY = os.getenv('RAGFLOW_API_KEY')
RAGFLOW_BASE_URL = os.getenv('RAGFLOW_BASE_URL', 'http://localhost:9380')
RAGFLOW_DEFAULT_CHUNK_METHOD = os.getenv('RAGFLOW_CHUNK_METHOD', 'naive')
RAGFLOW_DEFAULT_EMBEDDING_MODEL = os.getenv('RAGFLOW_EMBEDDING_MODEL', 'BAAI/bge-en-v1.5')

# Celery Configuration
CELERY_BROKER_URL = os.getenv('CELERY_BROKER_URL', 'redis://localhost:6379/0')
CELERY_RESULT_BACKEND = os.getenv('CELERY_RESULT_BACKEND', 'redis://localhost:6379/0')
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = TIME_ZONE

# AI Service Configuration
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
OPENAI_ORG = os.getenv('OPENAI_ORG')
OPENAI_PROJECT = os.getenv('OPENAI_PROJECT')

# MiniMax TTS Configuration
MINIMAX_GROUP_ID = os.getenv('MINIMAX_GROUP_ID')
MINIMAX_API_KEY = os.getenv('MINIMAX_API_KEY')

# Create logs directory if it doesn't exist
LOGS_DIR = BASE_DIR / 'logs'
LOGS_DIR.mkdir(exist_ok=True)