"""
Centralized configuration management for report generation.
"""

import os
import toml
from typing import Dict, Any, Optional
from pathlib import Path
from ..interfaces.configuration_interface import ReportConfigurationInterface


class ReportConfig(ReportConfigurationInterface):
    """Centralized configuration management for report generation"""
    
    def __init__(self):
        self._config_cache = {}
        self._secrets_cache = None
    
    def _load_secrets_toml(self) -> Dict[str, Any]:
        """Load secrets from secrets.toml file with caching"""
        if self._secrets_cache is not None:
            return self._secrets_cache
            
        secrets_path = self.get_secrets_path()
        if secrets_path and Path(secrets_path).exists():
            try:
                with open(secrets_path, 'r') as f:
                    self._secrets_cache = toml.load(f)
                    return self._secrets_cache
            except Exception as e:
                print(f"Error loading secrets.toml: {e}")
        
        self._secrets_cache = {}
        return self._secrets_cache
    
    def _get_unified_setting(self, key: str, default: Any = None) -> Any:
        """
        Get setting with unified precedence:
        1. secrets.toml (highest priority)
        2. Environment variables
        3. Default value
        """
        # 1. Check secrets.toml first
        secrets = self._load_secrets_toml()
        if key in secrets:
            return secrets[key]
        
        # 2. Check environment variables
        env_value = os.getenv(key)
        if env_value is not None:
            return env_value
        
        # 3. Return default
        return default
    
    def get_model_provider_config(self, provider: str) -> Dict[str, Any]:
        """Get configuration for a specific AI model provider"""
        cache_key = f'model_provider_{provider}'
        if cache_key not in self._config_cache:
            if provider == 'openai':
                self._config_cache[cache_key] = {
                    'api_key': self._get_unified_setting('OPENAI_API_KEY'),
                    'organization': self._get_unified_setting('OPENAI_ORG'),
                    'model': self._get_unified_setting('OPENAI_REPORT_MODEL', 'gpt-4o-mini'),
                    'temperature': 0.7,
                    'max_tokens': 4000
                }
            elif provider == 'google':
                self._config_cache[cache_key] = {
                    'api_key': self._get_unified_setting('GOOGLE_API_KEY'),
                    'model': self._get_unified_setting('GOOGLE_REPORT_MODEL', 'gemini-pro'),
                    'temperature': 0.7,
                    'max_tokens': 4000
                }
            else:
                self._config_cache[cache_key] = {}
        
        return self._config_cache[cache_key]
    
    def get_retriever_config(self, retriever: str) -> Dict[str, Any]:
        """Get configuration for a specific retriever"""
        cache_key = f'retriever_{retriever}'
        if cache_key not in self._config_cache:
            configs = {
                'tavily': {
                    'api_key': self._get_unified_setting('TAVILY_API_KEY'),
                    'search_depth': 'advanced',
                    'max_results': 10
                },
                'brave': {
                    'api_key': self._get_unified_setting('BRAVE_API_KEY'),
                    'max_results': 10
                },
                'serper': {
                    'api_key': self._get_unified_setting('SERPER_API_KEY'),
                    'max_results': 10
                },
                'you': {
                    'api_key': self._get_unified_setting('YOU_API_KEY'),
                    'max_results': 10
                },
                'bing': {
                    'api_key': self._get_unified_setting('BING_API_KEY'),
                    'max_results': 10
                },
                'duckduckgo': {
                    'max_results': 10,
                    'timeout': 30
                },
                'searxng': {
                    'base_url': self._get_unified_setting('SEARXNG_BASE_URL', 'http://localhost:8080'),
                    'max_results': 10
                },
                'azure_ai_search': {
                    'api_key': self._get_unified_setting('AZURE_AI_SEARCH_API_KEY'),
                    'service_name': self._get_unified_setting('AZURE_AI_SEARCH_SERVICE_NAME'),
                    'index_name': self._get_unified_setting('AZURE_AI_SEARCH_INDEX_NAME')
                }
            }
            self._config_cache[cache_key] = configs.get(retriever, {})
        
        return self._config_cache[cache_key]
    
    def get_generation_config(self) -> Dict[str, Any]:
        """Get general report generation configuration"""
        if 'generation_config' not in self._config_cache:
            self._config_cache['generation_config'] = {
                'default_temperature': 0.2,
                'default_top_p': 0.4,
                'max_conv_turn': 3,
                'max_perspective': 3,
                'search_top_k': 10,
                'initial_retrieval_k': 150,
                'final_context_k': 20,
                'reranker_threshold': 0.5,
                'max_thread_num': 10,
                'cache_timeout': 3600,  # 1 hour
                'job_timeout': 3600,  # 1 hour
                'cleanup_days': 7
            }
        return self._config_cache['generation_config']
    
    def create_deep_report_config(self, report_data: Dict[str, Any], output_dir: Path) -> Any:
        """Create configuration object for DeepReportGenerator"""
        # This will be implemented in the generation service
        # to avoid circular imports with report_agent
        pass
    
    def validate_config(self, config: Dict[str, Any]) -> Dict[str, bool]:
        """Validate all configuration components"""
        validation_results = {}
        
        # Validate model provider
        provider = config.get('model_provider', 'openai')
        provider_config = self.get_model_provider_config(provider)
        validation_results[f'{provider}_model'] = bool(provider_config.get('api_key'))
        
        # Validate retriever
        retriever = config.get('retriever', 'tavily')
        retriever_config = self.get_retriever_config(retriever)
        validation_results[f'{retriever}_retriever'] = bool(
            retriever_config.get('api_key') or retriever == 'duckduckgo'
        )
        
        # Validate secrets file
        validation_results['secrets_file'] = bool(self.get_secrets_path())
        
        return validation_results
    
    def get_secrets_path(self) -> Optional[str]:
        """Get path to secrets file for API keys"""
        # Check multiple possible locations
        possible_paths = [
            Path(__file__).parent.parent.parent.parent / "secrets.toml",  # backend/secrets.toml
            Path(__file__).parent.parent.parent / "agents" / "report_agent" / "secrets.toml",
        ]
        
        for path in possible_paths:
            if path.exists():
                return str(path)
        
        return None
    
    def clear_cache(self):
        """Clear configuration cache"""
        self._config_cache.clear()
    
    def setup_environment_from_secrets(self):
        """Load secrets.toml into environment variables for unified access"""
        secrets = self._load_secrets_toml()
        for key, value in secrets.items():
            if key not in os.environ:  # Don't override existing env vars
                os.environ[key] = str(value)


# Global singleton instance
report_config = ReportConfig()

# Setup environment variables from secrets.toml for unified access
report_config.setup_environment_from_secrets()