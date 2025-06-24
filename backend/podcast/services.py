"""
Podcast generation service for Django backend.

This service handles:
- Podcast conversation generation using OpenAI
- Text-to-speech conversion
- Audio file merging and processing
- Django model integration
"""

import uuid
import logging
import asyncio
import os
import json
import tempfile
import subprocess
import requests
import redis
from typing import Dict, Optional, List, Any
from datetime import datetime, timezone
from pathlib import Path
import shutil
from django.conf import settings
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage

import openai
import aiofiles

from .models import PodcastJob

logger = logging.getLogger(__name__)

class PodcastGenerationService:
    """Service for generating podcasts from parsed content using OpenAI"""
    
    def __init__(self):
        # OpenAI client (lazy initialization to avoid startup errors)
        self._openai_client = None
        
        # Redis client for caching status updates
        self._redis_client = None
        
        # Audio output directory
        self.audio_dir = Path(settings.MEDIA_ROOT) / "podcasts" / "audio"
        self.audio_dir.mkdir(parents=True, exist_ok=True)
    
    @property
    def redis_client(self):
        """Lazy initialization of Redis client."""
        if self._redis_client is None:
            try:
                self._redis_client = redis.Redis.from_url(settings.CELERY_BROKER_URL)
                # Test connection
                self._redis_client.ping()
            except Exception as e:
                logger.warning(f"Redis connection failed, caching disabled: {e}")
                self._redis_client = None
        return self._redis_client
    
    @property
    def openai_client(self):
        """Lazy initialization of OpenAI client."""
        if self._openai_client is None:
            openai_api_key = getattr(settings, 'OPENAI_API_KEY', None) or os.getenv('OPENAI_API_KEY')
            if not openai_api_key:
                raise ValueError("OpenAI API key is not configured. Please set OPENAI_API_KEY in settings or environment.")
            
            self._openai_client = openai.OpenAI(
                api_key=openai_api_key,
                organization=getattr(settings, 'OPENAI_ORG', None) or os.getenv('OPENAI_ORG'),
                project=getattr(settings, 'OPENAI_PROJECT', None) or os.getenv('OPENAI_PROJECT')
            )
        return self._openai_client

    async def generate_podcast_conversation(self, content: str, file_metadata: Dict) -> str:
        """Generate podcast conversation from content using OpenAI"""
        try:
            # Truncate content to first 15,000 words like in the original
            words = content.split()
            truncated_content = " ".join(words[:15000]) if len(words) > 15000 else content
            
            # 角色特征预埋配置
            role_context = {
                "Yang": {
                    "角色职责": "主持人",
                    "说话风格": "生活类比",
                    "反问频率": 0.6,  # 60%的发言包含反问句
                    "开场白特征": "欢迎来到深度解析，今天我们将拆解这篇颠覆性论文..."
                },
                "Oliver": {
                    "角色职责": "领域专家",
                    "数据引用": "必带统计",
                    "技术术语密度": 0.8,  # 80%的发言包含技术术语
                    "深度分析特征": "这个创新点本质上是将Transformer的注意力机制重构为..."
                },
                "Liman": {
                    "反驳触发词": "不过",
                    "质疑强度": 0.7,  # 70%的发言包含质疑观点
                    "行业视角特征": "医疗领域应用时可能遇到伦理挑战，比如..."
                }
            }
            
            # 将角色特征转换为自然语言指令
            role_instructions = "\n".join(
                [f"- {name}: {', '.join([f'{k}={v}' for k, v in traits.items()])}" 
                for name, traits in role_context.items()]
            )
            
            # 构建动态Prompt
            prompt = f"""
            ## 角色特征设定（严格遵循）
            {role_instructions}
            
            ## 对话生成规则
            1. 根据[反问频率]参数控制反问句使用密度
            2. 按照[技术术语密度]参数混合专业术语与通俗表达
            3. [反驳触发词]必须出现在李特曼的质疑观点开头
            4. 杨飞飞需使用[开场白特征]模板开启对话
            5. 奥立昆在关键论点处必须体现[深度分析特征]
            6. 李特曼在讨论应用场景时需结合[行业视角特征]
            
            ## 对话结构
            <Yang>{role_context['Yang']['开场白特征']}</Yang>
            ...（后续对话）...
            
            ## 论文内容
            <Paper>{truncated_content}</Paper>
            """
            
            # 添加风格强化指令
            prompt += """
            ## 自然语言增强要求
            - 每3轮对话插入1次自然打断（如"抱歉打断，这里补充..."）
            - 技术解释后添加"用大白话说就是..."的转换说明
            - 关键数据呈现时使用"您可能没想到..."等引导语
            - 专家观点交锋时使用"我部分同意，但..."等过渡
            - 整体把握：快速切入重点，讨论问题深入浅出
            """
            
            response = self.openai_client.chat.completions.create(
                messages=[{
                    "role": "user",
                    "content": prompt,
                    "temperature": 0.7
                }],
                model="gpt-4-turbo",
                max_tokens=4000
            )
            
            conversation = response.choices[0].message.content
            logger.info(f"Generated conversation with {len(conversation)} characters")
            return conversation
            
        except Exception as e:
            logger.error(f"Error generating conversation: {e}")
            raise

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
                "李特曼": "Chinese (Mandarin)_Humorous_Elder"
            }
            
            # Get voice, default to first available voice if speaker not found
            voice = voice_mapping.get(speaker.strip(), "Chinese (Mandarin)_Wise_Women")
            
            logger.info(f"Using voice '{voice}' for speaker '{speaker}'")
            
            # Check for required MiniMax credentials
            minimax_group_id = getattr(settings, 'MINIMAX_GROUP_ID', None) or os.getenv('MINIMAX_GROUP_ID')
            minimax_api_key = getattr(settings, 'MINIMAX_API_KEY', None) or os.getenv('MINIMAX_API_KEY')
            
            if not minimax_group_id or not minimax_api_key:
                raise ValueError("MiniMax credentials are not configured. Please set MINIMAX_GROUP_ID and MINIMAX_API_KEY.")
            
            url = f"https://api.minimax.io/v1/t2a_v2?GroupId={minimax_group_id}"
            
            payload = json.dumps({
                "model": "speech-02-hd",
                "text": text,
                "stream": False,
                "voice_setting": {
                    "voice_id": voice,
                    "speed": 1,
                    "vol": 1,
                    "pitch": 0
                },
                "audio_setting": {
                    "sample_rate": 32000,
                    "bitrate": 128000,
                    "format": "mp3",
                    "channel": 1
                }
            })
            
            headers = {
                'Authorization': f'Bearer {minimax_api_key}',
                'Content-Type': 'application/json'
            }
            
            response = requests.post(url, headers=headers, data=payload)
            response.raise_for_status()
            
            parsed_json = response.json()
            
            # Check if the response contains audio data
            if 'data' not in parsed_json or 'audio' not in parsed_json['data']:
                raise ValueError(f"Invalid response from MiniMax API: {parsed_json}")
            
            # Get audio data and decode from hex
            audio_value = bytes.fromhex(parsed_json['data']['audio'])
            
            # Save audio to output path
            with open(output_path, 'wb') as f:
                f.write(audio_value)

            return output_path
            
        except Exception as e:
            logger.error(f"Error generating speech for speaker {speaker}: {e}")
            raise

    def merge_audio_files(self, input_paths: List[str], output_path: str) -> str:
        """Merge multiple audio files using ffmpeg"""
        try:
            # Create temporary file list for ffmpeg
            with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
                for path in input_paths:
                    f.write(f"file '{path}'\n")
                filelist_path = f.name
            
            # Merge files
            temp_merged = output_path.replace('.mp3', '_temp.mp3')
            cmd = [
                'ffmpeg', '-f', 'concat', '-safe', '0', 
                '-i', filelist_path, '-c', 'copy', temp_merged
            ]
            subprocess.run(cmd, check=True, capture_output=True)
            
            # Apply speed adjustment
            cmd = [
                'ffmpeg', '-i', temp_merged, 
                '-filter:a', 'atempo=1.2', 
                output_path
            ]
            subprocess.run(cmd, check=True, capture_output=True)
            
            # Clean up temporary files
            os.unlink(filelist_path)
            os.unlink(temp_merged)
            
            return output_path
            
        except Exception as e:
            logger.error(f"Error merging audio files: {e}")
            raise

    def generate_podcast_audio(self, conversation_text: str, output_path: str) -> str:
        """Generate complete podcast audio from conversation text"""
        try:
            # Parse conversation into segments - match any speaker tags
            import re
            # Updated pattern to match XML-style tags like <Yang>text</Yang>
            pattern = r'<([^/>][^>]*)>(.*?)(?=<[^/>][^>]*>|</[^>]*>|$)'
            matches = re.findall(pattern, conversation_text, re.DOTALL)
            
            # Filter out empty matches and closing tags
            filtered_matches = []
            for speaker, content in matches:
                content = content.strip()
                if content and not speaker.startswith('/'):  # Skip empty content and closing tags
                    filtered_matches.append((speaker, content))
            
            if not filtered_matches:
                # Fallback: try to match simple speaker format like "Speaker: text"
                pattern_fallback = r'([^:]+):\s*(.*?)(?=\n[^:]+:|$)'
                fallback_matches = re.findall(pattern_fallback, conversation_text, re.DOTALL)
                filtered_matches = [(speaker.strip(), content.strip()) for speaker, content in fallback_matches if content.strip()]
                
            if not filtered_matches:
                logger.error(f"No speaker segments found. Text format: {conversation_text[:200]}...")
                raise ValueError(f"No speaker segments found in conversation text. Format may be incorrect.")
            
            logger.info(f"Found {len(filtered_matches)} speaker segments")
            
            # Create temporary directory for segments
            temp_dir = tempfile.mkdtemp()
            segment_paths = []
            
            try:
                # Generate audio for each segment
                for i, (speaker, content) in enumerate(filtered_matches):
                    speaker = speaker.strip()
                    content = content.strip()
                    
                    if content:  # Only generate if there's content
                        logger.info(f"Processing segment {i+1}/{len(filtered_matches)} for {speaker} ({len(content)} chars)")
                        segment_path = os.path.join(temp_dir, f"segment_{i:03d}.mp3")
                        self.generate_speech_segment(speaker, content, segment_path)
                        segment_paths.append(segment_path)
                        logger.info(f"Completed segment {i+1}/{len(filtered_matches)}")
                
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

    def create_podcast_job(self, source_file_ids: List[str], job_metadata: Dict, user=None) -> PodcastJob:
        """Create a new podcast generation job"""
        try:
            # Create job instance
            job = PodcastJob.objects.create(
                user=user,
                title=job_metadata.get("title", "Generated Podcast"),
                description=job_metadata.get("description", ""),
                source_file_ids=source_file_ids,
                source_metadata=job_metadata.get("source_metadata", {}),
                status="pending",
                progress="Job queued for processing"
            )
            
            logger.info(f"Created podcast job {job.job_id} with {len(source_file_ids)} source files")
            return job
            
        except Exception as e:
            logger.error(f"Error creating podcast job: {e}")
            raise

    def _cache_job_status(self, job_id: str, status_data: Dict):
        """Cache job status in Redis for SSE streaming"""
        if not self.redis_client:
            return  # Redis not available, skip caching
        
        try:
            cache_key = f"podcast_job_status:{job_id}"
            self.redis_client.setex(
                cache_key, 
                300,  # 5 minutes TTL
                json.dumps(status_data)
            )
        except Exception as e:
            logger.warning(f"Failed to cache job status for {job_id}: {e}")

    def update_job_progress(self, job_id: str, progress: str, status: Optional[str] = None):
        """Update job progress and optionally status"""
        try:
            job = PodcastJob.objects.get(job_id=job_id)
            job.progress = progress
            if status:
                job.status = status
            job.save()
            
            # Cache status for SSE streaming
            status_data = {
                'job_id': str(job.job_id),
                'status': job.status,
                'progress': job.progress,
                'error_message': job.error_message,
                'audio_file_url': job.audio_file.url if job.audio_file else None,
                'title': job.title
            }
            self._cache_job_status(job_id, status_data)
            
            logger.debug(f"Updated podcast job {job_id} progress: {progress}")
            
        except PodcastJob.DoesNotExist:
            logger.error(f"Job {job_id} not found")
        except Exception as e:
            logger.error(f"Error updating job progress for {job_id}: {e}")

    def update_job_result(self, job_id: str, result: Dict, status: str = "completed"):
        """Update job with final result"""
        try:
            job = PodcastJob.objects.get(job_id=job_id)
            job.status = status
            
            if status == "completed":
                job.progress = "Podcast generation completed successfully"
                if "audio_path" in result:
                    # Save the audio file to the model
                    audio_path = Path(result["audio_path"])
                    if audio_path.exists():
                        with open(audio_path, 'rb') as f:
                            job.audio_file.save(
                                f"{job_id}.mp3",
                                ContentFile(f.read()),
                                save=False
                            )
                        # Clean up the temporary file
                        audio_path.unlink()
                
                if "conversation_text" in result:
                    job.conversation_text = result["conversation_text"]
                
                if "source_metadata" in result:
                    job.source_metadata = result["source_metadata"]
            
            job.save()
            
            # Cache final status for SSE streaming
            status_data = {
                'job_id': str(job.job_id),
                'status': job.status,
                'progress': job.progress,
                'error_message': job.error_message,
                'audio_file_url': job.audio_file.url if job.audio_file else None,
                'title': job.title
            }
            self._cache_job_status(job_id, status_data)
            
            logger.info(f"Updated podcast job {job_id} with final result, status: {status}")
            
        except PodcastJob.DoesNotExist:
            logger.error(f"Job {job_id} not found")
        except Exception as e:
            logger.error(f"Error updating job result for {job_id}: {e}")

    def update_job_error(self, job_id: str, error: str):
        """Update job with error information"""
        try:
            job = PodcastJob.objects.get(job_id=job_id)
            job.status = "error"
            job.error_message = error
            job.progress = f"Job failed: {error}"
            job.save()
            
            # Cache error status for SSE streaming
            status_data = {
                'job_id': str(job.job_id),
                'status': job.status,
                'progress': job.progress,
                'error_message': job.error_message,
                'audio_file_url': job.audio_file.url if job.audio_file else None,
                'title': job.title
            }
            self._cache_job_status(job_id, status_data)
            
            logger.error(f"Updated podcast job {job_id} with error: {error}")
            
        except PodcastJob.DoesNotExist:
            logger.error(f"Job {job_id} not found")
        except Exception as e:
            logger.error(f"Error updating job error for {job_id}: {e}")

    def get_job_status(self, job_id: str) -> Optional[Dict]:
        """Get the status of a podcast generation job"""
        try:
            job = PodcastJob.objects.get(job_id=job_id)
            return {
                "job_id": str(job.job_id),
                "status": job.status,
                "progress": job.progress,
                "title": job.title,
                "description": job.description,
                "created_at": job.created_at.isoformat() if job.created_at else None,
                "updated_at": job.updated_at.isoformat() if job.updated_at else None,
                "source_file_ids": job.source_file_ids,
                "source_metadata": job.source_metadata,
                "audio_url": job.audio_url,
                "conversation_text": job.conversation_text,
                "error_message": job.error_message if job.error_message else None,
                "duration_seconds": job.duration_seconds,
                "result": job.get_result_dict() if job.status == "completed" else None
            }
            
        except PodcastJob.DoesNotExist:
            logger.error(f"Job {job_id} not found")
            return None
        except Exception as e:
            logger.error(f"Error getting job status for {job_id}: {e}")
            return None

    def cancel_podcast_job(self, job_id: str) -> bool:
        """Cancel a podcast generation job"""
        try:
            job = PodcastJob.objects.get(job_id=job_id)
            
            if job.status in ['pending', 'generating']:
                job.status = 'cancelled'
                job.error_message = "Job cancelled by user"
                job.progress = "Job cancelled"
                job.save()
                logger.info(f"Cancelled job {job_id}")
                return True
            else:
                logger.warning(f"Cannot cancel job {job_id}, status: {job.status}")
                return False
                
        except PodcastJob.DoesNotExist:
            logger.error(f"Job {job_id} not found")
            return False
        except Exception as e:
            logger.error(f"Error cancelling job {job_id}: {e}")
            return False

    def list_podcast_jobs(self, user=None, limit: int = 50) -> List[Dict[str, Any]]:
        """List podcast generation jobs"""
        try:
            queryset = PodcastJob.objects.all()
            if user:
                queryset = queryset.filter(user=user)
            
            jobs = queryset[:limit]
            
            result = []
            for job in jobs:
                job_data = {
                    "job_id": str(job.job_id),
                    "title": job.title,
                    "description": job.description,
                    "status": job.status,
                    "progress": job.progress,
                    "created_at": job.created_at.isoformat() if job.created_at else None,
                    "updated_at": job.updated_at.isoformat() if job.updated_at else None,
                    "source_file_ids": job.source_file_ids,
                    "source_metadata": job.source_metadata,
                    "audio_url": job.audio_url,
                    "error_message": job.error_message if job.error_message else None,
                    "duration_seconds": job.duration_seconds
                }
                result.append(job_data)
            
            logger.info(f"Listed {len(result)} podcast jobs")
            return result
            
        except Exception as e:
            logger.error(f"Error listing podcast jobs: {e}")
            return []

    def delete_podcast_job(self, job_id: str) -> bool:
        """Delete a podcast generation job and its associated files"""
        try:
            job = PodcastJob.objects.get(job_id=job_id)
            
            # Delete associated audio file if it exists
            if job.audio_file:
                job.audio_file.delete(save=False)
            
            # Delete the job
            job.delete()
            
            logger.info(f"Deleted podcast job {job_id}")
            return True
            
        except PodcastJob.DoesNotExist:
            logger.error(f"Job {job_id} not found")
            return False
        except Exception as e:
            logger.error(f"Error deleting podcast job {job_id}: {e}")
            return False

# Global singleton instance
podcast_generation_service = PodcastGenerationService()