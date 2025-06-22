from rest_framework import serializers
from .models import Report

class ReportSerializer(serializers.ModelSerializer):
    class Meta:
        model = Report
        fields = [
            'id',           # was 'report_id'
            'user',
            'notebooks',
            'topic',
            'transcript_content',
            'paper_content',
            'article_title',
            'model_provider',
            'retriever',
            'temperature',
            'top_p',
            'max_conv_turn',
            'status',
            'result_content',
            'error_message',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ('id', 'created_at', 'updated_at')

class ReportCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Report
        fields = [
            'user',
            'notebooks',
            'topic',
            'transcript_content',
            'paper_content',
            'article_title',
            'model_provider',
            'retriever',
            'temperature',
            'top_p',
            'max_conv_turn',
        ]
        read_only_fields = ('user',)
