from django.contrib import admin
from .models import Notebook, UploadedFile, NotebookSource

@admin.register(Notebook)
class NotebookAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'user', 'created_at')
    list_filter = ('user', 'created_at')
    search_fields = ('name', 'user__username')
    ordering = ('-created_at',)

@admin.register(UploadedFile)
class UploadedFileAdmin(admin.ModelAdmin):
    list_display = (
        'upload_file_id',
        'original_filename',
        'notebook',
        'status',
        'parsing_status',
        'created_at',
    )
    list_filter = ('status', 'parsing_status', 'created_at')
    search_fields = ('original_filename', 'upload_file_id', 'notebook__name')
    readonly_fields = (
        'upload_file_id',
        'original_filename',
        'file_extension',
        'content_type',
        'file_size',
        'validation_result',
        'processing_result',
        'created_at',
        'updated_at',
    )
    raw_id_fields = ('notebook',)

@admin.register(NotebookSource)
class NotebookSourceAdmin(admin.ModelAdmin):
    list_display = ('source_id', 'notebook', 'source_type')
    list_filter = ('source_type', 'notebook__user')
    search_fields = (
        'notebook__name',
    )
    raw_id_fields = ('notebook',)
