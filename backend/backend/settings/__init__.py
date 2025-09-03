"""
Django settings package for DeepSight application.

This package organizes settings by environment following Django best practices.
"""

import os

# Determine which settings module to use based on environment
environment = os.getenv('DJANGO_ENVIRONMENT', 'development')

if environment == 'production':
    from .production import *
elif environment == 'testing':
    from .testing import *
else:
    from .development import *