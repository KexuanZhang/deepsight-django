"""
Service tests for the notebooks module.
"""

from unittest.mock import Mock, patch
from django.test import TestCase
from django.contrib.auth import get_user_model

from ..models import Notebook
from ..services.notebook_service import NotebookService
from ..exceptions import NotebookNotFoundError

User = get_user_model()


class NotebookServiceTests(TestCase):
    """Test cases for NotebookService."""

    def setUp(self):
        self.user = User.objects.create_user(
            username="testuser", email="test@example.com", password="testpass123"
        )
        self.service = NotebookService()

    def test_get_user_notebooks(self):
        """Test getting user notebooks."""
        # Create test notebooks
        notebook1 = Notebook.objects.create(user=self.user, name="Notebook 1")
        notebook2 = Notebook.objects.create(user=self.user, name="Notebook 2")

        # Create notebook for another user (should not appear)
        other_user = User.objects.create_user(
            username="other", email="other@example.com", password="pass"
        )
        Notebook.objects.create(user=other_user, name="Other Notebook")

        notebooks = self.service.get_user_notebooks(self.user)

        self.assertEqual(notebooks.count(), 2)
        self.assertIn(notebook1, notebooks)
        self.assertIn(notebook2, notebooks)

    def test_create_notebook(self):
        """Test notebook creation via service."""
        from unittest.mock import Mock
        
        # Mock serializer
        mock_serializer = Mock()
        mock_serializer.save.return_value = Mock(
            id="test-id", name="Test Notebook", user=self.user
        )

        result = self.service.create_notebook(mock_serializer, self.user)

        mock_serializer.save.assert_called_once_with(user=self.user)
        self.assertIsNotNone(result)

    def test_get_notebook_or_404_success(self):
        """Test successful notebook retrieval."""
        notebook = Notebook.objects.create(user=self.user, name="Test Notebook")

        result = self.service.get_notebook_or_404(str(notebook.id), self.user)

        self.assertEqual(result, notebook)

    def test_get_notebook_or_404_not_found(self):
        """Test notebook not found raises exception."""
        with self.assertRaises(NotebookNotFoundError):
            self.service.get_notebook_or_404("non-existent-id", self.user)

    def test_get_notebook_or_404_wrong_user(self):
        """Test accessing another user's notebook raises exception."""
        other_user = User.objects.create_user(
            username="other", email="other@example.com", password="pass"
        )
        notebook = Notebook.objects.create(user=other_user, name="Other Notebook")

        with self.assertRaises(NotebookNotFoundError):
            self.service.get_notebook_or_404(str(notebook.id), self.user) 