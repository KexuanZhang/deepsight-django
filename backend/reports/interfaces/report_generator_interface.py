"""
Report Generator Interface for dependency inversion.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any
from pathlib import Path


class ReportGeneratorInterface(ABC):
    """Interface for report generator implementations"""
    
    @abstractmethod
    def validate_configuration(self, config: Dict[str, Any]) -> bool:
        """Validate that the configuration is correct for report generation"""
        pass
    
    @abstractmethod
    def generate_report(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Generate a report based on the provided configuration"""
        pass
    
    @abstractmethod
    def get_supported_providers(self) -> Dict[str, Any]:
        """Get information about supported AI providers and retrievers"""
        pass
    
    @abstractmethod
    def cancel_generation(self, job_id: str) -> bool:
        """Cancel an ongoing report generation if possible"""
        pass
    
    @property
    @abstractmethod
    def generator_name(self) -> str:
        """Get the name of the report generator"""
        pass