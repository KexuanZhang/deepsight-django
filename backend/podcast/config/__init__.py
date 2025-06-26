"""
Configuration management for podcast generation.
"""

from .podcast_config import PodcastConfig
from .role_configs import role_config_manager
from .content_detector import content_detector

__all__ = ['PodcastConfig', 'role_config_manager', 'content_detector']