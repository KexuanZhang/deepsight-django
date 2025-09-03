"""
Model tests for the notebooks module.
"""

import tempfile
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError

from ..models import (
    Notebook, 
    Source, 
    KnowledgeBaseItem, 
    BatchJob,
    BatchJobItem
)

User = get_user_model()


class NotebookModelTests(TestCase):
    """Test cases for Notebook model."""

    def setUp(self):
        self.user = User.objects.create_user(
            username="testuser", email="test@example.com", password="testpass123"
        )

    def test_notebook_creation(self):
        """Test notebook creation."""
        notebook = Notebook.objects.create(
            user=self.user, name="Test Notebook", description="Test description"
        )

        self.assertEqual(notebook.user, self.user)
        self.assertEqual(notebook.name, "Test Notebook")
        self.assertEqual(str(notebook), "Test Notebook")

    def test_notebook_ordering(self):
        """Test notebook ordering by creation date."""
        notebook1 = Notebook.objects.create(user=self.user, name="First")
        notebook2 = Notebook.objects.create(user=self.user, name="Second")

        notebooks = list(Notebook.objects.all())
        self.assertEqual(notebooks[0], notebook2)  # Most recent first
        self.assertEqual(notebooks[1], notebook1)

    def test_notebook_user_isolation(self):
        """Test that users can only see their own notebooks."""
        other_user = User.objects.create_user(
            username="other", email="other@example.com", password="pass"
        )
        
        notebook1 = Notebook.objects.create(user=self.user, name="User 1 Notebook")
        notebook2 = Notebook.objects.create(user=other_user, name="User 2 Notebook")
        
        user1_notebooks = Notebook.objects.filter(user=self.user)
        user2_notebooks = Notebook.objects.filter(user=other_user)
        
        self.assertEqual(user1_notebooks.count(), 1)
        self.assertEqual(user2_notebooks.count(), 1)
        self.assertEqual(user1_notebooks.first(), notebook1)
        self.assertEqual(user2_notebooks.first(), notebook2)


class SourceModelTests(TestCase):
    """Test cases for Source model."""

    def setUp(self):
        self.user = User.objects.create_user(
            username="testuser", email="test@example.com", password="testpass123"
        )
        self.notebook = Notebook.objects.create(
            user=self.user, name="Test Notebook"
        )

    def test_source_creation(self):
        """Test source creation."""
        source = Source.objects.create(
            notebook=self.notebook,
            source_type="file",
            title="test.pdf"
        )

        self.assertEqual(source.notebook, self.notebook)
        self.assertEqual(source.source_type, "file")
        self.assertEqual(source.title, "test.pdf")
        self.assertEqual(source.processing_status, "pending")

    def test_source_str_representation(self):
        """Test source string representation."""
        source = Source.objects.create(
            notebook=self.notebook,
            source_type="url",
            title="https://example.com"
        )
        
        self.assertEqual(str(source), "https://example.com")
        
        # Test without title
        source_no_title = Source.objects.create(
            notebook=self.notebook,
            source_type="file"
        )
        
        self.assertTrue(str(source_no_title).startswith("Source"))


class KnowledgeBaseItemModelTests(TestCase):
    """Test cases for KnowledgeBaseItem model."""

    def setUp(self):
        self.user = User.objects.create_user(
            username="testuser", email="test@example.com", password="testpass123"
        )

    def test_knowledge_base_item_creation(self):
        """Test knowledge base item creation."""
        item = KnowledgeBaseItem.objects.create(
            user=self.user,
            title="Test Document",
            content_type="document",
            content="Test content",
            tags=[],
            file_metadata={}
        )

        self.assertEqual(item.user, self.user)
        self.assertEqual(item.title, "Test Document")
        self.assertEqual(item.content_type, "document")
        self.assertEqual(item.content, "Test content")

    def test_knowledge_base_item_hash_generation(self):
        """Test that source hash is properly generated."""
        item = KnowledgeBaseItem.objects.create(
            user=self.user,
            title="Test Document",
            content="Test content",
            source_hash="test_hash_123",
            tags=[],
            file_metadata={}
        )

        self.assertEqual(item.source_hash, "test_hash_123")

    def test_knowledge_base_item_tags(self):
        """Test tags field functionality."""
        item = KnowledgeBaseItem.objects.create(
            user=self.user,
            title="Test Document",
            tags=["tag1", "tag2", "tag3"],
            file_metadata={}
        )

        self.assertEqual(item.tags, ["tag1", "tag2", "tag3"])


class BatchJobModelTests(TestCase):
    """Test cases for BatchJob and BatchJobItem models."""

    def setUp(self):
        self.user = User.objects.create_user(
            username="testuser", email="test@example.com", password="testpass123"
        )
        self.notebook = Notebook.objects.create(
            user=self.user, name="Test Notebook"
        )

    def test_batch_job_creation(self):
        """Test batch job creation."""
        batch_job = BatchJob.objects.create(
            notebook=self.notebook,
            job_type='url_parse',
            total_items=5
        )

        self.assertEqual(batch_job.notebook, self.notebook)
        self.assertEqual(batch_job.job_type, 'url_parse')
        self.assertEqual(batch_job.total_items, 5)
        self.assertEqual(batch_job.status, 'pending')
        self.assertEqual(batch_job.completed_items, 0)
        self.assertEqual(batch_job.failed_items, 0)

    def test_batch_job_item_creation(self):
        """Test batch job item creation."""
        batch_job = BatchJob.objects.create(
            notebook=self.notebook,
            job_type='file_upload',
            total_items=3
        )

        batch_item = BatchJobItem.objects.create(
            batch_job=batch_job,
            item_data={'filename': 'test.pdf'},
            upload_id='test_upload_123',
            status='pending'
        )

        self.assertEqual(batch_item.batch_job, batch_job)
        self.assertEqual(batch_item.item_data, {'filename': 'test.pdf'})
        self.assertEqual(batch_item.upload_id, 'test_upload_123')
        self.assertEqual(batch_item.status, 'pending')

    def test_batch_job_str_representation(self):
        """Test batch job string representation."""
        batch_job = BatchJob.objects.create(
            notebook=self.notebook,
            job_type='url_parse_media',
            total_items=2
        )

        expected = f"BatchJob {batch_job.id} (url_parse_media) - pending"
        self.assertEqual(str(batch_job), expected) 