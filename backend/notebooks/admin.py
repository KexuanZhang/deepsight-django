from django.contrib import admin
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


class UploadedFileInline(admin.StackedInline):
    model = UploadedFile
    readonly_fields = ("content_type", "original_name", "uploaded_at")
    extra = 0


class PastedTextFileInline(admin.StackedInline):
    model = PastedTextFile
    readonly_fields = ("created_at",)
    extra = 0


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
        UploadedFileInline,
        PastedTextFileInline,
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
    inlines = [UploadedFileInline, PastedTextFileInline, URLProcessingResultInline, ProcessingJobInline]


@admin.register(ProcessingJob)
class ProcessingJobAdmin(admin.ModelAdmin):
    list_display = ("id", "source", "job_type", "status", "created_at", "completed_at")
    list_filter = ("job_type", "status")
    search_fields = ("source__title",)
    readonly_fields = ("created_at", "completed_at")


@admin.register(KnowledgeItem)
class KnowledgeItemAdmin(admin.ModelAdmin):
    list_display = ("id", "notebook", "source", "created_at")
    list_filter = ("notebook",)
    search_fields = ("content",)
    readonly_fields = ("created_at",)


# Register remaining models in default fashion
admin.site.register(UploadedFile)
admin.site.register(PastedTextFile)
admin.site.register(URLProcessingResult)
# admin.site.register(SearchResult)
