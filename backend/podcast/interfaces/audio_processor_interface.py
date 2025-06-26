"""
Audio Processor Interface for dependency inversion.
"""

from abc import ABC, abstractmethod
from typing import List, Tuple


class AudioProcessorInterface(ABC):
    """Interface for audio processor implementations"""
    
    @abstractmethod
    def generate_speech_segment(self, speaker: str, text: str, output_path: str) -> str:
        """Generate speech for a single segment"""
        pass
    
    @abstractmethod  
    def merge_audio_files(self, input_paths: List[str], output_path: str) -> str:
        """Merge multiple audio files"""
        pass
    
    @abstractmethod
    def parse_conversation_segments(self, conversation_text: str) -> List[Tuple[str, str]]:
        """Parse conversation text into speaker segments"""
        pass
    
    @abstractmethod
    def generate_podcast_audio(self, conversation_text: str, output_path: str) -> str:
        """Generate complete podcast audio from conversation text"""
        pass