"""
Interfaces for podcast generation components.
"""

from .ai_client_interface import AIClientInterface
from .audio_processor_interface import AudioProcessorInterface
from .content_detector_interface import ContentDetectorInterface
from .role_config_interface import RoleConfigInterface

__all__ = [
    'AIClientInterface',
    'AudioProcessorInterface', 
    'ContentDetectorInterface',
    'RoleConfigInterface'
]