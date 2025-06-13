from django.contrib import admin
from .models import Notebook, UploadedPDF, NotebookSource

@admin.register(Notebook)
class NotebookAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'user', 'created_at')
    list_filter = ('user',)
    search_fields = ('name',)

@admin.register(UploadedPDF)
class UploadedPDFAdmin(admin.ModelAdmin):
    list_display = ('id', 'notebook', 'file_path', 'uploaded_at')
    list_filter = ('notebook',)
    search_fields = ('file_path',)

@admin.register(NotebookSource)
class NotebookSourceAdmin(admin.ModelAdmin):
    list_display = ('id', 'notebook', 'source_type', 'publication', 'event')
    list_filter = ('source_type',)
    raw_id_fields = ('publication', 'event')
