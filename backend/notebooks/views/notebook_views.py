"""
Notebook Views - Handle notebook CRUD operations only
"""
import logging

from rest_framework import permissions, authentication, generics

from ..models import Notebook
from ..serializers import NotebookSerializer
from ..services import NotebookService

logger = logging.getLogger(__name__)


class NotebookListCreateAPIView(generics.ListCreateAPIView):
    """
    GET  /api/notebooks/      → list all notebooks for request.user
    POST /api/notebooks/      → create a new notebook for request.user
    """

    serializer_class = NotebookSerializer
    permission_classes = [permissions.IsAuthenticated]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.notebook_service = NotebookService()

    def get_queryset(self):
        # Use service for business logic
        return self.notebook_service.get_user_notebooks(self.request.user)

    def perform_create(self, serializer):
        # Use service for business logic
        self.notebook_service.create_notebook(serializer, self.request.user)


class NotebookRetrieveUpdateDestroyAPIView(generics.RetrieveUpdateDestroyAPIView):
    """
    GET    /api/notebooks/{pk}/   → retrieve a notebook
    PUT    /api/notebooks/{pk}/   → update name & description
    PATCH  /api/notebooks/{pk}/   → partial update
    DELETE /api/notebooks/{pk}/   → delete the notebook
    """

    serializer_class = NotebookSerializer
    permission_classes = [permissions.IsAuthenticated]
    authentication_classes = [authentication.SessionAuthentication]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.notebook_service = NotebookService()

    def get_queryset(self):
        # Use service for permission checking
        return self.notebook_service.get_user_notebook_queryset(self.request.user)

    def perform_update(self, serializer):
        # Use service for business logic
        notebook = self.get_object()
        self.notebook_service.update_notebook(notebook, serializer)

    def perform_destroy(self, instance):
        # Use service for business logic
        self.notebook_service.delete_notebook(instance) 