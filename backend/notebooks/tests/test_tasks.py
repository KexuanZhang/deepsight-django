"""
Task tests for the notebooks module.
"""

from unittest.mock import Mock, patch
from django.test import TestCase
from django.contrib.auth import get_user_model

from ..models import Notebook, BatchJob, BatchJobItem
from ..tasks import (
    process_url_task,
    process_file_upload_task,
    _check_batch_completion,
    cleanup_old_batch_jobs
)

User = get_user_model()


class TaskTests(TestCase):
    """Test cases for Celery tasks."""

    def setUp(self):
        self.user = User.objects.create_user(
            username="testuser", email="test@example.com", password="testpass123"
        )
        self.notebook = Notebook.objects.create(
            user=self.user, name="Test Notebook"
        )

    @patch('notebooks.tasks.url_service')
    def test_process_url_task_success(self, mock_url_service):
        """Test successful URL processing task."""
        # Mock service response
        mock_url_service.process_url.return_value = {
            'file_id': 'test-file-id',
            'status': 'completed'
        }

        # Call task function directly (not through Celery)
        result = process_url_task(
            url="https://example.com",
            notebook_id=str(self.notebook.id),
            user_id=self.user.id
        )

        self.assertIsNotNone(result)
        mock_url_service.process_url.assert_called_once()

    def test_process_url_task_missing_params(self):
        """Test URL processing task with missing parameters."""
        from ..exceptions import ValidationError

        with self.assertRaises(ValidationError):
            process_url_task(
                url="",  # Missing URL
                notebook_id=str(self.notebook.id),
                user_id=self.user.id
            )

    @patch('notebooks.tasks.file_service')
    def test_process_file_upload_task_success(self, mock_file_service):
        """Test successful file upload processing task."""
        # Mock service response
        mock_file_service.upload_file.return_value = {
            'file_id': 'test-file-id',
            'status': 'completed'
        }

        # Call task function directly
        result = process_file_upload_task(
            file_data=b"test file content",
            filename="test.txt",
            notebook_id=str(self.notebook.id),
            user_id=self.user.id
        )

        self.assertIsNotNone(result)
        mock_file_service.upload_file.assert_called_once()

    def test_check_batch_completion(self):
        """Test batch completion checking."""
        # Create batch job with items
        batch_job = BatchJob.objects.create(
            notebook=self.notebook,
            job_type='url_parse',
            total_items=3
        )

        # Create batch items
        BatchJobItem.objects.create(
            batch_job=batch_job,
            item_data={'url': 'http://example1.com'},
            status='completed'
        )
        BatchJobItem.objects.create(
            batch_job=batch_job,
            item_data={'url': 'http://example2.com'},
            status='completed'
        )
        BatchJobItem.objects.create(
            batch_job=batch_job,
            item_data={'url': 'http://example3.com'},
            status='failed'
        )

        # Check completion
        _check_batch_completion(batch_job.id)

        # Refresh from database
        batch_job.refresh_from_db()

        self.assertEqual(batch_job.status, 'partially_completed')
        self.assertEqual(batch_job.completed_items, 2)
        self.assertEqual(batch_job.failed_items, 1)

    def test_cleanup_old_batch_jobs(self):
        """Test cleanup of old batch jobs."""
        from datetime import datetime, timedelta

        # Create old completed batch job
        old_job = BatchJob.objects.create(
            notebook=self.notebook,
            job_type='url_parse',
            status='completed'
        )
        
        # Manually set old updated_at date
        old_date = datetime.now() - timedelta(days=8)
        BatchJob.objects.filter(id=old_job.id).update(updated_at=old_date)

        # Create recent job (should not be deleted)
        recent_job = BatchJob.objects.create(
            notebook=self.notebook,
            job_type='file_upload',
            status='completed'
        )

        initial_count = BatchJob.objects.count()
        self.assertEqual(initial_count, 2)

        # Run cleanup
        deleted_count = cleanup_old_batch_jobs()

        self.assertEqual(deleted_count, 1)
        self.assertEqual(BatchJob.objects.count(), 1)
        self.assertTrue(BatchJob.objects.filter(id=recent_job.id).exists()) 