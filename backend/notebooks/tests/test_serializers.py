"""
Serializer tests for the notebooks module.
"""

from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase

from ..models import Notebook, KnowledgeBaseItem
from ..serializers import (
    NotebookSerializer,
    FileUploadSerializer,
    URLParseSerializer,
    BatchJobSerializer
)

User = get_user_model()


class NotebookSerializerTests(TestCase):
    """Test cases for NotebookSerializer."""

    def setUp(self):
        self.user = User.objects.create_user(
            username="testuser", email="test@example.com", password="testpass123"
        )

    def test_notebook_serialization(self):
        """Test notebook serialization."""
        notebook = Notebook.objects.create(
            user=self.user, name="Test Notebook", description="Test description"
        )

        serializer = NotebookSerializer(notebook)
        data = serializer.data

        self.assertEqual(data['name'], "Test Notebook")
        self.assertEqual(data['description'], "Test description")
        self.assertIn('id', data)
        self.assertIn('created_at', data)

    def test_notebook_deserialization(self):
        """Test notebook creation from serialized data."""
        data = {
            'name': 'New Notebook',
            'description': 'New description'
        }

        serializer = NotebookSerializer(data=data)
        self.assertTrue(serializer.is_valid())

        # Test that read-only fields are not included in validated_data
        self.assertNotIn('id', serializer.validated_data)
        self.assertNotIn('created_at', serializer.validated_data)


class FileUploadSerializerTests(TestCase):
    """Test cases for FileUploadSerializer."""

    def test_valid_file_upload_data(self):
        """Test validation of valid file upload data."""
        from django.core.files.uploadedfile import SimpleUploadedFile
        
        file_content = b"Test file content"
        uploaded_file = SimpleUploadedFile(
            "test.txt", file_content, content_type="text/plain"
        )

        data = {
            'file': uploaded_file,
            'upload_file_id': 'test_upload_123'
        }

        serializer = FileUploadSerializer(data=data)
        self.assertTrue(serializer.is_valid())

    def test_missing_file(self):
        """Test validation with missing file."""
        data = {
            'upload_file_id': 'test_upload_123'
        }

        serializer = FileUploadSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('file', serializer.errors)


class URLParseSerializerTests(TestCase):
    """Test cases for URLParseSerializer."""

    def test_valid_url_data(self):
        """Test validation of valid URL data."""
        data = {
            'url': 'https://example.com',
            'upload_url_id': 'test_url_123'
        }

        serializer = URLParseSerializer(data=data)
        self.assertTrue(serializer.is_valid())

    def test_invalid_url_format(self):
        """Test validation with invalid URL format."""
        data = {
            'url': 'not-a-valid-url'
        }

        serializer = URLParseSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('url', serializer.errors)

    def test_missing_url(self):
        """Test validation with missing URL."""
        data = {}

        serializer = URLParseSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('url', serializer.errors) 