"""
View tests for the notebooks module.
"""

from django.test import TestCase
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework.test import APITestCase
from rest_framework import status

from ..models import Notebook

User = get_user_model()


class NotebookViewTests(APITestCase):
    """Test cases for Notebook API views."""

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
        
        url = reverse("notebook-detail", kwargs={"pk": str(notebook.id)})
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["name"], "Test Notebook")

    def test_unauthorized_access(self):
        """Test that unauthorized users cannot access notebooks."""
        self.client.force_authenticate(user=None)
        
        url = reverse("notebook-list-create")
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_user_isolation(self):
        """Test that users can only access their own notebooks."""
        other_user = User.objects.create_user(
            username="other", email="other@example.com", password="pass"
        )
        other_notebook = Notebook.objects.create(user=other_user, name="Other Notebook")

        # Try to access other user's notebook
        url = reverse("notebook-detail", kwargs={"pk": str(other_notebook.id)})
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND) 