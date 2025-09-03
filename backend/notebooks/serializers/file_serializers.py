"""
File upload and processing serializers for the notebooks module.
"""

from rest_framework import serializers
from ..models import (
    KnowledgeBaseItem,
    KnowledgeBaseImage,
)
from ..utils.helpers import check_source_duplicate, check_content_duplicate


class FileUploadSerializer(serializers.Serializer):
    """Serializer for file upload requests."""

    file = serializers.FileField()
    upload_file_id = serializers.CharField(required=False)
    
    def validate(self, data):
        """Check for duplicate filename or content before processing."""
        file = data.get('file')
        if not file:
            return data
            
        # Get original filename before any processing
        original_filename = file.name
        
        # Get user and notebook from context
        request = self.context.get('request')
        notebook_id = self.context.get('notebook_id')
        
        if request and hasattr(request, 'user') and request.user.is_authenticated:
            user_id = request.user.id
            
            # Detect if this is pasted text (markdown files with generated names)
            is_pasted_text = (
                original_filename.endswith('.md') and 
                file.content_type in ['text/markdown', 'text/plain'] and
                file.size < 50000  # Reasonable limit for pasted text
            )
            
            import logging
            logger = logging.getLogger(__name__)
            logger.info(f"[FileUploadSerializer] Validating file: {original_filename}, is_pasted_text: {is_pasted_text}, content_type: {file.content_type}, size: {file.size}")
            
            if is_pasted_text:
                # For pasted text, check content hash instead of filename
                try:
                    file_content = file.read().decode('utf-8', errors='ignore')
                    file.seek(0)  # Reset file pointer
                    
                    existing_item = check_content_duplicate(file_content, user_id, notebook_id)
                    if existing_item:
                        raise serializers.ValidationError({
                            'file': f'This text content already exists in your workspace. Duplicate content detected.',
                            'existing_item_id': str(existing_item.id)
                        })
                    # For pasted text, we only check content, not filename
                    return data
                except serializers.ValidationError:
                    # Re-raise ValidationError so it's properly handled
                    raise
                except Exception as e:
                    # If we can't read content, fall back to filename check
                    import logging
                    logger = logging.getLogger(__name__)
                    logger.warning(f"Could not read file content for duplicate check: {e}")
            
            # For regular files, check source duplicate using original filename
            existing_item = check_source_duplicate(original_filename, user_id, notebook_id)
            if existing_item:
                raise serializers.ValidationError({
                    'file': f'File with name "{original_filename}" already exists. Check the knowledge base.',
                    'existing_item_id': str(existing_item.id)
                })
        
        return data


class VideoImageExtractionSerializer(serializers.Serializer):
    """Serializer for video image extraction requests."""
    video_file_id = serializers.CharField(
        max_length=64,
        help_text="Video file ID in format f_{file_id}"
    )
    # Image processing parameters with defaults matching DeepSight
    extract_interval = serializers.IntegerField(
        default=8,
        min_value=1,
        max_value=3600,
        help_text="Frame extraction interval in seconds (default: 8)"
    )
    pixel_threshold = serializers.IntegerField(
        default=3,
        min_value=0,
        max_value=64,
        help_text="Max Hamming distance for pixel deduplication (default: 3)"
    )
    sequential_deep_threshold = serializers.FloatField(
        default=0.8,
        min_value=0.0,
        max_value=1.0,
        help_text="Cosine similarity threshold for sequential deep deduplication (default: 0.8)"
    )
    global_deep_threshold = serializers.FloatField(
        default=0.85,
        min_value=0.0,
        max_value=1.0,
        help_text="Cosine similarity threshold for global deep deduplication (default: 0.85)"
    )
    min_words = serializers.IntegerField(
        default=20,
        min_value=0,
        help_text="Minimum words per caption (default: 20)"
    )
    max_words = serializers.IntegerField(
        default=100,
        min_value=0,
        help_text="Maximum words per caption (default: 100)"
    )


class BatchFileUploadSerializer(serializers.Serializer):
    """Serializer for batch file upload requests."""
    
    # Accept either a single file or multiple files
    file = serializers.FileField(required=False)
    files = serializers.ListField(
        child=serializers.FileField(),
        required=False,
        allow_empty=False
    )
    upload_file_id = serializers.CharField(required=False)

    def validate(self, data):
        """Ensure either file or files is provided and check for duplicates."""
        file = data.get('file')
        files = data.get('files')
        
        if not file and not files:
            raise serializers.ValidationError("Either 'file' or 'files' must be provided.")
        
        if file and files:
            raise serializers.ValidationError("Provide either 'file' or 'files', not both.")
        
        # Check for duplicates
        request = self.context.get('request')
        notebook_id = self.context.get('notebook_id')
        
        if request and hasattr(request, 'user') and request.user.is_authenticated:
            user_id = request.user.id
            
            # Check single file
            if file:
                existing_item = check_source_duplicate(file.name, user_id, notebook_id)
                if existing_item:
                    raise serializers.ValidationError({
                        'file': f'File with name "{file.name}" already exists. Check the knowledge base.',
                        'existing_item_id': str(existing_item.id)
                    })
            
            # Check multiple files
            if files:
                duplicate_files = []
                for f in files:
                    existing_item = check_source_duplicate(f.name, user_id, notebook_id)
                    if existing_item:
                        duplicate_files.append({
                            'filename': f.name,
                            'existing_item_id': str(existing_item.id)
                        })
                
                if duplicate_files:
                    raise serializers.ValidationError({
                        'files': 'Some files already exist. Check the knowledge base.',
                        'duplicates': duplicate_files
                    })
        
        return data




class KnowledgeBaseItemSerializer(serializers.ModelSerializer):
    """Serializer for knowledge base items with MinIO object key support."""
    
    file_url = serializers.SerializerMethodField()
    original_file_url = serializers.SerializerMethodField()
    
    class Meta:
        model = KnowledgeBaseItem
        fields = [
            "id",
            "title",
            "content_type",
            "content",
            "file_object_key",
            "file_url",
            "original_file_object_key", 
            "original_file_url",
            "file_metadata",
            "metadata",
            "tags",
            "source_hash",
            "parsing_status",
            "ragflow_document_id",
            "ragflow_processing_status",
            "notes",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id", "created_at", "updated_at", "source_hash",
            "ragflow_document_id", "ragflow_processing_status"
        ]
    
    def get_file_url(self, obj):
        """Get pre-signed URL for processed file."""
        return obj.get_file_url() if obj.file_object_key else None
    
    def get_original_file_url(self, obj):
        """Get pre-signed URL for original file."""
        return obj.get_original_file_url() if obj.original_file_object_key else None


class KnowledgeBaseImageSerializer(serializers.ModelSerializer):
    """Serializer for knowledge base images with MinIO storage support."""
    
    image_url = serializers.SerializerMethodField()
    figure_data_dict = serializers.SerializerMethodField()
    
    class Meta:
        model = KnowledgeBaseImage
        fields = [
            "id",
            "knowledge_base_item",
            "image_caption",
            "minio_object_key",
            "image_url",
            "content_type",
            "file_size",
            "image_metadata",
            "figure_data_dict",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id", 
            "image_url", 
            "figure_data_dict",
            "created_at", 
            "updated_at"
        ]
    
    def get_image_url(self, obj):
        """Get pre-signed URL for image access"""
        return obj.get_image_url()
    
    def get_figure_data_dict(self, obj):
        """Get figure_data.json compatible dictionary"""
        return obj.to_figure_data_dict()


class KnowledgeBaseImageCreateUpdateSerializer(serializers.ModelSerializer):
    """Serializer for creating/updating knowledge base images."""
    
    class Meta:
        model = KnowledgeBaseImage
        fields = [
            "knowledge_base_item",
            "image_caption",
        ]
    
    # validate_figure_name method removed as field no longer exists


  