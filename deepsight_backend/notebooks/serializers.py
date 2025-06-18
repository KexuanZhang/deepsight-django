# notebooks/serializers.py
from rest_framework import serializers
from .models import Notebook, UploadedFile, NotebookSource
class UploadedFileUploadSerializer(serializers.Serializer):
    file = serializers.FileField()

class UploadedFileSerializer(serializers.ModelSerializer):
    class Meta:
        model = UploadedFile
        fields = (
            'id',
            'upload_file_id',
            'notebook',
            'file',
            'original_filename',
            'file_extension',
            'content_type',
            'file_size',
            'status',
            'parsing_status',
            'validation_result',
            'processing_result',
            'created_at',
            'updated_at',
        )
        read_only_fields = (
            'id',
            'upload_file_id',
            'notebook',
            'original_filename',
            'file_extension',
            'content_type',
            'file_size',
            'status',
            'parsing_status',
            'validation_result',
            'processing_result',
            'created_at',
            'updated_at',
        )

# notebooks/serializers.py

class NotebookSourceSerializer(serializers.ModelSerializer):
    class Meta:
        model = NotebookSource
        fields = [
            'source_id',
            'notebook',
            'source_type',
            'uploaded_file',
            'url',
            'raw_text',
        ]
        read_only_fields = ['source_id']

    def validate(self, attrs):
        st = attrs.get('source_type')
        # require the correct field for each type
        if st == NotebookSource.SOURCE_FILE and not attrs.get('uploaded_file'):
            raise serializers.ValidationError("uploaded_file is required for file sources")
        if st == NotebookSource.SOURCE_LINK and not attrs.get('url'):
            raise serializers.ValidationError("url is required for link sources")
        if st == NotebookSource.SOURCE_TEXT and not attrs.get('raw_text'):
            raise serializers.ValidationError("raw_text is required for text sources")
        return attrs


class NotebookSerializer(serializers.ModelSerializer):
    uploaded_files = UploadedFileSerializer(many=True, read_only=True)
    sources = NotebookSourceSerializer(many=True, read_only=True)

    class Meta:
        model = Notebook
        fields = (
            'id',
            'user',
            'name',
            'created_at',
            'uploaded_files',
            'sources',
        )
        read_only_fields = ('id', 'user', 'created_at')
