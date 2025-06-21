from rest_framework import serializers
from .models import (
    Notebook,
    Source,
    URLProcessingResult,
    ProcessingJob,
    # SearchResult,
    KnowledgeItem,
)

class NotebookSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notebook
        # Only these four fields go over the wire:
        fields = ['id', 'name', 'description', 'created_at']
        read_only_fields = ['id', 'created_at']
# notebooks/serializers.py

from rest_framework import serializers
from .models import Source

class FileUploadSerializer(serializers.Serializer):
    file           = serializers.FileField()
    upload_file_id = serializers.CharField(required=False)





class URLProcessingResultSerializer(serializers.ModelSerializer):
    class Meta:
        model = URLProcessingResult
        fields = [
            'id', 'content_md', 'downloaded_file', 'error_message', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']


class ProcessingJobSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProcessingJob
        fields = [
            'id', 'job_type', 'status', 'result_file', 'error_message',
            'created_at', 'completed_at'
        ]
        read_only_fields = ['id', 'status', 'result_file', 'error_message', 'created_at', 'completed_at']


# class SearchResultSerializer(serializers.ModelSerializer):
#     class Meta:
#         model = SearchResult
#         fields = ['id', 'snippet', 'metadata', 'created_at']
#         read_only_fields = ['id', 'created_at']


class KnowledgeItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = KnowledgeItem
        fields = [
            'id', 'notebook', 'source', 'content', 'file', 'metadata', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']


class SourceSerializer(serializers.ModelSerializer):
    url_result = URLProcessingResultSerializer(read_only=True)
    jobs = ProcessingJobSerializer(many=True, read_only=True)
    # search_results = SearchResultSerializer(many=True, read_only=True)

    class Meta:
        model = Source
        fields = [
            'id', 'notebook', 'source_type', 'title', 'created_at',
            'needs_processing', 'processing_status',
            'url_result', 'jobs'
        ]
        read_only_fields = [
            'id', 'created_at', 'processing_status',
            'url_result', 'jobs'
        ]

