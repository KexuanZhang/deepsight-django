from django.contrib import admin
from django.utils.html import format_html
from .models import (
    Notebook,
    KnowledgeBaseItem,
    NotebookChatMessage,
    RagFlowDataset,
)



class KnowledgeBaseItemInline(admin.TabularInline):
    """Inline admin for knowledge base items."""

    model = KnowledgeBaseItem
    readonly_fields = ("created_at", "parsing_status")
    fields = ("title", "content_type", "parsing_status", "notes", "created_at")
    extra = 0
    show_change_link = True


@admin.register(Notebook)
class NotebookAdmin(admin.ModelAdmin):
    """Admin configuration for Notebook model."""

    list_display = ("id", "user", "name", "get_item_count", "created_at")
    search_fields = ("name", "user__username", "user__email")
    list_filter = ("created_at", "user")
    readonly_fields = ("created_at",)
    inlines = [KnowledgeBaseItemInline]

    def get_item_count(self, obj):
        """Get count of knowledge base items in notebook."""
        return obj.knowledge_base_items.count()

    get_item_count.short_description = "Knowledge Items"

    def get_queryset(self, request):
        return (
            super()
            .get_queryset(request)
            .select_related("user")
            .prefetch_related("knowledge_base_items")
        )




@admin.register(KnowledgeBaseItem)
class KnowledgeBaseItemAdmin(admin.ModelAdmin):
    """Admin configuration for KnowledgeBaseItem model."""

    list_display = (
        "id",
        "notebook",
        "title",
        "content_type",
        "parsing_status",
        "get_file_status",
        "created_at",
    )
    list_filter = ("content_type", "parsing_status", "created_at", "notebook__user")
    search_fields = ("title", "content", "notebook__name", "notebook__user__username")
    readonly_fields = ("created_at", "updated_at", "source_hash")
    fieldsets = (
        (None, {"fields": ("notebook", "title", "content_type", "parsing_status", "notes")}),
        ("Content", {"fields": ("file_object_key", "original_file_object_key", "content", "tags")}),
        ("Metadata", {"fields": ("metadata", "source_hash"), "classes": ("collapse",)}),
        (
            "Timestamps",
            {"fields": ("created_at", "updated_at"), "classes": ("collapse",)},
        ),
    )

    def get_file_status(self, obj):
        """Get file status display."""
        status = []
        if obj.file_object_key:
            status.append("Processed")
        if obj.original_file_object_key:
            status.append("Original")
        if obj.content:
            status.append("Inline")
        return format_html(", ".join(status)) if status else "No files"

    get_file_status.short_description = "Files"

    def get_queryset(self, request):
        return super().get_queryset(request).select_related("notebook", "notebook__user")


@admin.register(RagFlowDataset)
class RagFlowDatasetAdmin(admin.ModelAdmin):
    """Admin configuration for RagFlowDataset model."""
    
    list_display = (
        "id", 
        "notebook", 
        "dataset_name", 
        "status", 
        "get_document_count",
        "created_at"
    )
    list_filter = ("status", "created_at")
    search_fields = ("dataset_name", "notebook__name", "notebook__user__username")
    readonly_fields = ("created_at", "updated_at", "ragflow_dataset_id", "ragflow_chat_id")
    fieldsets = (
        (None, {"fields": ("notebook", "dataset_name", "status")}),
        ("RagFlow Integration", {"fields": ("ragflow_dataset_id", "ragflow_chat_id")}),
        ("Status", {"fields": ("error_message",)}),
        ("Metadata", {"fields": ("metadata",), "classes": ("collapse",)}),
        ("Timestamps", {"fields": ("created_at", "updated_at"), "classes": ("collapse",)}),
    )
    
    def get_document_count(self, obj):
        """Get count of documents in the dataset."""
        return obj.get_document_count()
    
    get_document_count.short_description = "Documents"
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related("notebook", "notebook__user")


@admin.register(NotebookChatMessage)
class NotebookChatMessageAdmin(admin.ModelAdmin):
    list_display = ("notebook", "sender", "short_message", "timestamp")
    list_filter = ("notebook", "sender", "timestamp")
    search_fields = ("message",)

    def short_message(self, obj):
        return (obj.message[:75] + "...") if len(obj.message) > 75 else obj.message
    short_message.short_description = "Message"