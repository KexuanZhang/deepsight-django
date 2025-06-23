from django.contrib import admin
from django.utils.html import format_html
from .models import (
    Notebook,
    Source,
    URLProcessingResult,
    ProcessingJob,
    KnowledgeBaseItem,
    KnowledgeItem,
)


class URLProcessingResultInline(admin.StackedInline):
    """Inline admin for URL processing results."""
    model = URLProcessingResult
    readonly_fields = ("created_at",)
    extra = 0
    fields = ("content_md", "downloaded_file", "error_message", "created_at")


class ProcessingJobInline(admin.TabularInline):
    """Inline admin for processing jobs."""
    model = ProcessingJob
    readonly_fields = ("status", "result_file", "error_message", "created_at", "completed_at")
    fields = ("job_type", "status", "created_at", "completed_at", "result_file", "error_message")
    extra = 0
    show_change_link = True


class KnowledgeItemInline(admin.TabularInline):
    """Inline admin for knowledge items."""
    model = KnowledgeItem
    readonly_fields = ("added_at",)
    fields = ("knowledge_base_item", "source", "notes", "added_at")
    extra = 0
    show_change_link = True


@admin.register(Notebook)
class NotebookAdmin(admin.ModelAdmin):
    """Admin configuration for Notebook model."""
    list_display = ("id", "user", "name", "get_item_count", "created_at")
    search_fields = ("name", "user__username", "user__email")
    list_filter = ("created_at", "user")
    readonly_fields = ("created_at",)
    inlines = [KnowledgeItemInline]
    
    def get_item_count(self, obj):
        """Get count of knowledge items in notebook."""
        return obj.knowledge_items.count()
    get_item_count.short_description = "Items"
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('user').prefetch_related('knowledge_items')


@admin.register(Source)
class SourceAdmin(admin.ModelAdmin):
    """Admin configuration for Source model."""
    list_display = (
        "id",
        "notebook",
        "source_type",
        "title",
        "processing_status",
        "needs_processing",
        "created_at",
    )
    list_filter = ("source_type", "processing_status", "needs_processing", "created_at")
    search_fields = ("title", "notebook__name", "notebook__user__username")
    readonly_fields = ("created_at",)
    inlines = [URLProcessingResultInline, ProcessingJobInline]
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('notebook', 'notebook__user')


@admin.register(ProcessingJob)
class ProcessingJobAdmin(admin.ModelAdmin):
    """Admin configuration for ProcessingJob model."""
    list_display = ("id", "source", "job_type", "status", "created_at", "completed_at")
    list_filter = ("job_type", "status", "created_at")
    search_fields = ("source__title", "job_type")
    readonly_fields = ("created_at", "completed_at")
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('source', 'source__notebook')


@admin.register(KnowledgeBaseItem)
class KnowledgeBaseItemAdmin(admin.ModelAdmin):
    """Admin configuration for KnowledgeBaseItem model."""
    list_display = ("id", "user", "title", "content_type", "get_file_status", "created_at")
    list_filter = ("content_type", "created_at", "user")
    search_fields = ("title", "content", "user__username", "user__email")
    readonly_fields = ("created_at", "updated_at", "source_hash")
    fieldsets = (
        (None, {
            'fields': ('user', 'title', 'content_type')
        }),
        ('Content', {
            'fields': ('file', 'original_file', 'content', 'tags')
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
    
    def get_file_status(self, obj):
        """Get file status display."""
        status = []
        if obj.file:
            status.append("Processed")
        if obj.original_file:
            status.append("Original")
        if obj.content:
            status.append("Inline")
        return format_html(", ".join(status)) if status else "No files"
    get_file_status.short_description = "Files"
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('user')


@admin.register(KnowledgeItem)
class KnowledgeItemAdmin(admin.ModelAdmin):
    """Admin configuration for KnowledgeItem model."""
    list_display = ("id", "notebook", "get_kb_title", "source", "added_at")
    list_filter = ("notebook", "added_at", "source__source_type")
    search_fields = ("knowledge_base_item__title", "notebook__name", "notes")
    readonly_fields = ("added_at",)
    
    def get_kb_title(self, obj):
        """Get knowledge base item title."""
        return obj.knowledge_base_item.title
    get_kb_title.short_description = "Knowledge Base Item"
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            'notebook', 'knowledge_base_item', 'source', 'notebook__user'
        )


@admin.register(URLProcessingResult)
class URLProcessingResultAdmin(admin.ModelAdmin):
    """Admin configuration for URLProcessingResult model."""
    list_display = ("id", "source", "get_content_length", "has_file", "created_at")
    list_filter = ("created_at",)
    search_fields = ("source__title", "content_md")
    readonly_fields = ("created_at",)
    
    def get_content_length(self, obj):
        """Get content length."""
        return len(obj.content_md) if obj.content_md else 0
    get_content_length.short_description = "Content Length"
    
    def has_file(self, obj):
        """Check if has downloaded file."""
        return bool(obj.downloaded_file)
    has_file.boolean = True
    has_file.short_description = "Has File"
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('source')