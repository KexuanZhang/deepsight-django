"""
Chat Service - Handle chat functionality business logic following Django patterns.
"""
import json
import logging
from typing import Dict, List, Optional, Generator
from django.db import transaction
from django.core.exceptions import ValidationError
from rest_framework import status

from ..models import Notebook, NotebookChatMessage
from core.services import NotebookBaseService

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

    def check_notebook_knowledge_base(self, notebook) -> Optional[Dict]:
        """
        Check if notebook has data in its RagFlow dataset.
        
        Args:
            notebook: Notebook instance
            
        Returns:
            None if valid, error dict if no data found
        """
        try:
            # Check if notebook has RagFlow dataset
            if not hasattr(notebook, 'ragflow_dataset'):
                return {
                    "error": "This notebook doesn't have a knowledge base yet. Please upload files first.",
                    "status_code": status.HTTP_400_BAD_REQUEST
                }
            
            ragflow_dataset = notebook.ragflow_dataset
            
            # Check if dataset is ready
            if not ragflow_dataset.is_ready():
                return {
                    "error": f"Knowledge base is not ready. Status: {ragflow_dataset.status}",
                    "status_code": status.HTTP_400_BAD_REQUEST
                }
            
            # Check if dataset has documents
            document_count = ragflow_dataset.get_document_count()
            if document_count == 0:
                return {
                    "error": "Your knowledge base is empty. Please upload files first.",
                    "status_code": status.HTTP_400_BAD_REQUEST
                }
            
            return None
            
        except Exception as e:
            logger.exception(f"Error checking notebook knowledge base: {e}")
            return {
                "error": "Failed to check knowledge base status.",
                "status_code": status.HTTP_500_INTERNAL_SERVER_ERROR
            }

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
        Create agentic RAG chat stream with message recording using RagFlow Knowledge Base Agent.
        
        Args:
            user_id: User ID
            question: User's question
            history: Chat history as list of (sender, message) tuples
            file_ids: Optional file IDs for context (not used with agentic RAG)
            notebook: Notebook instance
            collections: Optional additional collections (not used with agentic RAG)
            
        Returns:
            Generator yielding chat stream chunks
        """
        from .agentic_rag_service import AgenticRAGService
        
        # Convert history format for agent
        formatted_history = []
        if history:
            for sender, message in history:
                role = "user" if sender == "user" else "assistant"
                formatted_history.append({"role": role, "content": message})
        
        # Create agentic RAG service
        agentic_rag = AgenticRAGService()
        
        def wrapped_stream():
            """Wrapper to capture assistant tokens and save final response"""
            buffer = []
            
            # Get streaming response from knowledge base agent
            agent_stream = agentic_rag.ask_agent_streaming(
                notebook=notebook,
                user_id=user_id,
                question=question,
                history=formatted_history
            )
            
            for chunk in agent_stream:
                yield chunk
                
                # Parse token events to build full response
                if chunk.startswith("data: "):
                    try:
                        import json
                        payload = json.loads(chunk[len("data: "):])
                        if payload.get("type") == "token":
                            buffer.append(payload.get("text", ""))
                    except json.JSONDecodeError:
                        # Skip malformed JSON
                        continue
            
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
        Generate suggested questions using the knowledge base agent.
        
        Args:
            notebook: Notebook instance
            
        Returns:
            Dict with suggestions or error information
        """
        try:
            from .agentic_rag_service import AgenticRAGService
            
            # Get recent chat history
            recent_messages = NotebookChatMessage.objects.filter(
                notebook=notebook
            ).order_by("-timestamp")[:10]  # Last 10 messages
            
            # Build history context
            history = []
            for msg in reversed(recent_messages):  # Reverse to get chronological order
                role = "user" if msg.sender == "user" else "assistant" 
                history.append({"role": role, "content": msg.message})
            
            # Create suggestion prompt
            suggestion_prompt = """Based on our conversation and the knowledge base, suggest 3-5 relevant follow-up questions that would be helpful to explore. 
            Make the questions specific and actionable. Format your response as a simple numbered list."""
            
            # Use agentic RAG to generate suggestions
            agentic_rag = AgenticRAGService()
            result = agentic_rag.ask_agent_direct(
                notebook=notebook,
                user_id=notebook.user.id,
                question=suggestion_prompt,
                history=history
            )
            
            if result.get('success'):
                content = result.get('content', '')
                
                # Parse suggestions from response (simple parsing for numbered list)
                suggestions = []
                lines = content.split('\n')
                for line in lines:
                    line = line.strip()
                    if line and (line[0].isdigit() or line.startswith('-')):
                        # Remove numbering and clean up
                        clean_question = line.split('.', 1)[-1].strip()
                        if clean_question.startswith('-'):
                            clean_question = clean_question[1:].strip()
                        if clean_question:
                            suggestions.append(clean_question)
                
                # Fallback: if no parsed suggestions, use the raw content
                if not suggestions:
                    suggestions = [content]
                
                self.log_notebook_operation(
                    "agent_suggestions_generated",
                    str(notebook.id),
                    notebook.user.id,
                    suggestion_count=len(suggestions)
                )
                
                return {
                    "success": True,
                    "suggestions": suggestions[:5]  # Limit to 5 suggestions
                }
            else:
                return {
                    "error": result.get('error', 'Failed to generate suggestions'),
                    "status_code": result.get('status_code', status.HTTP_500_INTERNAL_SERVER_ERROR)
                }

        except Exception as e:
            self.logger.exception(f"Failed to generate agent suggestions for notebook {notebook.id}: {e}")
            return {
                "error": "Failed to generate suggestions",
                "status_code": status.HTTP_500_INTERNAL_SERVER_ERROR,
                "details": {"error": str(e)}
            }