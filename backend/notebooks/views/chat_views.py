"""
Chat Views - Handle chat functionality only
"""
import json
import logging

from django.http import StreamingHttpResponse
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response

from pymilvus import Collection
from pymilvus.exceptions import SchemaNotReadyException, CollectionNotExistException

from ..models import Notebook, NotebookChatMessage
from ..utils.view_mixins import StandardAPIView, NotebookPermissionMixin
from rag.rag import RAGChatbot, SuggestionRAGAgent, user_collection
from ..services import ChatService

logger = logging.getLogger(__name__)


class RAGChatFromKBView(NotebookPermissionMixin, APIView):
    """
    POST /api/v1/notebooks/{notebook_id}/chat/
    {
      "question":       "Explain quantum tunneling",
      "mode":           "local"|"global"|"hybrid",
      "filter_sources": ["paper1.pdf","notes.md"]
    }
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.chat_service = ChatService()

    def post(self, request, notebook_id):
        question = request.data.get("question")
        mode = request.data.get("mode", "hybrid")
        filter_sources = request.data.get("filter_sources", None)

        # 1) Validate inputs using service
        validation_error = self.chat_service.validate_chat_request(question, mode)
        if validation_error:
            return Response(validation_error, status=validation_error['status_code'])

        # 2) Fetch & authorize notebook
        try:
            notebook = self.get_user_notebook(notebook_id, request.user)
        except:
            return Response({"error": "Notebook not found."}, status=status.HTTP_404_NOT_FOUND)

        # 3) Check user's knowledge base using service
        user_id = request.user.pk
        kb_error = self.chat_service.check_user_knowledge_base(user_id)
        if kb_error:
            return Response(kb_error, status=kb_error['status_code'])

        # 4) Load chat history and record user question using service
        history = self.chat_service.get_chat_history(notebook)
        self.chat_service.record_user_message(notebook, question)

        # 5) Create chat stream using service
        stream = self.chat_service.create_chat_stream(
            user_id=user_id,
            question=question,
            history=history,
            mode=mode,
            filter_sources=filter_sources,
            notebook=notebook
        )

        return StreamingHttpResponse(
            stream,
            content_type="text/event-stream",
        )


class ChatHistoryView(StandardAPIView, NotebookPermissionMixin):
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.chat_service = ChatService()

    def get(self, request, notebook_id):
        try:
            notebook = self.get_user_notebook(notebook_id, request.user)
        except Exception as e:
            return Response({"error": "Notebook not found"}, status=404)
        
        # Use service to get formatted history
        history = self.chat_service.get_formatted_chat_history(notebook)
        return Response({"history": history})
    

class ClearChatHistoryView(StandardAPIView, NotebookPermissionMixin):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.chat_service = ChatService()

    def delete(self, request, notebook_id):
        try:
            notebook = self.get_user_notebook(notebook_id, request.user)
        except Exception as e:
            return Response({"error": "Notebook not found"}, status=404)
        
        # Use service to clear history
        success = self.chat_service.clear_chat_history(notebook)
        if success:
            return Response({"success": True, "message": "Chat history cleared"})
        else:
            return Response({"error": "Failed to clear chat history"}, status=500)
    

class SuggestedQuestionsView(StandardAPIView, NotebookPermissionMixin):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.chat_service = ChatService()

    def get(self, request, notebook_id):
        try:
            notebook = self.get_user_notebook(notebook_id, request.user)
            
            # Use service to generate suggestions
            result = self.chat_service.generate_suggested_questions(notebook)
            
            if result.get('success'):
                return Response({"suggestions": result['suggestions']})
            else:
                return Response(result, status=result.get('status_code', 500))
                
        except Exception as e:
            return Response({"error": str(e)}, status=400) 