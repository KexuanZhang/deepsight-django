"""
Model provider configurations for report generation.
"""

from typing import Dict, Any, List
from enum import Enum


class ModelProvider(Enum):
    """Supported AI model providers"""
    OPENAI = "openai"
    GOOGLE = "google"


class ModelProviderConfig:
    """Configuration for AI model providers"""
    
    @staticmethod
    def get_provider_mapping() -> Dict[str, Any]:
        """Get mapping from string to enum values"""
        return {
            "openai": ModelProvider.OPENAI,
            "google": ModelProvider.GOOGLE,
        }
    
    @staticmethod
    def get_supported_providers() -> List[str]:
        """Get list of supported provider names"""
        return [provider.value for provider in ModelProvider]
    
    @staticmethod
    def get_default_models() -> Dict[str, str]:
        """Get default models for each provider"""
        return {
            "openai": "gpt-4o-mini",
            "google": "gemini-pro",
        }
    
    @staticmethod
    def get_model_limits() -> Dict[str, Dict[str, int]]:
        """Get token limits for different models"""
        return {
            "gpt-4o-mini": {"max_tokens": 128000, "output_tokens": 16384},
            "gpt-4o": {"max_tokens": 128000, "output_tokens": 16384},
            "gpt-3.5-turbo": {"max_tokens": 16385, "output_tokens": 4096},
            "gemini-pro": {"max_tokens": 32768, "output_tokens": 8192},
            "gemini-1.5-pro": {"max_tokens": 2097152, "output_tokens": 8192},
        }
    
    @staticmethod
    def validate_provider(provider: str) -> bool:
        """Validate if provider is supported"""
        return provider in ModelProviderConfig.get_supported_providers()
    
    @staticmethod
    def get_provider_requirements(provider: str) -> Dict[str, Any]:
        """Get requirements for a specific provider"""
        requirements = {
            "openai": {
                "required_env_vars": ["OPENAI_API_KEY"],
                "optional_env_vars": ["OPENAI_ORG", "OPENAI_PROJECT"],
                "default_temperature": 0.7,
                "default_max_tokens": 4000
            },
            "google": {
                "required_env_vars": ["GOOGLE_API_KEY"],
                "optional_env_vars": [],
                "default_temperature": 0.7,
                "default_max_tokens": 4000
            }
        }
        return requirements.get(provider, {})