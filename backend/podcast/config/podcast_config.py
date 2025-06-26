"""
Configuration management for podcast generation.
"""

import os
from typing import Dict, Any, Optional
from django.conf import settings


class PodcastConfig:
    """Centralized configuration management for podcast generation"""
    
    def __init__(self):
        self._config_cache = {}
    
    def get_ai_config(self) -> Dict[str, Any]:
        """Get AI provider configuration"""
        if 'ai_config' not in self._config_cache:
            self._config_cache['ai_config'] = {
                'provider': self._get_setting('PODCAST_AI_PROVIDER', 'openai').lower(),
                'openai': {
                    'api_key': self._get_setting('OPENAI_API_KEY', required=False),
                    'organization': self._get_setting('OPENAI_ORG', required=False),
                    'project': self._get_setting('OPENAI_PROJECT', required=False),
                    'model': self._get_setting('OPENAI_MODEL', 'gpt-4o-mini'),
                },
                'deepseek': {
                    'api_key': self._get_setting('DEEPSEEK_API_KEY', required=False),
                    'model': self._get_setting('DEEPSEEK_MODEL', 'deepseek-chat'),
                    'base_url': 'https://api.deepseek.com'
                }
            }
        return self._config_cache['ai_config']
    
    def get_audio_config(self) -> Dict[str, Any]:
        """Get audio processing configuration"""
        if 'audio_config' not in self._config_cache:
            self._config_cache['audio_config'] = {
                'minimax': {
                    'group_id': self._get_setting('MINIMAX_GROUP_ID', required=False),
                    'api_key': self._get_setting('MINIMAX_API_KEY', required=False),
                    'model': 'speech-02-turbo',
                    'base_url': 'https://api.minimax.io/v1/t2a_v2'
                },
                'audio_settings': {
                    'sample_rate': 32000,
                    'bitrate': 128000,
                    'format': 'mp3',
                    'channel': 1,
                    'tempo': 1.2
                },
                'voice_mapping': {
                    'Yang': 'Chinese (Mandarin)_Wise_Women',
                    '杨飞飞': 'Chinese (Mandarin)_Wise_Women',
                    'Oliver': 'Chinese (Mandarin)_Reliable_Executive',
                    '奥立昆': 'Chinese (Mandarin)_Reliable_Executive',
                    'Liman': 'Chinese (Mandarin)_Humorous_Elder',
                    '李特曼': 'Chinese (Mandarin)_Humorous_Elder',
                }
            }
        return self._config_cache['audio_config']
    
    def get_redis_config(self) -> Dict[str, Any]:
        """Get Redis configuration"""
        if 'redis_config' not in self._config_cache:
            self._config_cache['redis_config'] = {
                'url': getattr(settings, 'CELERY_BROKER_URL', 'redis://localhost:6379/0'),
                'status_ttl': 300  # 5 minutes
            }
        return self._config_cache['redis_config']
    
    def get_conversation_config(self) -> Dict[str, Any]:
        """Get conversation generation configuration"""
        if 'conversation_config' not in self._config_cache:
            self._config_cache['conversation_config'] = {
                'max_words': 15000,
                'temperature': 0.3,
                'max_tokens': 5000,
                'presence_penalty': 0.1,
                'frequency_penalty': 0.1,
                'system_prompt': "你是一位专业的技术内容生成专家，专门从事研究分析和创新评估。请生成实质性的、技术严谨的播客讨论，重点关注具体细节、方法论洞察和实际意义。避免废话，始终保持专业的技术话语。所有内容都必须用中文生成。"
            }
        return self._config_cache['conversation_config']
    
    def _get_setting(self, key: str, default: Any = None, required: bool = True) -> Any:
        """Get setting from Django settings or environment"""
        value = getattr(settings, key, None) or os.getenv(key, default)
        if required and value is None:
            raise ValueError(f"Required setting {key} is not configured")
        return value
    
    def validate_config(self) -> Dict[str, bool]:
        """Validate all configurations"""
        validation_results = {}
        
        # Validate AI config
        ai_config = self.get_ai_config()
        provider = ai_config['provider']
        
        if provider == 'openai':
            validation_results['openai'] = bool(ai_config['openai']['api_key'])
        elif provider == 'deepseek':
            validation_results['deepseek'] = bool(ai_config['deepseek']['api_key'])
        
        # Validate audio config
        audio_config = self.get_audio_config()
        validation_results['minimax'] = bool(
            audio_config['minimax']['group_id'] and 
            audio_config['minimax']['api_key']
        )
        
        return validation_results
    
    def clear_cache(self):
        """Clear configuration cache"""
        self._config_cache.clear()


# Global singleton instance
podcast_config = PodcastConfig()