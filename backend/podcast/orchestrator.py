"""
Main orchestrator service for podcast generation using dependency injection.
"""

import logging
from typing import Dict, Optional, List, Any
from .interfaces.ai_client_interface import AIClientInterface
from .interfaces.audio_processor_interface import AudioProcessorInterface
from .interfaces.content_detector_interface import ContentDetectorInterface
from .interfaces.role_config_interface import RoleConfigInterface
from .core.conversation_service import ConversationService
from .core.job_service import JobService
from .core.status_service import StatusService
from .factories.ai_client_factory import AIClientFactory
from .factories.audio_processor_factory import AudioProcessorFactory
from .models import PodcastJob

logger = logging.getLogger(__name__)


class PodcastOrchestrator:
    """Main orchestrator service for podcast generation using dependency injection"""
    
    def __init__(
        self,
        ai_client: Optional[AIClientInterface] = None,
        audio_processor: Optional[AudioProcessorInterface] = None,
        content_detector: Optional[ContentDetectorInterface] = None,
        role_config: Optional[RoleConfigInterface] = None
    ):
        # Use dependency injection or default implementations
        self.ai_client = ai_client or AIClientFactory.create_client()
        self.audio_processor = audio_processor or AudioProcessorFactory.create_processor()
        
        # Import here to avoid circular imports
        from .config import content_detector as default_content_detector
        from .config import role_config_manager as default_role_config
        
        self.content_detector = content_detector or default_content_detector
        self.role_config = role_config or default_role_config
        
        # Initialize services with dependencies
        self.conversation_service = ConversationService(
            self.ai_client,
            self.content_detector,
            self.role_config
        )
        self.job_service = JobService()
        self.status_service = StatusService()
    
    async def generate_podcast_conversation(
        self, content: str, file_metadata: Dict
    ) -> str:
        """Generate podcast conversation from content"""
        return await self.conversation_service.generate_conversation(content, file_metadata)
    
    def generate_podcast_audio(self, conversation_text: str, output_path: str) -> str:
        """Generate complete podcast audio from conversation text"""
        return self.audio_processor.generate_podcast_audio(conversation_text, output_path)
    
    def create_podcast_job(
        self, source_file_ids: List[str], job_metadata: Dict, user=None, notebook=None
    ) -> PodcastJob:
        """Create a new podcast generation job"""
        return self.job_service.create_job(source_file_ids, job_metadata, user, notebook)
    
    def update_job_progress(
        self, job_id: str, progress: str, status: Optional[str] = None
    ):
        """Update job progress and optionally status"""
        self.status_service.update_job_progress(job_id, progress, status)
    
    def update_job_result(self, job_id: str, result: Dict, status: str = "completed"):
        """Update job with final result"""
        self.job_service.update_job_result(job_id, result, status)
    
    def update_job_error(self, job_id: str, error: str):
        """Update job with error information"""
        self.job_service.update_job_error(job_id, error)
    
    def get_job_status(self, job_id: str) -> Optional[Dict]:
        """Get the status of a podcast generation job"""
        return self.job_service.get_job_status(job_id)
    
    def cancel_podcast_job(self, job_id: str) -> bool:
        """Cancel a podcast generation job"""
        return self.job_service.cancel_job(job_id)
    
    def list_podcast_jobs(self, user=None, limit: int = 50) -> List[Dict[str, Any]]:
        """List podcast generation jobs"""
        return self.job_service.list_jobs(user, limit)
    
    def delete_podcast_job(self, job_id: str) -> bool:
        """Delete a podcast generation job and its associated files"""
        return self.job_service.delete_job(job_id)


# Global singleton instance with default dependencies
podcast_orchestrator = PodcastOrchestrator()