"""
Django settings for testing environment.
"""

from .base import *

# Testing configuration
DEBUG = False

ALLOWED_HOSTS = ['testserver', 'localhost', '127.0.0.1']

# Test database configuration (in-memory SQLite for speed)
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': ':memory:',
    }
}

# Disable migrations during testing for speed
class DisableMigrations:
    def __contains__(self, item):
        return True
    
    def __getitem__(self, item):
        return None

MIGRATION_MODULES = DisableMigrations()

# Fast password hashing for tests
PASSWORD_HASHERS = [
    'django.contrib.auth.hashers.MD5PasswordHasher',
]

# Test logging - minimal logging to avoid cluttering test output
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'null': {
            'class': 'logging.NullHandler',
        },
    },
    'root': {
        'handlers': ['null'],
    },
}

# Test cache - use dummy cache
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.dummy.DummyCache',
    }
}

# Email backend for testing
EMAIL_BACKEND = 'django.core.mail.backends.locmem.EmailBackend'

# Disable Celery during testing
CELERY_TASK_ALWAYS_EAGER = True
CELERY_TASK_EAGER_PROPAGATES = True

# Test-specific CORS settings
CORS_ALLOW_ALL_ORIGINS = True

# Test storage settings - use in-memory storage when possible
# For MinIO tests, use a test bucket
MINIO_SETTINGS.update({
    'BUCKET_NAME': 'test-bucket',
})

# Disable some middleware for faster tests
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
]

# Test media handling
MEDIA_URL = '/test-media/'
MEDIA_ROOT = BASE_DIR / 'test-media'

# Speed up tests by reducing some limits
REST_FRAMEWORK.update({
    'PAGE_SIZE': 10,  # Smaller page size for tests
})

# Disable some security features that slow down tests
SESSION_COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False
SECURE_SSL_REDIRECT = False