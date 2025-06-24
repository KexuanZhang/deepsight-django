"""
Podcast generation service for Django backend.

This is the main orchestrator service that coordinates different modules
for comprehensive podcast generation capabilities.

Modules:
- content_detector: Automatic content type detection
- role_configs: Expert roles and prompt templates
- ai_clients: AI provider management (OpenAI/DeepSeek)
- audio_processor: Audio generation and processing
"""

import logging
import json
import redis
from typing import Dict, Optional, List, Any
from pathlib import Path
from django.conf import settings
from django.core.files.base import ContentFile

from .models import PodcastJob
from .content_detector import content_detector
from .role_configs import role_config_manager
from .ai_clients import ai_client_manager
from .audio_processor import audio_processor

logger = logging.getLogger(__name__)


class PodcastGenerationService:
    """Main orchestrator service for podcast generation"""

    def __init__(self):
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

    async def generate_podcast_conversation(
        self, content: str, file_metadata: Dict
    ) -> str:
        """Generate podcast conversation from content using configured AI provider"""
        try:
            # Validate AI provider configuration
            if not ai_client_manager.validate_ai_provider():
                raise ValueError(
                    f"AI provider {ai_client_manager.ai_provider} is not properly configured"
                )

            # Detect content type and get appropriate role configuration
            content_type = content_detector.detect_content_type(content, file_metadata)
            role_context = role_config_manager.get_content_specific_roles(content_type)

            # Truncate content to first 15,000 words like in the original
            words = content.split()
            truncated_content = (
                " ".join(words[:15000]) if len(words) > 15000 else content
            )

            # 构建角色特征描述
            role_descriptions = []
            for name, context in role_context.items():
                desc = f"- {name}（{context['role']}）：{context['focus']}，{context['style']}"
                if "expertise" in context:
                    desc += f"，专长：{context['expertise']}"
                if "perspective" in context:
                    desc += f"，视角：{context['perspective']}"
                role_descriptions.append(desc)

            role_section = "\n            ".join(role_descriptions)

            # 获取针对内容类型的prompt模板
            prompt_template = role_config_manager.get_content_specific_prompt(
                content_type
            )

            # 构建完整的prompt
            prompt = prompt_template.format(
                role_section=role_section,
                yang_opening=role_context["杨飞飞"]["opening"],
                oliver_focus=role_context["奥立昆"]["focus"],
                liman_perspective=role_context["李特曼"]["perspective"],
                content=truncated_content,
            )

            response = ai_client_manager.create_chat_completion(
                messages=[
                    {
                        "role": "system",
                        "content": "你是一位专业的技术内容生成专家，专门从事研究分析和创新评估。请生成实质性的、技术严谨的播客讨论，重点关注具体细节、方法论洞察和实际意义。避免废话，始终保持专业的技术话语。所有内容都必须用中文生成。",
                    },
                    {"role": "user", "content": prompt},
                ],
                temperature=0.3,  # Lower temperature for more focused, consistent technical content
                max_tokens=5000,  # Increased for more detailed technical discussions
                presence_penalty=0.1,  # Slight penalty to reduce repetition
                frequency_penalty=0.1,  # Encourage diverse technical vocabulary
            )

            conversation = response.choices[0].message.content

            # Post-process to ensure technical focus
            conversation = self._enhance_technical_focus(conversation)

            logger.info(
                f"Generated conversation using {ai_client_manager.ai_provider} for content type '{content_type}' with {len(conversation)} characters"
            )
            return conversation

        except Exception as e:
            logger.error(
                f"Error generating conversation with {ai_client_manager.ai_provider}: {e}"
            )
            raise

    def _enhance_technical_focus(self, conversation: str) -> str:
        """Post-process conversation to enhance technical focus and remove fluff"""
        try:
            # Remove common conversational filler patterns
            import re

            # Patterns that indicate low-value conversational content
            fluff_patterns = [
                r"<[^>]+>(?:嗯|嗯嗯|对|对的|是的|好的|没错|确实|当然|哈哈|呵呵)[^<]*</[^>]+>",  # Simple agreements
                r"<[^>]+>(?:那|那么|然后|接下来|下面|现在)[^<]*让我们[^<]*</[^>]+>",  # Transitional filler
                r"<[^>]+>(?:大家好|欢迎|感谢|谢谢)[^<]*(?:收听|观看|关注)[^<]*</[^>]+>",  # Generic greetings
                r"<[^>]+>(?:总的来说|总而言之|综上所述|最后)[^<]*(?:非常|很|真的)[^<]*(?:有趣|精彩|重要)[^<]*</[^>]+>",  # Generic conclusions
            ]

            # Remove identified fluff patterns
            for pattern in fluff_patterns:
                conversation = re.sub(
                    pattern, "", conversation, flags=re.IGNORECASE | re.DOTALL
                )

            # Ensure each speaker segment has substantial technical content
            segments = re.findall(
                r"<([^/>][^>]*)>(.*?)(?=<[^/>][^>]*>|</[^>]*>|$)",
                conversation,
                re.DOTALL,
            )

            enhanced_segments = []
            for speaker, content in segments:
                content = content.strip()
                if content and not speaker.startswith(
                    "/"
                ):  # Skip empty content and closing tags
                    # Only keep segments with substantial technical content (> 50 characters)
                    if len(content) > 50:
                        enhanced_segments.append(f"<{speaker}>{content}</{speaker}>")

            # Reconstruct conversation
            enhanced_conversation = "\n\n".join(enhanced_segments)

            # If too much was removed, return original
            if len(enhanced_conversation) < len(conversation) * 0.5:
                logger.warning(
                    "Technical enhancement removed too much content, returning original"
                )
                return conversation

            return enhanced_conversation

        except Exception as e:
            logger.warning(
                f"Error enhancing technical focus: {e}, returning original conversation"
            )
            return conversation

    def generate_podcast_audio(self, conversation_text: str, output_path: str) -> str:
        """Generate complete podcast audio from conversation text using audio processor"""
        return audio_processor.generate_podcast_audio(conversation_text, output_path)

    def create_podcast_job(
        self, source_file_ids: List[str], job_metadata: Dict, user=None
    ) -> PodcastJob:
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
                progress="Job queued for processing",
            )

            logger.info(
                f"Created podcast job {job.job_id} with {len(source_file_ids)} source files"
            )
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
                json.dumps(status_data),
            )
        except Exception as e:
            logger.warning(f"Failed to cache job status for {job_id}: {e}")

    def update_job_progress(
        self, job_id: str, progress: str, status: Optional[str] = None
    ):
        """Update job progress and optionally status"""
        try:
            job = PodcastJob.objects.get(job_id=job_id)
            job.progress = progress
            if status:
                job.status = status
            job.save()

            # Cache status for SSE streaming
            status_data = {
                "job_id": str(job.job_id),
                "status": job.status,
                "progress": job.progress,
                "error_message": job.error_message,
                "audio_file_url": job.audio_file.url if job.audio_file else None,
                "title": job.title,
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
                        with open(audio_path, "rb") as f:
                            job.audio_file.save(
                                f"{job_id}.mp3", ContentFile(f.read()), save=False
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
                "job_id": str(job.job_id),
                "status": job.status,
                "progress": job.progress,
                "error_message": job.error_message,
                "audio_file_url": job.audio_file.url if job.audio_file else None,
                "title": job.title,
            }
            self._cache_job_status(job_id, status_data)

            logger.info(
                f"Updated podcast job {job_id} with final result, status: {status}"
            )

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
                "job_id": str(job.job_id),
                "status": job.status,
                "progress": job.progress,
                "error_message": job.error_message,
                "audio_file_url": job.audio_file.url if job.audio_file else None,
                "title": job.title,
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
                "result": job.get_result_dict() if job.status == "completed" else None,
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

            if job.status in ["pending", "generating"]:
                job.status = "cancelled"
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
                    "created_at": job.created_at.isoformat()
                    if job.created_at
                    else None,
                    "updated_at": job.updated_at.isoformat()
                    if job.updated_at
                    else None,
                    "source_file_ids": job.source_file_ids,
                    "source_metadata": job.source_metadata,
                    "audio_url": job.audio_url,
                    "error_message": job.error_message if job.error_message else None,
                    "duration_seconds": job.duration_seconds,
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
