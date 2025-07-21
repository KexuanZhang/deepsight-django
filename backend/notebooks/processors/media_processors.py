"""
Media Processors - Handle video and audio specific processing logic
"""
import os
import tempfile
import subprocess
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


class MediaProcessor:
    """Handle media-specific processing for video and audio files"""
    
    def __init__(self):
        self.logger = logging.getLogger(f"{__name__}.media_processor")
        self._whisper_model = None

    @property
    def whisper_model(self):
        """Lazy load whisper model."""
        if self._whisper_model is None:
            try:
                import faster_whisper
                device = self._detect_device()
                self._whisper_model = faster_whisper.WhisperModel("base", device=device)
                self.logger.info(f"Loaded Whisper model on {device}")
            except ImportError:
                self.logger.warning("faster-whisper not available")
                self._whisper_model = False
        return self._whisper_model

    def _detect_device(self):
        """Detect best available device."""
        try:
            import torch
            if torch.cuda.is_available():
                return "cuda"
            elif hasattr(torch.backends, 'mps') and torch.backends.mps.is_available():
                return "mps"
        except ImportError:
            pass
        return "cpu"

    async def extract_audio_from_video(self, video_path: str, output_format: str = 'wav') -> str:
        """Extract audio from video file using ffmpeg."""
        try:
            temp_audio_file = tempfile.mktemp(suffix=f'.{output_format}')
            
            cmd = [
                'ffmpeg', '-i', video_path, '-vn', '-acodec', 'pcm_s16le',
                '-ar', '16000', '-ac', '1', temp_audio_file, '-y'
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode != 0:
                raise Exception(f"FFmpeg failed: {result.stderr}")

            return temp_audio_file

        except Exception as e:
            self.logger.error(f"Audio extraction failed: {e}")
            raise

    async def transcribe_audio(self, audio_path: str) -> Dict[str, Any]:
        """Transcribe audio file using Whisper."""
        try:
            whisper_model = self.whisper_model
            if not whisper_model:
                return {
                    'transcript': '',
                    'segments': [],
                    'metadata': {'error': 'Whisper model not available'}
                }

            # Transcribe using faster-whisper
            segments, info = whisper_model.transcribe(audio_path)
            
            transcript = ""
            segment_list = []
            
            for segment in segments:
                timestamp_text = f"[{segment.start:.2f}s] {segment.text}"
                transcript += timestamp_text + "\n"
                
                segment_list.append({
                    'start': segment.start,
                    'end': segment.end,
                    'text': segment.text.strip(),
                    'probability': getattr(segment, 'avg_logprob', 0)
                })

            return {
                'transcript': transcript.strip(),
                'segments': segment_list,
                'metadata': {
                    'duration': info.duration,
                    'language': info.language,
                    'language_probability': info.language_probability,
                    'processing_method': 'faster_whisper',
                    'model': 'base'
                }
            }

        except Exception as e:
            self.logger.error(f"Audio transcription failed: {e}")
            raise

    async def extract_video_frames(self, video_path: str, interval: int = 30, output_dir: Optional[str] = None) -> Dict[str, Any]:
        """Extract frames from video at specified intervals."""
        try:
            if not output_dir:
                output_dir = tempfile.mkdtemp(suffix='_video_frames')
            
            # Create output directory if it doesn't exist
            os.makedirs(output_dir, exist_ok=True)
            
            # Extract frames using ffmpeg
            cmd = [
                'ffmpeg', '-i', video_path, '-vf', f'fps=1/{interval}',
                os.path.join(output_dir, 'frame_%04d.jpg'), '-y'
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode != 0:
                raise Exception(f"FFmpeg frame extraction failed: {result.stderr}")

            # List extracted frames
            frame_files = []
            for file in os.listdir(output_dir):
                if file.startswith('frame_') and file.endswith('.jpg'):
                    frame_files.append(os.path.join(output_dir, file))
            
            frame_files.sort()

            return {
                'output_directory': output_dir,
                'frame_files': frame_files,
                'frame_count': len(frame_files),
                'interval_seconds': interval,
                'metadata': {
                    'processing_method': 'ffmpeg_frame_extraction',
                    'output_format': 'jpg'
                }
            }

        except Exception as e:
            self.logger.error(f"Frame extraction failed: {e}")
            raise

    async def get_video_metadata(self, video_path: str) -> Dict[str, Any]:
        """Extract metadata from video file using ffprobe."""
        try:
            cmd = [
                'ffprobe', '-v', 'quiet', '-print_format', 'json',
                '-show_format', '-show_streams', video_path
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode != 0:
                raise Exception(f"FFprobe failed: {result.stderr}")

            import json
            probe_data = json.loads(result.stdout)
            
            # Extract video stream info
            video_stream = None
            audio_stream = None
            
            for stream in probe_data.get('streams', []):
                if stream.get('codec_type') == 'video' and not video_stream:
                    video_stream = stream
                elif stream.get('codec_type') == 'audio' and not audio_stream:
                    audio_stream = stream

            format_info = probe_data.get('format', {})

            metadata = {
                'duration': float(format_info.get('duration', 0)),
                'size': int(format_info.get('size', 0)),
                'format_name': format_info.get('format_name', ''),
                'bit_rate': int(format_info.get('bit_rate', 0)),
            }

            if video_stream:
                metadata.update({
                    'video_codec': video_stream.get('codec_name', ''),
                    'width': int(video_stream.get('width', 0)),
                    'height': int(video_stream.get('height', 0)),
                    'frame_rate': video_stream.get('r_frame_rate', ''),
                    'video_bitrate': int(video_stream.get('bit_rate', 0))
                })

            if audio_stream:
                metadata.update({
                    'audio_codec': audio_stream.get('codec_name', ''),
                    'audio_channels': int(audio_stream.get('channels', 0)),
                    'audio_sample_rate': int(audio_stream.get('sample_rate', 0)),
                    'audio_bitrate': int(audio_stream.get('bit_rate', 0))
                })

            return metadata

        except Exception as e:
            self.logger.error(f"Video metadata extraction failed: {e}")
            raise

    async def get_audio_metadata(self, audio_path: str) -> Dict[str, Any]:
        """Extract metadata from audio file using ffprobe."""
        try:
            cmd = [
                'ffprobe', '-v', 'quiet', '-print_format', 'json',
                '-show_format', '-show_streams', audio_path
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode != 0:
                raise Exception(f"FFprobe failed: {result.stderr}")

            import json
            probe_data = json.loads(result.stdout)
            
            format_info = probe_data.get('format', {})
            audio_stream = None
            
            for stream in probe_data.get('streams', []):
                if stream.get('codec_type') == 'audio':
                    audio_stream = stream
                    break

            metadata = {
                'duration': float(format_info.get('duration', 0)),
                'size': int(format_info.get('size', 0)),
                'format_name': format_info.get('format_name', ''),
                'bit_rate': int(format_info.get('bit_rate', 0)),
            }

            if audio_stream:
                metadata.update({
                    'codec': audio_stream.get('codec_name', ''),
                    'channels': int(audio_stream.get('channels', 0)),
                    'sample_rate': int(audio_stream.get('sample_rate', 0)),
                    'audio_bitrate': int(audio_stream.get('bit_rate', 0))
                })

            return metadata

        except Exception as e:
            self.logger.error(f"Audio metadata extraction failed: {e}")
            raise

    def cleanup_temp_files(self, *file_paths):
        """Clean up temporary files."""
        for file_path in file_paths:
            try:
                if file_path and os.path.exists(file_path):
                    if os.path.isfile(file_path):
                        os.unlink(file_path)
                    elif os.path.isdir(file_path):
                        import shutil
                        shutil.rmtree(file_path)
                    self.logger.info(f"Cleaned up temporary file/directory: {file_path}")
            except Exception as e:
                self.logger.warning(f"Failed to cleanup {file_path}: {e}") 