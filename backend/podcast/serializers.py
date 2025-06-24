from rest_framework import serializers
from .models import PodcastJob


class PodcastJobSerializer(serializers.ModelSerializer):
    job_id = serializers.UUIDField(read_only=True)
    audio_url = serializers.SerializerMethodField()

    class Meta:
        model = PodcastJob
        fields = [
            "job_id",
            "title",
            "description",
            "status",
            "progress",
            "created_at",
            "updated_at",
            "audio_url",
            "conversation_text",
            "error_message",
            "source_file_ids",
            "source_metadata",
            "duration_seconds",
        ]
        read_only_fields = [
            "job_id",
            "status",
            "progress",
            "created_at",
            "updated_at",
            "audio_url",
            "conversation_text",
            "error_message",
            "duration_seconds",
        ]

    def get_audio_url(self, obj):
        return obj.audio_url


class PodcastJobCreateSerializer(serializers.Serializer):
    source_file_ids = serializers.ListField(
        child=serializers.CharField(),
        help_text="List of source file IDs to generate podcast from",
    )
    title = serializers.CharField(
        max_length=200,
        default="Generated Podcast",
        help_text="Title for the generated podcast",
    )
    description = serializers.CharField(
        required=False,
        allow_blank=True,
        help_text="Description for the generated podcast",
    )

    def validate_source_file_ids(self, value):
        if not value:
            raise serializers.ValidationError("At least one source file ID is required")
        return value


class PodcastJobListSerializer(serializers.ModelSerializer):
    job_id = serializers.UUIDField(read_only=True)
    audio_url = serializers.SerializerMethodField()

    class Meta:
        model = PodcastJob
        fields = [
            "job_id",
            "title",
            "description",
            "status",
            "progress",
            "created_at",
            "updated_at",
            "audio_url",
            "error_message",
            "duration_seconds",
        ]

    def get_audio_url(self, obj):
        return obj.audio_url
