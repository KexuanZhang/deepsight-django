from rest_framework import serializers
from .models import (
    Notebook,
    Source,
    UploadedFile,
    PastedTextFile,
    URLProcessingResult,
    ProcessingJob,
    # SearchResult,
    KnowledgeItem,
)


class UploadedFileSerializer(serializers.ModelSerializer):
    class Meta:
        model = UploadedFile
        fields = [
            'id', 'file', 'content_type', 'original_name', 'uploaded_at'
        ]
        read_only_fields = ['id', 'content_type', 'original_name', 'uploaded_at']


class PastedTextFileSerializer(serializers.ModelSerializer):
    class Meta:
        model = PastedTextFile
        fields = ['id', 'file', 'created_at']
        read_only_fields = ['id', 'created_at']


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
    upload = UploadedFileSerializer(read_only=True)
    pasted_text_file = PastedTextFileSerializer(read_only=True)
    url_result = URLProcessingResultSerializer(read_only=True)
    jobs = ProcessingJobSerializer(many=True, read_only=True)
    # search_results = SearchResultSerializer(many=True, read_only=True)

    class Meta:
        model = Source
        fields = [
            'id', 'notebook', 'source_type', 'title', 'created_at',
            'needs_processing', 'processing_status',
            'upload', 'pasted_text_file', 'url_result', 'jobs'
        ]
        read_only_fields = [
            'id', 'created_at', 'processing_status',
            'upload', 'pasted_text_file', 'url_result', 'jobs'
        ]


class NotebookSerializer(serializers.ModelSerializer):
    sources = SourceSerializer(many=True, read_only=True)
    knowledge_items = KnowledgeItemSerializer(many=True, read_only=True)

    class Meta:
        model = Notebook
        fields = ['id', 'user', 'name', 'description', 'created_at', 'sources', 'knowledge_items']
        read_only_fields = ['id', 'created_at']
