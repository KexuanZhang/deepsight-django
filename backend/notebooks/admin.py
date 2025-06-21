from django.contrib import admin
from .models import (
    Notebook,
    Source,
    URLProcessingResult,
    ProcessingJob,
    # SearchResult,
    KnowledgeBaseItem,
    KnowledgeItem,
)





class URLProcessingResultInline(admin.StackedInline):
    model = URLProcessingResult
    readonly_fields = ("created_at",)
    extra = 0


class ProcessingJobInline(admin.TabularInline):
    model = ProcessingJob
    readonly_fields = ("status", "result_file", "error_message", "created_at", "completed_at")
    fields = ("job_type", "status", "created_at", "completed_at", "result_file", "error_message")
    extra = 0
    show_change_link = True


# class SearchResultInline(admin.TabularInline):
#     model = SearchResult
#     readonly_fields = ("snippet", "metadata", "created_at")
#     extra = 0
#     show_change_link = True


class SourceAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "notebook",
        "source_type",
        "title",
        "processing_status",
        "needs_processing",
        "created_at",
    )
    list_filter = ("source_type", "processing_status", "needs_processing")
    search_fields = ("title",)
    readonly_fields = ("created_at",)
    inlines = [
        URLProcessingResultInline,
        ProcessingJobInline,
        # SearchResultInline,
    ]


@admin.register(Notebook)
class NotebookAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "name", "created_at")
    search_fields = ("name", "user__username",)
    list_filter = ("created_at",)
    readonly_fields = ("created_at",)
    inlines = [
        # Optionally show sources inline if desired
        # SourceInline,
    ]


@admin.register(Source)
class SourceAdminNoInline(admin.ModelAdmin):
    # If you want a standalone Source admin view
    list_display = (
        "id",
        "notebook",
        "source_type",
        "title",
        "processing_status",
        "needs_processing",
        "created_at",
    )
    list_filter = ("source_type", "processing_status", "needs_processing")
    search_fields = ("title",)
    readonly_fields = ("created_at",)
    inlines = [URLProcessingResultInline, ProcessingJobInline]


@admin.register(ProcessingJob)
class ProcessingJobAdmin(admin.ModelAdmin):
    list_display = ("id", "source", "job_type", "status", "created_at", "completed_at")
    list_filter = ("job_type", "status")
    search_fields = ("source__title",)
    readonly_fields = ("created_at", "completed_at")


@admin.register(KnowledgeBaseItem)
class KnowledgeBaseItemAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "title", "content_type", "created_at")
    list_filter = ("content_type", "created_at")
    search_fields = ("title", "content", "user__username")
    readonly_fields = ("created_at", "updated_at", "source_hash")
    fieldsets = (
        (None, {
            'fields': ('user', 'title', 'content_type')
        }),
        ('Content', {
            'fields': ('file', 'content', 'tags')
        }),
        ('Metadata', {
            'fields': ('metadata', 'source_hash'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )


@admin.register(KnowledgeItem)
class KnowledgeItemAdmin(admin.ModelAdmin):
    list_display = ("id", "notebook", "knowledge_base_item", "source", "added_at")
    list_filter = ("notebook", "added_at")
    search_fields = ("knowledge_base_item__title", "notebook__name", "notes")
    readonly_fields = ("added_at",)
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            'notebook', 'knowledge_base_item', 'source'
        )


# Register remaining models in default fashion
admin.site.register(URLProcessingResult)
# admin.site.register(SearchResult)
