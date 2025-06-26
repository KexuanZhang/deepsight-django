"""
Content Detector Interface for dependency inversion.
"""

from abc import ABC, abstractmethod
from typing import Dict, List


class ContentDetectorInterface(ABC):
    """Interface for content detector implementations"""
    
    @abstractmethod
    def detect_content_type(self, content: str, file_metadata: Dict) -> str:
        """Detect the type of content to adjust podcast generation strategy"""
        pass
    
    @abstractmethod
    def add_content_type(self, content_type: str, keywords: List[str]):
        """Add a new content type with its detection keywords"""
        pass
    
    @abstractmethod
    def get_supported_types(self) -> List[str]:
        """Get list of supported content types"""
        pass