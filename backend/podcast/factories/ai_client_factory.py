"""
Factory for creating AI client instances.
"""

from typing import Dict, Any
from ..interfaces.ai_client_interface import AIClientInterface
from ..config.podcast_config import podcast_config


class OpenAIClient(AIClientInterface):
    """OpenAI client implementation"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self._client = None
    
    @property
    def client(self):
        """Lazy initialization of OpenAI client"""
        if self._client is None:
            import openai
            
            api_key = self.config.get('api_key')
            if not api_key:
                raise ValueError("OpenAI API key is not configured")
            
            self._client = openai.OpenAI(
                api_key=api_key,
                organization=self.config.get('organization'),
                project=self.config.get('project')
            )
        return self._client
    
    def validate_provider(self) -> bool:
        """Validate OpenAI configuration"""
        try:
            _ = self.client
            return True
        except Exception:
            return False
    
    def get_model_name(self) -> str:
        """Get OpenAI model name"""
        return self.config.get('model', 'gpt-4o-mini')
    
    def create_chat_completion(self, messages, **kwargs):
        """Create chat completion using OpenAI"""
        return self.client.chat.completions.create(
            model=self.get_model_name(),
            messages=messages,
            **kwargs
        )
    
    @property
    def provider_name(self) -> str:
        return "openai"


class DeepSeekClient(AIClientInterface):
    """DeepSeek client implementation"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self._client = None
    
    @property
    def client(self):
        """Lazy initialization of DeepSeek client"""
        if self._client is None:
            import openai
            
            api_key = self.config.get('api_key')
            if not api_key:
                raise ValueError("DeepSeek API key is not configured")
            
            self._client = openai.OpenAI(
                api_key=api_key,
                base_url=self.config.get('base_url', 'https://api.deepseek.com')
            )
        return self._client
    
    def validate_provider(self) -> bool:
        """Validate DeepSeek configuration"""
        try:
            _ = self.client
            return True
        except Exception:
            return False
    
    def get_model_name(self) -> str:
        """Get DeepSeek model name"""
        return self.config.get('model', 'deepseek-chat')
    
    def create_chat_completion(self, messages, **kwargs):
        """Create chat completion using DeepSeek"""
        return self.client.chat.completions.create(
            model=self.get_model_name(),
            messages=messages,
            **kwargs
        )
    
    @property
    def provider_name(self) -> str:
        return "deepseek"


class AIClientFactory:
    """Factory for creating AI client instances"""
    
    @staticmethod
    def create_client(provider: str = None) -> AIClientInterface:
        """Create AI client based on provider"""
        config = podcast_config.get_ai_config()
        
        if provider is None:
            provider = config['provider']
        
        if provider == 'openai':
            return OpenAIClient(config['openai'])
        elif provider == 'deepseek':
            return DeepSeekClient(config['deepseek'])
        else:
            raise ValueError(f"Unknown AI provider: {provider}")
    
    @staticmethod
    def get_available_providers() -> list:
        """Get list of available AI providers"""
        return ['openai', 'deepseek']