"""
Podcast Service using Panel Discussion Agent Framework

This service simplifies podcast generation by leveraging the 
panel discussion framework to create conversation and then convert to audio.
"""

import logging
from typing import Dict, Any, List, Optional
from pathlib import Path
from django.utils import timezone

from .utils import (
    extract_selected_content,
    parse_conversation,
    generate_conversation_audio_optimized
)
from .storage import PodcastStorageService

logger = logging.getLogger(__name__)


class PodcastService:
    """
    Podcast service that uses the panel discussion framework
    to generate conversations and convert them to audio.
    """
    
    def __init__(self):
        """Initialize the podcast service with storage"""
        self.storage_service = PodcastStorageService()
    
    
    async def create_podcast_with_panel_crew(self, selected_item_ids: List[int], 
                                     user_id: int, podcast_id: str, notebook_id: Optional[int] = None, custom_instruction: str = None) -> Dict[str, Any]:
        """
        Create a podcast from selected knowledge base items using panel_crew.
        
        Args:
            selected_item_ids: List of KnowledgeBaseItem IDs selected by frontend
            user_id: User ID for the podcast
            podcast_id: Podcast ID for the podcast
            notebook_id: Notebook ID (optional)
            custom_instruction: Optional custom discussion instruction
            
        Returns:
            Dictionary with conversation result and metadata
        """
        try:
            # Extract content from selected items
            selected_content = await extract_selected_content(selected_item_ids)
            
            # Create topic with custom instruction
            topic = custom_instruction if custom_instruction else ""
            
            # Run panel crew discussion
            from agents.panel_crew import PanelCrewCollaboration
            
            # Create crew with material content
            panel_crew = PanelCrewCollaboration(
                material_content=selected_content
            )
            
            logger.info(f"Starting panel crew discussion for topic: {topic}")
            result = panel_crew.crew().kickoff(inputs={'topic': topic, 'material_content': selected_content})
            
            # Parse conversation directly from crew result
            conversation_turns = parse_conversation(str(result))
            
            if not conversation_turns:
                raise Exception("No conversation turns extracted from panel discussion")
            
            # Convert to audio and store in MinIO
            audio_object_key = self._process_conversation_to_audio(conversation_turns, user_id, podcast_id, notebook_id)
            
            return {
                "status": "completed",
                "conversation_turns": conversation_turns,
                "crew_result": str(result),  # Convert crew result to string
                "audio_object_key": audio_object_key,
                "metadata": {
                    "total_turns": len(conversation_turns),
                    "participants": list(set([turn['speaker'] for turn in conversation_turns])),
                    "generated_at": timezone.now().isoformat(),
                    "selected_items_count": len(selected_item_ids),
                    "topic": topic
                }
            }
                
        except Exception as e:
            logger.error(f"Panel crew podcast creation failed for selected items {selected_item_ids}: {e}")
            return {
                "status": "failed",
                "error": str(e),
                "conversation_turns": None,
                "crew_result": None,
                "audio_object_key": None
            }

    
    def _process_conversation_to_audio(self, conversation_turns: List[Dict[str, str]], user_id: int, podcast_id: str, notebook_id: Optional[int] = None) -> Optional[str]:
        """
        Main orchestration method for converting conversation to audio and storing in MinIO.
        
        Args:
            conversation_turns: Already parsed conversation turns
            user_id: User ID for the podcast
            podcast_id: Podcast ID for the podcast
            notebook_id: Notebook ID (optional)
            
        Returns:
            MinIO object key for the stored audio file, or None if failed
        """
        try:
            import tempfile
            
            # Create temporary directory for audio processing
            temp_dir = Path(tempfile.mkdtemp())
            
            try:
                # Generate audio file using optimized approach from utils
                audio_file_path = generate_conversation_audio_optimized(conversation_turns, temp_dir)
                
                # Store in MinIO using storage service
                if audio_file_path:
                    return self._store_audio_with_metadata(audio_file_path, conversation_turns, user_id, podcast_id, notebook_id)
                
                return None
                
            finally:
                # Clean up temporary directory
                import shutil
                try:
                    shutil.rmtree(temp_dir)
                except Exception as cleanup_error:
                    logger.warning(f"Failed to clean up temp directory {temp_dir}: {cleanup_error}")
            
        except Exception as e:
            logger.error(f"Conversation to audio processing failed: {e}")
            return None
    
    
    def _store_audio_with_metadata(self, audio_file_path: Path, conversation_turns: List[Dict[str, str]], user_id: int, podcast_id: str, notebook_id: Optional[int] = None) -> Optional[str]:
        """
        Store audio file using storage service with conversation metadata.
        
        Args:
            audio_file_path: Path to audio file to store
            conversation_turns: List of conversation turns for metadata
            user_id: User ID for the podcast
            podcast_id: Podcast ID for the podcast
            notebook_id: Notebook ID (optional)
            
        Returns:
            MinIO object key for stored file, or None if failed
        """
        try:
            # Prepare metadata from conversation
            metadata = {
                "total_turns": len(conversation_turns),
                "participants": list(set([turn['speaker'] for turn in conversation_turns])),
                "generated_at": timezone.now().isoformat()
            }
            
            # Store using storage service
            storage_result = self.storage_service.store_podcast_audio(audio_file_path, user_id, podcast_id, notebook_id, metadata)
            
            if storage_result["storage_success"]:
                return storage_result["audio_object_key"]
            else:
                logger.error(f"Storage service failed: {storage_result['error']}")
                return None
                
        except Exception as e:
            logger.error(f"Audio storage with metadata failed: {e}")
            return None
    


