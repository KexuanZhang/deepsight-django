"""
Batch processing serializers for the notebooks module.
"""

from rest_framework import serializers
from ..models import BatchJob, BatchJobItem


class BatchJobSerializer(serializers.ModelSerializer):
    """Serializer for batch job tracking."""
    
    class Meta:
        model = BatchJob
        fields = [
            'id', 'job_type', 'status', 'total_items', 
            'completed_items', 'failed_items', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class BatchJobItemSerializer(serializers.ModelSerializer):
    """Serializer for individual batch job items."""
    
    class Meta:
        model = BatchJobItem
        fields = [
            'id', 'item_data', 'upload_id', 'status', 
            'result_data', 'error_message', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at'] 