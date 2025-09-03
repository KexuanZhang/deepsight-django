"""
Notebook-related serializers for the notebooks module following DRF best practices.
"""

from rest_framework import serializers
from django.contrib.auth import get_user_model
from ..models import Notebook

User = get_user_model()


class NotebookSerializer(serializers.ModelSerializer):
    """
    Serializer for Notebook model with comprehensive field handling.
    
    Provides basic CRUD operations with proper validation and read-only fields.
    """
    
    # Computed fields
    source_count = serializers.SerializerMethodField()
    knowledge_item_count = serializers.SerializerMethodField()
    chat_message_count = serializers.SerializerMethodField()
    last_activity = serializers.SerializerMethodField()
    ragflow_dataset_info = serializers.SerializerMethodField()
    
    class Meta:
        model = Notebook
        fields = [
            "id", "name", "description", "created_at", "updated_at",
            "source_count", "knowledge_item_count", "chat_message_count", 
            "last_activity", "ragflow_dataset_info"
        ]
        read_only_fields = [
            "id", "created_at", "updated_at", "source_count", 
            "knowledge_item_count", "chat_message_count", "last_activity",
            "ragflow_dataset_info"
        ]
    
    def get_source_count(self, obj):
        """Get count of knowledge base items in the notebook."""
        return obj.knowledge_base_items.count()
    
    def get_knowledge_item_count(self, obj):
        """Get count of processed knowledge base items."""
        return obj.knowledge_base_items.filter(parsing_status='done').count()
    
    def get_chat_message_count(self, obj):
        """Get count of chat messages in the notebook."""
        return obj.chat_messages.count()
    
    def get_last_activity(self, obj):
        """Get the timestamp of the last activity in the notebook."""
        latest_kb_item = obj.knowledge_base_items.order_by('-updated_at').first()
        latest_chat = obj.chat_messages.order_by('-timestamp').first()
        
        last_activity = obj.updated_at
        
        if latest_kb_item and latest_kb_item.updated_at > last_activity:
            last_activity = latest_kb_item.updated_at
        
        if latest_chat and latest_chat.timestamp > last_activity:
            last_activity = latest_chat.timestamp
        
        return last_activity
    
    def get_ragflow_dataset_info(self, obj):
        """Get RagFlow dataset information for the notebook."""
        try:
            ragflow_dataset = obj.ragflow_dataset
            return {
                "id": ragflow_dataset.ragflow_dataset_id,
                "status": ragflow_dataset.status,
                "is_ready": ragflow_dataset.is_ready(),
                "document_count": ragflow_dataset.get_document_count() if ragflow_dataset.is_ready() else 0,
                "error_message": ragflow_dataset.error_message or None
            }
        except AttributeError:
            # No RagFlow dataset exists yet
            return {
                "id": None,
                "status": "not_created",
                "is_ready": False,
                "document_count": 0,
                "error_message": None
            }
    
    def validate_name(self, value):
        """Validate notebook name."""
        if not value or not value.strip():
            raise serializers.ValidationError("Notebook name cannot be empty.")
        
        if len(value.strip()) > 100:
            raise serializers.ValidationError("Notebook name cannot exceed 100 characters.")
        
        return value.strip()
    
    def validate_description(self, value):
        """Validate notebook description."""
        if value and len(value.strip()) > 500:
            raise serializers.ValidationError("Description cannot exceed 500 characters.")
        
        return value.strip() if value else ""


class NotebookListSerializer(serializers.ModelSerializer):
    """
    Lightweight serializer for notebook listing with minimal fields.
    
    Used in list views where full detail is not needed for performance.
    """
    
    item_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Notebook
        fields = ["id", "name", "description", "created_at", "item_count"]
        read_only_fields = ["id", "created_at", "item_count"]
    
    def get_item_count(self, obj):
        """Get total count of items in the notebook."""
        return obj.knowledge_base_items.count()


class NotebookCreateSerializer(serializers.ModelSerializer):
    """
    Serializer for notebook creation with specific validation rules.
    """
    
    class Meta:
        model = Notebook
        fields = ["name", "description"]
    
    def validate_name(self, value):
        """Validate notebook name for creation."""
        if not value or not value.strip():
            raise serializers.ValidationError("Notebook name is required.")
        
        value = value.strip()
        
        if len(value) < 2:
            raise serializers.ValidationError("Notebook name must be at least 2 characters long.")
        
        if len(value) > 100:
            raise serializers.ValidationError("Notebook name cannot exceed 100 characters.")
        
        # Check for duplicate names for the user
        request = self.context.get('request')
        if request and hasattr(request, 'user'):
            if Notebook.objects.filter(user=request.user, name__iexact=value).exists():
                raise serializers.ValidationError("A notebook with this name already exists.")
        
        return value
    
    def create(self, validated_data):
        """Create notebook with user from request context."""
        request = self.context.get('request')
        if request and hasattr(request, 'user'):
            validated_data['user'] = request.user
        
        return super().create(validated_data)


class NotebookUpdateSerializer(serializers.ModelSerializer):
    """
    Serializer for notebook updates with specific validation rules.
    """
    
    class Meta:
        model = Notebook
        fields = ["name", "description"]
    
    def validate_name(self, value):
        """Validate notebook name for updates."""
        if not value or not value.strip():
            raise serializers.ValidationError("Notebook name cannot be empty.")
        
        value = value.strip()
        
        if len(value) < 2:
            raise serializers.ValidationError("Notebook name must be at least 2 characters long.")
        
        if len(value) > 100:
            raise serializers.ValidationError("Notebook name cannot exceed 100 characters.")
        
        # Check for duplicate names for the user (excluding current notebook)
        request = self.context.get('request')
        if request and hasattr(request, 'user') and self.instance:
            if Notebook.objects.filter(
                user=request.user, 
                name__iexact=value
            ).exclude(pk=self.instance.pk).exists():
                raise serializers.ValidationError("A notebook with this name already exists.")
        
        return value 