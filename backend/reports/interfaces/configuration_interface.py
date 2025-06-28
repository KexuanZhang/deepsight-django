"""
Configuration Interface for dependency inversion.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from pathlib import Path


class ReportConfigurationInterface(ABC):
    """Interface for report configuration management"""
    
    @abstractmethod
    def get_model_provider_config(self, provider: str) -> Dict[str, Any]:
        """Get configuration for a specific AI model provider"""
        pass
    
    @abstractmethod
    def get_retriever_config(self, retriever: str) -> Dict[str, Any]:
        """Get configuration for a specific retriever"""
        pass
    
    @abstractmethod
    def get_generation_config(self) -> Dict[str, Any]:
        """Get general report generation configuration"""
        pass
    
    @abstractmethod
    def create_deep_report_config(self, report_data: Dict[str, Any], output_dir: Path) -> Any:
        """Create configuration object for DeepReportGenerator"""
        pass
    
    @abstractmethod
    def validate_config(self, config: Dict[str, Any]) -> Dict[str, bool]:
        """Validate all configuration components"""
        pass
    
    @abstractmethod
    def get_secrets_path(self) -> Optional[str]:
        """Get path to secrets file for API keys"""
        pass