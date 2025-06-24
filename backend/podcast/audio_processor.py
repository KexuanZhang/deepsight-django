"""
Audio processing module for podcast generation.

This module handles text-to-speech conversion, audio file merging,
and audio processing operations using MiniMax TTS.
"""

import os
import json
import tempfile
import subprocess
import requests
import logging
import re
from typing import List
from pathlib import Path
from django.conf import settings

logger = logging.getLogger(__name__)


class AudioProcessor:
    """Handles audio generation and processing for podcast creation"""

    def __init__(self):
        self.audio_dir = Path(settings.MEDIA_ROOT) / "podcasts" / "audio"
        self.audio_dir.mkdir(parents=True, exist_ok=True)

    def generate_speech_segment(self, speaker: str, text: str, output_path: str) -> str:
        """Generate speech for a single segment using MiniMax TTS API"""
        try:
            # Map speakers to MiniMax voice IDs (handle both English and Chinese names)
            voice_mapping = {
                "Yang": "Chinese (Mandarin)_Wise_Women",
                "杨飞飞": "Chinese (Mandarin)_Wise_Women",
                "Oliver": "Chinese (Mandarin)_Reliable_Executive",
                "奥立昆": "Chinese (Mandarin)_Reliable_Executive",
                "Liman": "Chinese (Mandarin)_Humorous_Elder",
                "李特曼": "Chinese (Mandarin)_Humorous_Elder",
            }

            # Get voice, default to first available voice if speaker not found
            voice = voice_mapping.get(speaker.strip(), "Chinese (Mandarin)_Wise_Women")

            logger.info(f"Using voice '{voice}' for speaker '{speaker}'")

            # Check for required MiniMax credentials
            minimax_group_id = getattr(settings, "MINIMAX_GROUP_ID", None) or os.getenv(
                "MINIMAX_GROUP_ID"
            )
            minimax_api_key = getattr(settings, "MINIMAX_API_KEY", None) or os.getenv(
                "MINIMAX_API_KEY"
            )

            if not minimax_group_id or not minimax_api_key:
                raise ValueError(
                    "MiniMax credentials are not configured. Please set MINIMAX_GROUP_ID and MINIMAX_API_KEY."
                )

            url = f"https://api.minimax.io/v1/t2a_v2?GroupId={minimax_group_id}"

            payload = json.dumps(
                {
                    "model": "speech-02-hd",
                    "text": text,
                    "stream": False,
                    "voice_setting": {
                        "voice_id": voice,
                        "speed": 1,
                        "vol": 1,
                        "pitch": 0,
                    },
                    "audio_setting": {
                        "sample_rate": 32000,
                        "bitrate": 128000,
                        "format": "mp3",
                        "channel": 1,
                    },
                }
            )

            headers = {
                "Authorization": f"Bearer {minimax_api_key}",
                "Content-Type": "application/json",
            }

            response = requests.post(url, headers=headers, data=payload)
            response.raise_for_status()

            parsed_json = response.json()

            # Check if the response contains audio data
            if "data" not in parsed_json or "audio" not in parsed_json["data"]:
                raise ValueError(f"Invalid response from MiniMax API: {parsed_json}")

            # Get audio data and decode from hex
            audio_value = bytes.fromhex(parsed_json["data"]["audio"])

            # Save audio to output path
            with open(output_path, "wb") as f:
                f.write(audio_value)

            return output_path

        except Exception as e:
            logger.error(f"Error generating speech for speaker {speaker}: {e}")
            raise

    def merge_audio_files(self, input_paths: List[str], output_path: str) -> str:
        """Merge multiple audio files using ffmpeg"""
        try:
            # Create temporary file list for ffmpeg
            with tempfile.NamedTemporaryFile(
                mode="w", suffix=".txt", delete=False
            ) as f:
                for path in input_paths:
                    f.write(f"file '{path}'\n")
                filelist_path = f.name

            # Merge files
            temp_merged = output_path.replace(".mp3", "_temp.mp3")
            cmd = [
                "ffmpeg",
                "-f",
                "concat",
                "-safe",
                "0",
                "-i",
                filelist_path,
                "-c",
                "copy",
                temp_merged,
            ]
            subprocess.run(cmd, check=True, capture_output=True)

            # Apply speed adjustment
            cmd = ["ffmpeg", "-i", temp_merged, "-filter:a", "atempo=1.2", output_path]
            subprocess.run(cmd, check=True, capture_output=True)

            # Clean up temporary files
            os.unlink(filelist_path)
            os.unlink(temp_merged)

            return output_path

        except Exception as e:
            logger.error(f"Error merging audio files: {e}")
            raise

    def parse_conversation_segments(self, conversation_text: str):
        """Parse conversation text into speaker segments"""
        # Updated pattern to match XML-style tags like <Yang>text</Yang>
        pattern = r"<([^/>][^>]*)>(.*?)(?=<[^/>][^>]*>|</[^>]*>|$)"
        matches = re.findall(pattern, conversation_text, re.DOTALL)

        # Filter out empty matches and closing tags
        filtered_matches = []
        for speaker, content in matches:
            content = content.strip()
            if content and not speaker.startswith(
                "/"
            ):  # Skip empty content and closing tags
                filtered_matches.append((speaker, content))

        if not filtered_matches:
            # Fallback: try to match simple speaker format like "Speaker: text"
            pattern_fallback = r"([^:]+):\s*(.*?)(?=\n[^:]+:|$)"
            fallback_matches = re.findall(
                pattern_fallback, conversation_text, re.DOTALL
            )
            filtered_matches = [
                (speaker.strip(), content.strip())
                for speaker, content in fallback_matches
                if content.strip()
            ]

        if not filtered_matches:
            logger.error(
                f"No speaker segments found. Text format: {conversation_text[:200]}..."
            )
            raise ValueError(
                f"No speaker segments found in conversation text. Format may be incorrect."
            )

        logger.info(f"Found {len(filtered_matches)} speaker segments")
        return filtered_matches

    def generate_podcast_audio(self, conversation_text: str, output_path: str) -> str:
        """Generate complete podcast audio from conversation text"""
        try:
            # Parse conversation into segments
            filtered_matches = self.parse_conversation_segments(conversation_text)

            # Create temporary directory for segments
            temp_dir = tempfile.mkdtemp()
            segment_paths = []

            try:
                # Generate audio for each segment
                for i, (speaker, content) in enumerate(filtered_matches):
                    speaker = speaker.strip()
                    content = content.strip()

                    if content:  # Only generate if there's content
                        logger.info(
                            f"Processing segment {i + 1}/{len(filtered_matches)} for {speaker} ({len(content)} chars)"
                        )
                        segment_path = os.path.join(temp_dir, f"segment_{i:03d}.mp3")
                        self.generate_speech_segment(speaker, content, segment_path)
                        segment_paths.append(segment_path)
                        logger.info(
                            f"Completed segment {i + 1}/{len(filtered_matches)}"
                        )

                logger.info(f"Merging {len(segment_paths)} audio segments")
                # Merge all segments
                self.merge_audio_files(segment_paths, output_path)
                logger.info(f"Audio generation completed: {output_path}")

                return output_path

            finally:
                # Clean up temporary files
                for path in segment_paths:
                    if os.path.exists(path):
                        os.unlink(path)
                if os.path.exists(temp_dir):
                    os.rmdir(temp_dir)

        except Exception as e:
            logger.error(f"Error generating podcast audio: {e}")
            raise


# Global singleton instance
audio_processor = AudioProcessor()
