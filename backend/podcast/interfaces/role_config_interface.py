"""
Role Config Interface for dependency inversion.
"""

from abc import ABC, abstractmethod
from typing import Dict, List


class RoleConfigInterface(ABC):
    """Interface for role configuration implementations"""
    
    @abstractmethod
    def get_content_specific_roles(self, content_type: str) -> Dict:
        """Get role configurations specific to content type"""
        pass
    
    @abstractmethod
    def get_content_specific_prompt(self, content_type: str) -> str:
        """Get prompt template specific to content type"""
        pass
    
    @abstractmethod
    def add_content_type_config(self, content_type: str, roles: Dict, prompt_template: str):
        """Add configuration for a new content type"""
        pass
    
    @abstractmethod
    def get_supported_content_types(self) -> List[str]:
        """Get list of supported content types"""
        pass