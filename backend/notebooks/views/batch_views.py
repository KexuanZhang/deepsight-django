"""
Batch Job Views - Handle batch processing operations only
"""
import logging

from rest_framework import status
from rest_framework.response import Response

from ..models import BatchJob
from ..utils.view_mixins import StandardAPIView, NotebookPermissionMixin
from ..services import KnowledgeBaseService

logger = logging.getLogger(__name__)


class BatchJobStatusView(StandardAPIView, NotebookPermissionMixin):
    """Get status of batch processing jobs."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.knowledge_service = KnowledgeBaseService()

    def get(self, request, notebook_id, batch_job_id):
        """Get status of a batch job."""
        # Verify notebook ownership
        notebook = self.get_user_notebook(notebook_id, request.user)

        # Use service to get batch job status
        result = self.knowledge_service.get_batch_job_status(batch_job_id, notebook)

        if result.get('success'):
            return self.success_response(result)
        else:
            return self.error_response(
                result['error'],
                status_code=result['status_code'],
                details=result.get('details', {}),
            ) 