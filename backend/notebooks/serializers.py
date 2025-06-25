from rest_framework import serializers
from .models import (
    Notebook,
    Source,
    URLProcessingResult,
    ProcessingJob,
    KnowledgeItem,
    KnowledgeBaseItem,
)


class NotebookSerializer(serializers.ModelSerializer):
    """Serializer for Notebook model."""

    class Meta:
        model = Notebook
        fields = ["id", "name", "description", "created_at"]
        read_only_fields = ["id", "created_at"]


class FileUploadSerializer(serializers.Serializer):
    """Serializer for file upload requests."""

    file = serializers.FileField()
    upload_file_id = serializers.CharField(required=False)


class URLParseSerializer(serializers.Serializer):
    """Serializer for URL parsing requests."""
    
    url = serializers.URLField()
    upload_url_id = serializers.CharField(required=False)


class URLParseWithMediaSerializer(serializers.Serializer):
    """Serializer for URL parsing with media extraction requests."""
    url = serializers.URLField(
        help_text="URL to parse and extract media from"
    )
    upload_url_id = serializers.CharField(
        max_length=64,
        required=False,
        help_text="Custom upload ID for tracking"
    )


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
        max_value=300,
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
        default=5,
        min_value=0,
        max_value=100,
        help_text="Minimum words/numbers required to keep an image via OCR filter (default: 5)"
    )


class URLProcessingResultSerializer(serializers.ModelSerializer):
    """Serializer for URL processing results."""

    class Meta:
        model = URLProcessingResult
        fields = ["id", "content_md", "downloaded_file", "error_message", "created_at"]
        read_only_fields = ["id", "created_at"]


class ProcessingJobSerializer(serializers.ModelSerializer):
    """Serializer for background processing jobs."""

    class Meta:
        model = ProcessingJob
        fields = [
            "id",
            "job_type",
            "status",
            "result_file",
            "error_message",
            "created_at",
            "completed_at",
        ]
        read_only_fields = [
            "id",
            "status",
            "result_file",
            "error_message",
            "created_at",
            "completed_at",
        ]


class KnowledgeBaseItemSerializer(serializers.ModelSerializer):
    """Serializer for knowledge base items."""

    class Meta:
        model = KnowledgeBaseItem
        fields = [
            "id",
            "title",
            "content_type",
            "content",
            "file",
            "original_file",
            "metadata",
            "tags",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at", "source_hash"]


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

    url_result = URLProcessingResultSerializer(read_only=True)
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
            "url_result",
            "jobs",
            "knowledge_items",
        ]
        read_only_fields = [
            "id",
            "created_at",
            "processing_status",
            "url_result",
            "jobs",
            "knowledge_items",
        ]
