"""
Factory for creating audio processor instances.
"""

from typing import Dict, Any
from ..interfaces.audio_processor_interface import AudioProcessorInterface
from ..config.podcast_config import podcast_config


class MiniMaxAudioProcessor(AudioProcessorInterface):
    """MiniMax TTS audio processor implementation"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.minimax_config = config['minimax']
        self.audio_settings = config['audio_settings']
        self.voice_mapping = config['voice_mapping']
    
    def generate_speech_segment(self, speaker: str, text: str, output_path: str) -> str:
        """Generate speech for a single segment using MiniMax TTS API"""
        import json
        import requests
        
        # Get voice, default to first available voice if speaker not found
        voice = self.voice_mapping.get(speaker.strip(), "Chinese (Mandarin)_Wise_Women")
        
        group_id = self.minimax_config.get('group_id')
        api_key = self.minimax_config.get('api_key')
        
        if not group_id or not api_key:
            raise ValueError("MiniMax credentials are not configured")
        
        url = f"https://api.minimax.io/v1/t2a_v2?GroupId={group_id}"
        
        payload = json.dumps({
            "model": self.minimax_config.get('model', 'speech-02-turbo'),
            "text": text,
            "stream": False,
            "voice_setting": {
                "voice_id": voice,
                "speed": 1,
                "vol": 1,
                "pitch": 0,
            },
            "audio_setting": {
                "sample_rate": self.audio_settings['sample_rate'],
                "bitrate": self.audio_settings['bitrate'],
                "format": self.audio_settings['format'],
                "channel": self.audio_settings['channel'],
            },
        })
        
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }
        
        response = requests.post(url, headers=headers, data=payload)
        response.raise_for_status()
        
        parsed_json = response.json()
        
        if "data" not in parsed_json or "audio" not in parsed_json["data"]:
            raise ValueError(f"Invalid response from MiniMax API: {parsed_json}")
        
        # Get audio data and decode from hex
        audio_value = bytes.fromhex(parsed_json["data"]["audio"])
        
        # Save audio to output path
        with open(output_path, "wb") as f:
            f.write(audio_value)
        
        return output_path
    
    def merge_audio_files(self, input_paths: list, output_path: str) -> str:
        """Merge multiple audio files using ffmpeg-python"""
        import ffmpeg
        
        if not input_paths:
            raise ValueError("No input audio files to merge.")
        
        if len(input_paths) == 1:
            # Only one file, just copy it to output
            ffmpeg.input(input_paths[0]).output(output_path).run(overwrite_output=True)
            return output_path
        
        # Concatenate all input files
        inputs = [ffmpeg.input(p) for p in input_paths]
        concat = ffmpeg.concat(*inputs, v=0, a=1).node
        audio = concat[0].filter('atempo', self.audio_settings['tempo'])
        out = ffmpeg.output(audio, output_path)
        out = out.global_args('-y')  # Overwrite output
        out.run(overwrite_output=True)
        return output_path
    
    def parse_conversation_segments(self, conversation_text: str):
        """Parse conversation text into speaker segments"""
        import re
        
        # Updated pattern to match XML-style tags like <Yang>text</Yang>
        pattern = r"<([^/>][^>]*)>(.*?)(?=<[^/>][^>]*>|</[^>]*>|$)"
        matches = re.findall(pattern, conversation_text, re.DOTALL)
        
        # Filter out empty matches and closing tags
        filtered_matches = []
        for speaker, content in matches:
            content = content.strip()
            if content and not speaker.startswith("/"):
                filtered_matches.append((speaker, content))
        
        if not filtered_matches:
            # Fallback: try to match simple speaker format like "Speaker: text"
            pattern_fallback = r"([^:]+):\s*(.*?)(?=\n[^:]+:|$)"
            fallback_matches = re.findall(pattern_fallback, conversation_text, re.DOTALL)
            filtered_matches = [
                (speaker.strip(), content.strip())
                for speaker, content in fallback_matches
                if content.strip()
            ]
        
        if not filtered_matches:
            raise ValueError("No speaker segments found in conversation text")
        
        return filtered_matches
    
    def generate_podcast_audio(self, conversation_text: str, output_path: str) -> str:
        """Generate complete podcast audio from conversation text"""
        import tempfile
        import os
        
        # Parse conversation into segments
        segments = self.parse_conversation_segments(conversation_text)
        
        # Create temporary directory for segments
        temp_dir = tempfile.mkdtemp()
        segment_paths = []
        
        try:
            # Generate audio for each segment
            for i, (speaker, content) in enumerate(segments):
                if content:  # Only generate if there's content
                    segment_path = os.path.join(temp_dir, f"segment_{i:03d}.mp3")
                    self.generate_speech_segment(speaker, content, segment_path)
                    segment_paths.append(segment_path)
            
            # Merge all segments
            self.merge_audio_files(segment_paths, output_path)
            return output_path
        
        finally:
            # Clean up temporary files
            for path in segment_paths:
                if os.path.exists(path):
                    os.unlink(path)
            if os.path.exists(temp_dir):
                os.rmdir(temp_dir)


class AudioProcessorFactory:
    """Factory for creating audio processor instances"""
    
    @staticmethod
    def create_processor(provider: str = 'minimax') -> AudioProcessorInterface:
        """Create audio processor based on provider"""
        config = podcast_config.get_audio_config()
        
        if provider == 'minimax':
            return MiniMaxAudioProcessor(config)
        else:
            raise ValueError(f"Unknown audio processor provider: {provider}")
    
    @staticmethod
    def get_available_providers() -> list:
        """Get list of available audio processor providers"""
        return ['minimax']