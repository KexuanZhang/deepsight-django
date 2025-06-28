"""
Retriever configurations for report generation.
"""

from typing import Dict, Any, List
from enum import Enum


class RetrieverType(Enum):
    """Supported retriever types"""
    TAVILY = "tavily"
    BRAVE = "brave"
    SERPER = "serper"
    YOU = "you"
    BING = "bing"
    DUCKDUCKGO = "duckduckgo"
    SEARXNG = "searxng"
    AZURE_AI_SEARCH = "azure_ai_search"


class RetrieverConfig:
    """Configuration for search retrievers"""
    
    @staticmethod
    def get_retriever_mapping() -> Dict[str, Any]:
        """Get mapping from string to enum values"""
        return {
            "tavily": RetrieverType.TAVILY,
            "brave": RetrieverType.BRAVE,
            "serper": RetrieverType.SERPER,
            "you": RetrieverType.YOU,
            "bing": RetrieverType.BING,
            "duckduckgo": RetrieverType.DUCKDUCKGO,
            "searxng": RetrieverType.SEARXNG,
            "azure_ai_search": RetrieverType.AZURE_AI_SEARCH,
        }
    
    @staticmethod
    def get_supported_retrievers() -> List[str]:
        """Get list of supported retriever names"""
        return [retriever.value for retriever in RetrieverType]
    
    @staticmethod
    def get_retriever_requirements() -> Dict[str, Dict[str, Any]]:
        """Get requirements for each retriever"""
        return {
            "tavily": {
                "requires_api_key": True,
                "env_var": "TAVILY_API_KEY",
                "max_results": 10,
                "supports_time_range": True,
                "supports_domains": True
            },
            "brave": {
                "requires_api_key": True,
                "env_var": "BRAVE_API_KEY",
                "max_results": 10,
                "supports_time_range": True,
                "supports_domains": False
            },
            "serper": {
                "requires_api_key": True,
                "env_var": "SERPER_API_KEY",
                "max_results": 10,
                "supports_time_range": True,
                "supports_domains": False
            },
            "you": {
                "requires_api_key": True,
                "env_var": "YOU_API_KEY",
                "max_results": 10,
                "supports_time_range": False,
                "supports_domains": False
            },
            "bing": {
                "requires_api_key": True,
                "env_var": "BING_API_KEY",
                "max_results": 10,
                "supports_time_range": True,
                "supports_domains": False
            },
            "duckduckgo": {
                "requires_api_key": False,
                "env_var": None,
                "max_results": 10,
                "supports_time_range": False,
                "supports_domains": False
            },
            "searxng": {
                "requires_api_key": False,
                "env_var": "SEARXNG_BASE_URL",
                "max_results": 10,
                "supports_time_range": False,
                "supports_domains": False
            },
            "azure_ai_search": {
                "requires_api_key": True,
                "env_var": "AZURE_AI_SEARCH_API_KEY",
                "max_results": 10,
                "supports_time_range": False,
                "supports_domains": False,
                "additional_env_vars": ["AZURE_AI_SEARCH_SERVICE_NAME", "AZURE_AI_SEARCH_INDEX_NAME"]
            }
        }
    
    @staticmethod
    def validate_retriever(retriever: str) -> bool:
        """Validate if retriever is supported"""
        return retriever in RetrieverConfig.get_supported_retrievers()
    
    @staticmethod
    def get_free_retrievers() -> List[str]:
        """Get list of retrievers that don't require API keys"""
        requirements = RetrieverConfig.get_retriever_requirements()
        return [
            name for name, config in requirements.items()
            if not config.get("requires_api_key", True)
        ]
    
    @staticmethod
    def get_time_range_mapping() -> Dict[str, Any]:
        """Get mapping for time range filters"""
        return {
            "day": "day",
            "week": "week", 
            "month": "month",
            "year": "year"
        }
    
    @staticmethod
    def get_search_depth_options() -> List[str]:
        """Get available search depth options"""
        return ["basic", "advanced"]