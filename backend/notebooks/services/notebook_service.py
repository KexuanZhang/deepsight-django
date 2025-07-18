"""
Notebook Service - Handle notebook business logic
"""
import logging
from django.shortcuts import get_object_or_404
from django.db import transaction

from ..models import Notebook

logger = logging.getLogger(__name__)


class NotebookService:
    """Handle notebook business logic"""
    
    def get_user_notebooks(self, user):
        """Get all notebooks for user"""
        logger.debug(f"Getting notebooks for user: {user}")
        return Notebook.objects.filter(user=user).order_by('-created_at')
    
    def create_notebook(self, serializer, user):
        """Create new notebook"""
        logger.info(f"Creating notebook for user: {user}")
        return serializer.save(user=user)
    
    def get_notebook_or_404(self, notebook_id, user):
        """Get notebook with permission check"""
        return get_object_or_404(Notebook, id=notebook_id, user=user)
    
    def get_user_notebook_queryset(self, user):
        """Get queryset for user's notebooks (for permissions)"""
        return Notebook.objects.filter(user=user)
    
    @transaction.atomic
    def update_notebook(self, notebook, serializer):
        """Update notebook with validation"""
        return serializer.save()
    
    @transaction.atomic
    def delete_notebook(self, notebook):
        """Delete notebook and related data"""
        # Note: Django will handle cascade deletion based on model relationships
        notebook_id = notebook.id
        notebook.delete()
        logger.info(f"Deleted notebook {notebook_id}")
        return True 