from django.contrib import admin
from .models import Report

@admin.register(Report)
class ReportAdmin(admin.ModelAdmin):
    list_display = (
        'id',           # was 'report_id'
        'user',
        'notebook',
        'article_title',
        'status',
        'created_at',
        'updated_at',
    )
    list_filter = ('status', 'user')
    search_fields = ('article_title', 'result_content')
    raw_id_fields = ('user', 'notebook')
