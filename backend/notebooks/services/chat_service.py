"""
Chat Service - Handle chat functionality business logic
"""
import json
import logging
from django.db import transaction
from rest_framework import status

from pymilvus import Collection
from pymilvus.exceptions import SchemaNotReadyException, CollectionNotExistException

from ..models import Notebook, NotebookChatMessage
from rag.rag import RAGChatbot, SuggestionRAGAgent, user_collection

logger = logging.getLogger(__name__)


class ChatService:
    """Handle chat functionality business logic"""
    
    def validate_chat_request(self, question, file_ids=None):
        """Validate chat request parameters"""
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

    def check_user_knowledge_base(self, user_id):
        """Check if user has data in their Milvus collection"""
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

    def get_chat_history(self, notebook):
        """Get chat history for notebook"""
        return list(
            NotebookChatMessage.objects
                .filter(notebook=notebook)
                .order_by("timestamp")
                .values_list("sender", "message")
        )

    @transaction.atomic
    def record_user_message(self, notebook, question):
        """Record user message in chat history"""
        return NotebookChatMessage.objects.create(
            notebook=notebook, sender="user", message=question
        )

    @transaction.atomic
    def record_assistant_message(self, notebook, message):
        """Record assistant message in chat history"""
        return NotebookChatMessage.objects.create(
            notebook=notebook, sender="assistant", message=message
        )

    def create_chat_stream(
        self,
        user_id,
        question,
        history,
        file_ids=None,         # <-- add file_ids param
        notebook=None,
        collections=None,
    ):
        """Create RAG chat stream with message recording"""
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

    def _get_total_content_length(self, notebook, file_ids):
        """Calculate total character length of selected knowledge base items using model manager"""
        from ..models import KnowledgeBaseItem
        
        # Use the custom manager to get items with content
        items = KnowledgeBaseItem.objects.get_items_with_content(file_ids, user_id=notebook.user.pk)
        
        total_length = sum(len(item['content'] or '') for item in items)
        logger.info(f"Total content length for {len(items)} files with content out of {len(file_ids)} requested: {total_length} characters")
        return total_length

    def get_formatted_chat_history(self, notebook):
        """Get formatted chat history for display"""
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
    def clear_chat_history(self, notebook):
        """Clear all chat history for notebook"""
        deleted_count = NotebookChatMessage.objects.filter(notebook=notebook).delete()[0]
        logger.info(f"Cleared {deleted_count} chat messages for notebook {notebook.id}")
        return True

    def generate_suggested_questions(self, notebook):
        """Generate suggested questions based on chat history"""
        try:
            history = NotebookChatMessage.objects.filter(notebook=notebook).order_by("timestamp")
            history_text = "\n".join([f"{msg.sender}: {msg.message}" for msg in history])

            agent = SuggestionRAGAgent()
            suggestions = agent.generate_suggestions(history_text)

            return {
                "success": True,
                "suggestions": suggestions
            }

        except Exception as e:
            logger.exception(f"Failed to generate suggestions for notebook {notebook.id}: {e}")
            return {
                "error": str(e),
                "status_code": status.HTTP_500_INTERNAL_SERVER_ERROR
            }