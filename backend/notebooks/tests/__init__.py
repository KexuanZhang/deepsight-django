"""
Tests package for the notebooks module.

This package contains focused test modules:
- test_models.py: Model tests
- test_serializers.py: Serializer tests  
- test_views.py: View tests
- test_services.py: Service tests
- test_tasks.py: Task tests
- test_validators.py: Validator tests
"""

# Import all test modules for test discovery
from .test_models import *
from .test_serializers import *
from .test_views import *
from .test_services import *
from .test_tasks import *
from .test_validators import * 