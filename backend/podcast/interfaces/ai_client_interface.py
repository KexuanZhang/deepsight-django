"""
AI Client Interface for dependency inversion.
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any


class AIClientInterface(ABC):
    """Interface for AI client implementations"""
    
    @abstractmethod
    def validate_provider(self) -> bool:
        """Validate that the AI provider is available and properly configured"""
        pass
    
    @abstractmethod
    def get_model_name(self) -> str:
        """Get the model name for the current provider"""
        pass
    
    @abstractmethod
    def create_chat_completion(self, messages: List[Dict[str, str]], **kwargs) -> Any:
        """Create a chat completion using the configured AI provider"""
        pass
    
    @property  
    @abstractmethod
    def provider_name(self) -> str:
        """Get the name of the AI provider"""
        pass