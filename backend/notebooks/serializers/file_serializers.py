"""
File upload and processing serializers for the notebooks module.
"""

from rest_framework import serializers
from ..models import (
    Source,
    ProcessingJob,
    KnowledgeBaseItem,
    KnowledgeBaseImage,
    KnowledgeItem,
)


class FileUploadSerializer(serializers.Serializer):
    """Serializer for file upload requests."""

    file = serializers.FileField()
    upload_file_id = serializers.CharField(required=False)


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
        """Ensure either file or files is provided."""
        file = data.get('file')
        files = data.get('files')
        
        if not file and not files:
            raise serializers.ValidationError("Either 'file' or 'files' must be provided.")
        
        if file and files:
            raise serializers.ValidationError("Provide either 'file' or 'files', not both.")
        
        return data


class ProcessingJobSerializer(serializers.ModelSerializer):
    """Serializer for processing jobs with MinIO object key support."""
    
    result_file_url = serializers.SerializerMethodField()
    
    class Meta:
        model = ProcessingJob
        fields = [
            "id",
            "job_type",
            "status",
            "result_file_object_key",
            "result_file_url",
            "result_file_metadata",
            "error_message",
            "created_at",
            "completed_at",
        ]
        read_only_fields = [
            "id",
            "created_at",
            "completed_at"
        ]
    
    def get_result_file_url(self, obj):
        """Get pre-signed URL for result file."""
        return obj.get_result_file_url() if obj.result_file_object_key else None


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
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at", "source_hash"]
    
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


class KnowledgeItemSerializer(serializers.ModelSerializer):
    """Serializer for notebook-knowledge base item links."""

    knowledge_base_item = KnowledgeBaseItemSerializer(read_only=True)

    class Meta:
        model = KnowledgeItem
        fields = [
            "id",
            "notebook",
            "knowledge_base_item",
            "source",
            "added_at",
            "notes",
        ]
        read_only_fields = ["id", "added_at"]


class SourceSerializer(serializers.ModelSerializer):
    """Serializer for source models with related data."""

    jobs = ProcessingJobSerializer(many=True, read_only=True)
    knowledge_items = KnowledgeItemSerializer(many=True, read_only=True)

    class Meta:
        model = Source
        fields = [
            "id",
            "notebook",
            "source_type",
            "title",
            "created_at",
            "needs_processing",
            "processing_status",
            "jobs",
            "knowledge_items",
        ]
        read_only_fields = [
            "id",
            "created_at",
            "needs_processing",
            "processing_status",
        ]
  