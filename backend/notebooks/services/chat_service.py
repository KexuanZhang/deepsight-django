"""
Chat Service - Handle chat functionality business logic following Django patterns.
"""
import json
import logging
from typing import Dict, List, Optional, Generator
from django.db import transaction
from django.core.exceptions import ValidationError
from rest_framework import status

from pymilvus import Collection
from pymilvus.exceptions import SchemaNotReadyException, CollectionNotExistException

from ..models import Notebook, NotebookChatMessage
from rag.rag import RAGChatbot, SuggestionRAGAgent, user_collection
from .base_service import NotebookBaseService

logger = logging.getLogger(__name__)


class ChatService(NotebookBaseService):
    """Handle chat functionality business logic following Django patterns."""
    
    def __init__(self):
        super().__init__()
    
    def perform_action(self, **kwargs):
        """
        Implementation of abstract method from BaseService.
        This service uses direct method calls rather than the template pattern.
        """
        # This method is required by BaseService but not used in this service
        # Individual methods handle their own transactions and validation
        pass
    
    def validate_chat_request(self, question: str, file_ids: Optional[List] = None) -> Optional[Dict]:
        """
        Validate chat request parameters.
        
        Args:
            question: The user's question
            file_ids: Optional list of file IDs to use for context
            
        Returns:
            None if valid, error dict if invalid
        """
        if not question:
            return {
                "error": "Question is required.",
                "status_code": status.HTTP_400_BAD_REQUEST
            }
        
        if file_ids is not None and not isinstance(file_ids, list):
            return {
                "error": "file_ids must be a list.",
                "status_code": status.HTTP_400_BAD_REQUEST
            }
        
        
        return None

    def check_user_knowledge_base(self, user_id: int) -> Optional[Dict]:
        """
        Check if user has data in their Milvus collection.
        
        Args:
            user_id: The user's ID
            
        Returns:
            None if valid, error dict if no data found
        """
        coll_name = user_collection(user_id)
        try:
            coll = Collection(coll_name)
            existing = coll.num_entities
        except (CollectionNotExistException, SchemaNotReadyException):
            existing = 0

        if existing == 0:
            return {
                "error": "Your knowledge base is empty. Please upload files first.",
                "status_code": status.HTTP_400_BAD_REQUEST
            }
        
        return None

    def get_chat_history(self, notebook) -> List[tuple]:
        """
        Get chat history for notebook.
        
        Args:
            notebook: Notebook instance
            
        Returns:
            List of (sender, message) tuples
        """
        return list(
            NotebookChatMessage.objects
                .filter(notebook=notebook)
                .order_by("timestamp")
                .values_list("sender", "message")
        )

    @transaction.atomic
    def record_user_message(self, notebook, question: str):
        """
        Record user message in chat history.
        
        Args:
            notebook: Notebook instance
            question: User's question
            
        Returns:
            Created NotebookChatMessage instance
        """
        message = NotebookChatMessage.objects.create(
            notebook=notebook, sender="user", message=question
        )
        self.log_notebook_operation(
            "user_message_recorded",
            str(notebook.id),
            notebook.user.id,
            message_id=str(message.id),
            message_length=len(question)
        )
        return message

    @transaction.atomic
    def record_assistant_message(self, notebook, message: str):
        """
        Record assistant message in chat history.
        
        Args:
            notebook: Notebook instance
            message: Assistant's response
            
        Returns:
            Created NotebookChatMessage instance
        """
        chat_message = NotebookChatMessage.objects.create(
            notebook=notebook, sender="assistant", message=message
        )
        self.log_notebook_operation(
            "assistant_message_recorded",
            str(notebook.id),
            notebook.user.id,
            message_id=str(chat_message.id),
            message_length=len(message)
        )
        return chat_message

    def create_chat_stream(
        self,
        user_id: int,
        question: str,
        history: List[tuple],
        file_ids: Optional[List] = None,
        notebook = None,
        collections: Optional[List] = None,
    ) -> Generator:
        """
        Create RAG chat stream with message recording.
        
        Args:
            user_id: User ID
            question: User's question
            history: Chat history as list of (sender, message) tuples
            file_ids: Optional file IDs for context
            notebook: Notebook instance
            collections: Optional additional collections
            
        Returns:
            Generator yielding chat stream chunks
        """
        # Check if we should use full content or RAG based on token limit
        use_full_content = False
        if file_ids and notebook:
            total_content_length = self._get_total_content_length(notebook, file_ids)
            # Using ~200,000 characters as rough estimate for 50k tokens (4 chars per token)
            TOKEN_LIMIT_CHARS = 200000
            use_full_content = total_content_length <= TOKEN_LIMIT_CHARS
            
        # Get the chatbot singleton
        bot = RAGChatbot(
            user_id=user_id,
            extra_collections=collections  # <-- pass collections to RAGChatbot
        )

        # Get raw stream from chatbot
        raw_stream = bot.stream(
            question=question,
            history=history,
            file_ids=file_ids,  # <-- pass file_ids to bot
            use_full_content=use_full_content,  # <-- pass the full content flag
        )

        def wrapped_stream():
            """Wrapper to capture assistant tokens and save final response"""
            buffer = []
            for chunk in raw_stream:
                yield chunk
                # Parse only token events
                if chunk.startswith("data: "):
                    try:
                        payload = json.loads(chunk[len("data: "):])
                        if payload.get("type") == "token":
                            buffer.append(payload.get("text", ""))
                    except json.JSONDecodeError:
                        # Skip malformed JSON
                        continue
                # Ignore metadata and done events
            
            # Once stream finishes, save the full assistant response
            full_response = "".join(buffer).strip()
            if full_response:
                self.record_assistant_message(notebook, full_response)

        return wrapped_stream()

    def _get_total_content_length(self, notebook, file_ids: List[str]) -> int:
        """
        Calculate total character length of selected knowledge base items.
        
        Args:
            notebook: Notebook instance
            file_ids: List of knowledge base item IDs
            
        Returns:
            Total character length of content
        """
        from ..models import KnowledgeBaseItem
        
        # Use the custom manager to get items with content
        items = KnowledgeBaseItem.objects.get_items_with_content(file_ids, user_id=notebook.user.pk)
        
        total_length = sum(len(item['content'] or '') for item in items)
        self.logger.info(f"Total content length for {len(items)} files with content out of {len(file_ids)} requested: {total_length} characters")
        return total_length

    def get_formatted_chat_history(self, notebook) -> List[Dict]:
        """
        Get formatted chat history for display.
        
        Args:
            notebook: Notebook instance
            
        Returns:
            List of formatted message dictionaries
        """
        messages = NotebookChatMessage.objects.filter(notebook=notebook).order_by("timestamp")
        history = []
        for message in messages:
            history.append({
                "id": message.id,
                "sender": message.sender,
                "message": message.message,
                "timestamp": message.timestamp
            })
        return history

    @transaction.atomic
    def clear_chat_history(self, notebook) -> bool:
        """
        Clear all chat history for notebook.
        
        Args:
            notebook: Notebook instance
            
        Returns:
            True if successful
        """
        deleted_count = NotebookChatMessage.objects.filter(notebook=notebook).delete()[0]
        self.log_notebook_operation(
            "chat_history_cleared",
            str(notebook.id),
            notebook.user.id,
            messages_deleted=deleted_count
        )
        return True

    def generate_suggested_questions(self, notebook) -> Dict:
        """
        Generate suggested questions based on chat history.
        
        Args:
            notebook: Notebook instance
            
        Returns:
            Dict with suggestions or error information
        """
        try:
            history = NotebookChatMessage.objects.filter(notebook=notebook).order_by("timestamp")
            history_text = "\n".join([f"{msg.sender}: {msg.message}" for msg in history])

            agent = SuggestionRAGAgent()
            suggestions = agent.generate_suggestions(history_text)

            self.log_notebook_operation(
                "suggestions_generated",
                str(notebook.id),
                notebook.user.id,
                suggestion_count=len(suggestions) if isinstance(suggestions, list) else 0
            )

            return {
                "success": True,
                "suggestions": suggestions
            }

        except Exception as e:
            self.logger.exception(f"Failed to generate suggestions for notebook {notebook.id}: {e}")
            return {
                "error": str(e),
                "status_code": status.HTTP_500_INTERNAL_SERVER_ERROR
            }