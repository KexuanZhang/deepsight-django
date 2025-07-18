"""
Notebook-related serializers for the notebooks module.
"""

from rest_framework import serializers
from ..models import Notebook


class NotebookSerializer(serializers.ModelSerializer):
    """Serializer for Notebook model."""
    
    class Meta:
        model = Notebook
        fields = ["id", "name", "description", "created_at"]
        read_only_fields = ["id", "created_at"] 