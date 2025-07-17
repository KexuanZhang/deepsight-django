from django.contrib import admin
from .models import PodcastJob


@admin.register(PodcastJob)
class PodcastJobAdmin(admin.ModelAdmin):
    list_display = ["id", "title", "status", "user", "created_at", "updated_at"]
    list_filter = ["status", "created_at", "updated_at"]
    search_fields = ["title", "id", "user__username"]
    readonly_fields = ["id", "created_at", "updated_at"]

    fieldsets = (
        ("Basic Information", {"fields": ("id", "user", "title", "description")}),
        ("Status", {"fields": ("status", "progress", "error_message")}),
        ("Files", {"fields": ("source_file_ids", "audio_object_key", "conversation_text")}),
        ("Metadata", {"fields": ("source_metadata", "file_metadata")}),
        ("Timestamps", {"fields": ("created_at", "updated_at")}),
    )

    def has_add_permission(self, request):
        # Prevent manual creation of jobs through admin
        return False
