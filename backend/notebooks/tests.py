import tempfile
import os
from unittest.mock import patch, MagicMock
from django.test import TestCase, override_settings
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from rest_framework.test import APITestCase
from rest_framework import status

from .models import Notebook, Source, KnowledgeBaseItem, KnowledgeItem, URLProcessingResult
from .utils.file_validator import FileValidator
from .utils.file_storage import FileStorageService

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


class SourceModelTests(TestCase):
    """Test cases for Source model."""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username="testuser", email="test@example.com", password="testpass123"
        )
        self.notebook = Notebook.objects.create(
            user=self.user,
            name="Test Notebook"
        )
    
    def test_source_creation(self):
        """Test source creation."""
        source = Source.objects.create(
            notebook=self.notebook,
            source_type="file",
            title="test.pdf",
            processing_status="pending"
        )
        
        self.assertEqual(source.notebook, self.notebook)
        self.assertEqual(source.source_type, "file")
        self.assertEqual(source.title, "test.pdf")


class URLProcessingResultTests(TestCase):
    """Test cases for URLProcessingResult model."""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com', 
            password='testpass123'
        )
        self.notebook = Notebook.objects.create(
            user=self.user,
            name="Test Notebook"
        )
        self.source = Source.objects.create(
            notebook=self.notebook,
            source_type="url",
            title="https://example.com",
            processing_status="done"
        )
    
    def test_url_processing_result_creation(self):
        """Test URLProcessingResult creation."""
        result = URLProcessingResult.objects.create(
            source=self.source,
            content_md="# Test Content\n\nThis is test content.",
        )
        
        self.assertEqual(result.source, self.source)
        self.assertEqual(result.content_md, "# Test Content\n\nThis is test content.")
        self.assertIsNone(result.downloaded_file)


class FileValidatorTests(TestCase):
    """Test cases for FileValidator."""
    
    def setUp(self):
        self.validator = FileValidator()
    
    def test_valid_pdf_file(self):
        """Test validation of valid PDF file."""
        test_file = SimpleUploadedFile(
            "test.pdf", 
            b"file_content", 
            content_type="application/pdf"
        )
        
        result = self.validator.validate_file(test_file)
        self.assertTrue(result["valid"])
        self.assertEqual(result["file_extension"], ".pdf")

    def test_invalid_file_extension(self):
        """Test validation of invalid file extension."""
        test_file = SimpleUploadedFile(
            "test.invalid", 
            b"file_content", 
            content_type="application/octet-stream"
        )
        
        result = self.validator.validate_file(test_file)
        self.assertFalse(result["valid"])
        self.assertIn("not supported", result["errors"][0])
    
    def test_empty_filename(self):
        """Test validation of empty filename."""
        test_file = SimpleUploadedFile(
            "", 
            b"file_content"
        )
        
        result = self.validator.validate_file(test_file)
        self.assertFalse(result["valid"])
        self.assertIn("Filename is required", result["errors"])


@override_settings(MEDIA_ROOT=tempfile.mkdtemp())
class NotebookAPITests(APITestCase):
    """Test cases for Notebook API endpoints."""

    def setUp(self):
        self.user = User.objects.create_user(
            username="testuser", email="test@example.com", password="testpass123"
        )
        self.client.force_authenticate(user=self.user)

    def test_create_notebook(self):
        """Test notebook creation via API."""
        url = reverse("notebook-list-create")
        data = {"name": "Test Notebook", "description": "Test description"}

        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Notebook.objects.count(), 1)

        notebook = Notebook.objects.first()
        self.assertEqual(notebook.name, "Test Notebook")
        self.assertEqual(notebook.user, self.user)

    def test_list_notebooks(self):
        """Test notebook listing via API."""
        # Create test notebooks
        Notebook.objects.create(user=self.user, name="Notebook 1")
        Notebook.objects.create(user=self.user, name="Notebook 2")

        # Create notebook for another user (should not appear)
        other_user = User.objects.create_user(
            username="other", email="other@example.com", password="pass"
        )
        Notebook.objects.create(user=other_user, name="Other Notebook")

        url = reverse("notebook-list-create")
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)
        self.assertEqual(response.data[0]["name"], "Notebook 2")  # Most recent first

    def test_retrieve_notebook(self):
        """Test notebook retrieval via API."""
        notebook = Notebook.objects.create(user=self.user, name="Test Notebook")

        url = reverse("notebook-detail", kwargs={"pk": notebook.pk})
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["name"], "Test Notebook")

    def test_update_notebook(self):
        """Test notebook update via API."""
        notebook = Notebook.objects.create(user=self.user, name="Original Name")

        url = reverse("notebook-detail", kwargs={"pk": notebook.pk})
        data = {"name": "Updated Name", "description": "Updated description"}

        response = self.client.patch(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        notebook.refresh_from_db()
        self.assertEqual(notebook.name, "Updated Name")
        self.assertEqual(notebook.description, "Updated description")

    def test_delete_notebook(self):
        """Test notebook deletion via API."""
        notebook = Notebook.objects.create(user=self.user, name="Test Notebook")

        url = reverse("notebook-detail", kwargs={"pk": notebook.pk})
        response = self.client.delete(url)

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(Notebook.objects.count(), 0)


@override_settings(MEDIA_ROOT=tempfile.mkdtemp())
class FileUploadAPITests(APITestCase):
    """Test cases for File Upload API endpoints."""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username="testuser", email="test@example.com", password="testpass123"
        )
        self.client.force_authenticate(user=self.user)
        self.notebook = Notebook.objects.create(
            user=self.user,
            name="Test Notebook"
        )

    @patch('notebooks.utils.upload_processor.UploadProcessor.process_upload')
    @patch('notebooks.utils.file_storage.FileStorageService.store_processed_file')
    def test_file_upload(self, mock_store, mock_process):
        """Test file upload via API."""
        # Mock the upload processor response
        mock_process.return_value = {
            'file_id': 123,  # Use integer ID
            'status': 'completed',
            'filename': 'test.pdf'
        }
        
        # Mock file storage to return a file ID
        mock_store.return_value = 123  # Use integer ID
        
        # Create a mock knowledge base item
        kb_item = KnowledgeBaseItem.objects.create(
            user=self.user,
            title="Test Document",
            content="Test content",
            content_type="document"
        )
        # The ID will be auto-assigned by Django, so we'll use that
        
        test_file = SimpleUploadedFile(
            "test.pdf",
            b"file_content",
            content_type="application/pdf"
        )
        
        # Mock the get_object_or_404 call to return our created kb_item
        with patch('notebooks.views.get_object_or_404') as mock_get:
            mock_get.return_value = kb_item
            
            url = reverse('file-upload', kwargs={'notebook_id': self.notebook.id})
            data = {'file': test_file, 'upload_file_id': 'test-upload-id'}
            
            response = self.client.post(url, data, format='multipart')
            
            # Check response
            self.assertEqual(response.status_code, status.HTTP_201_CREATED)
            self.assertTrue(response.data['success'])
            self.assertEqual(response.data['file_id'], 123)
            
            # Check that source was created
            self.assertEqual(Source.objects.count(), 1)
            source = Source.objects.first()
            self.assertEqual(source.notebook, self.notebook)
            self.assertEqual(source.source_type, "file")
            self.assertEqual(source.title, "test.pdf")


@override_settings(MEDIA_ROOT=tempfile.mkdtemp())
class URLParsingAPITests(APITestCase):
    """Test cases for URL Parsing API endpoints."""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username="testuser", email="test@example.com", password="testpass123"
        )
        self.client.force_authenticate(user=self.user)
        self.notebook = Notebook.objects.create(
            user=self.user,
            name="Test Notebook"
        )

    @patch('notebooks.utils.url_extractor.URLExtractor.process_url')
    def test_url_parse(self, mock_process_url):
        """Test URL parsing without media via API."""
        # Mock the URL extractor response
        mock_process_url.return_value = {
            'file_id': 124,  # Use integer ID
            'url': 'https://example.com',
            'status': 'completed',
            'content_preview': 'This is test content from the webpage.',
            'title': 'Example Page',
            'extraction_method': 'crawl4ai'
        }
        
        # Create a mock knowledge base item
        kb_item = KnowledgeBaseItem.objects.create(
            user=self.user,
            title="Example Page",
            content="This is test content from the webpage.",
            content_type="webpage"
        )
        # The ID will be auto-assigned by Django
        
        # Mock the get_object_or_404 call to return our created kb_item
        with patch('notebooks.views.get_object_or_404') as mock_get:
            mock_get.return_value = kb_item
            
            url = reverse('url-parse', kwargs={'notebook_id': self.notebook.id})
            data = {
                'url': 'https://example.com',
                'upload_url_id': 'test-url-upload-id'
            }
            
            response = self.client.post(url, data, format='json')
            
            # Check response
            self.assertEqual(response.status_code, status.HTTP_201_CREATED)
            self.assertTrue(response.data['success'])
            self.assertEqual(response.data['file_id'], 124)
            self.assertEqual(response.data['url'], 'https://example.com')
            self.assertEqual(response.data['title'], 'Example Page')
            self.assertEqual(response.data['extraction_method'], 'crawl4ai')
            
            # Check that source and URL result were created
            self.assertEqual(Source.objects.count(), 1)
            source = Source.objects.first()
            self.assertEqual(source.notebook, self.notebook)
            self.assertEqual(source.source_type, "url")
            self.assertEqual(source.title, "https://example.com")
            
            self.assertEqual(URLProcessingResult.objects.count(), 1)
            url_result = URLProcessingResult.objects.first()
            self.assertEqual(url_result.source, source)

    @patch('notebooks.utils.url_extractor.URLExtractor.process_url_with_media')
    def test_url_parse_with_media(self, mock_process_url_media):
        """Test URL parsing with media via API."""
        # Mock the URL extractor response for media processing
        mock_process_url_media.return_value = {
            'file_id': 125,  # Use integer ID
            'url': 'https://youtube.com/watch?v=test',
            'status': 'completed',
            'content_preview': 'Transcript of the video content...',
            'title': 'Test Video',
            'has_media': True,
            'processing_type': 'media'
        }
        
        # Create a mock knowledge base item
        kb_item = KnowledgeBaseItem.objects.create(
            user=self.user,
            title="Test Video",
            content="Transcript of the video content...",
            content_type="media"
        )
        # The ID will be auto-assigned by Django
        
        # Mock the get_object_or_404 call to return our created kb_item
        with patch('notebooks.views.get_object_or_404') as mock_get:
            mock_get.return_value = kb_item
            
            url = reverse('url-parse-media', kwargs={'notebook_id': self.notebook.id})
            data = {
                'url': 'https://youtube.com/watch?v=test',
                'extraction_strategy': 'cosine',
                'upload_url_id': 'test-media-upload-id'
            }
            
            response = self.client.post(url, data, format='json')
            
            # Check response
            self.assertEqual(response.status_code, status.HTTP_201_CREATED)
            self.assertTrue(response.data['success'])
            self.assertEqual(response.data['file_id'], 125)
            self.assertEqual(response.data['url'], 'https://youtube.com/watch?v=test')
            self.assertEqual(response.data['title'], 'Test Video')
            self.assertTrue(response.data['has_media'])
            self.assertEqual(response.data['processing_type'], 'media')
            
            # Check that source and URL result were created
            self.assertEqual(Source.objects.count(), 1)
            source = Source.objects.first()
            self.assertEqual(source.notebook, self.notebook)
            self.assertEqual(source.source_type, "url")
            self.assertEqual(source.title, "https://youtube.com/watch?v=test")
            
            self.assertEqual(URLProcessingResult.objects.count(), 1)
            url_result = URLProcessingResult.objects.first()
            self.assertEqual(url_result.source, source)

    def test_url_parse_invalid_url(self):
        """Test URL parsing with invalid URL."""
        url = reverse('url-parse', kwargs={'notebook_id': self.notebook.id})
        data = {
            'url': 'not-a-valid-url',
            'upload_url_id': 'test-url-upload-id'
        }
        
        response = self.client.post(url, data, format='json')
        
        # Check that validation fails
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('url', response.data['details'])

    def test_url_parse_missing_url(self):
        """Test URL parsing with missing URL."""
        url = reverse('url-parse', kwargs={'notebook_id': self.notebook.id})
        data = {
            'upload_url_id': 'test-url-upload-id'
        }
        
        response = self.client.post(url, data, format='json')
        
        # Check that validation fails
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('url', response.data['details'])

    def test_url_parse_unauthorized_notebook(self):
        """Test URL parsing with unauthorized notebook access."""
        # Create notebook for different user
        other_user = User.objects.create_user(
            username='other', email='other@example.com', password='pass'
        )
        other_notebook = Notebook.objects.create(
            user=other_user,
            name="Other Notebook"
        )
        
        url = reverse('url-parse', kwargs={'notebook_id': other_notebook.id})
        data = {
            'url': 'https://example.com',
            'upload_url_id': 'test-url-upload-id'
        }
        
        response = self.client.post(url, data, format='json')
        
        # Check that access is denied
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)