# notebooks/admin.py

from django.contrib import admin
from .models import Notebook, NotebookSource, UploadedFile, UrlLink


class NotebookSourceInline(admin.TabularInline):
    """
    Inline NotebookSource on the Notebook page.
    """
    model = NotebookSource
    fk_name = 'notebook'
    fields = (
        'source_type',
        'uploaded_file',
        'url_link',
        'raw_text',
        'created_at',
    )
    readonly_fields = ('created_at',)
    extra = 0
    autocomplete_fields = ('uploaded_file', 'url_link')


@admin.register(Notebook)
class NotebookAdmin(admin.ModelAdmin):
    """
    Notebook admin: lets you manage sources inline.
    """
    list_display    = ('id', 'name', 'user', 'created_at')
    list_filter     = ('user', 'created_at')
    search_fields   = ('name', 'user__username')
    readonly_fields = ('created_at',)
    inlines         = (NotebookSourceInline,)


@admin.register(NotebookSource)
class NotebookSourceAdmin(admin.ModelAdmin):
    """
    Standalone view of all NotebookSource entries.
    """
    list_display        = ('id', 'notebook', 'source_type', 'created_at')
    list_filter         = ('source_type', 'created_at')
    search_fields       = ('notebook__name',)
    readonly_fields     = ('created_at',)
    autocomplete_fields = ('uploaded_file', 'url_link')


@admin.register(UploadedFile)
class UploadedFileAdmin(admin.ModelAdmin):
    """
    Standalone admin for raw file uploads.
    """
    list_display    = ('id', 'file', 'file_size', 'content_type', 'created_at')
    list_filter     = ('created_at',)
    search_fields   = ('file',)
    readonly_fields = ('created_at',)


@admin.register(UrlLink)
class UrlLinkAdmin(admin.ModelAdmin):
    """
    Standalone admin for URL sources.
    """
    list_display    = ('id', 'source_title', 'url', 'created_at')
    list_filter     = ('created_at',)
    search_fields   = ('source_title', 'url')
    readonly_fields = ('created_at',)
