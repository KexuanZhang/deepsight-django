from django.contrib import admin
from .models import Report, ReportImage


@admin.register(Report)
class ReportAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "user",
        "article_title",
        "status",
        "model_provider",
        "retriever",
        "created_at",
        "updated_at",
    )
    list_filter = (
        "status",
        "model_provider",
        "retriever",
        "prompt_type",
        "created_at",
        "user",
    )
    search_fields = ("article_title", "topic", "user__username", "job_id")
    readonly_fields = (
        "id",
        "job_id",
        "created_at",
        "updated_at",
        "result_content",
        "generated_files",
        "processing_logs",
        "main_report_object_key",
    )
    raw_id_fields = ("user", "notebooks")

    fieldsets = (
        (
            "Basic Information",
            {
                "fields": (
                    "user",
                    "notebooks",
                    "article_title",
                    "topic",
                    "status",
                    "progress",
                )
            },
        ),
        (
            "Content Sources",
            {
                "fields": (
                    "selected_file_ids",
                    "selected_url_ids",
                    "csv_session_code",
                    "csv_date_filter",
                ),
                "classes": ("collapse",),
            },
        ),
        (
            "Model Configuration",
            {
                "fields": (
                    "model_provider",
                    "retriever",
                    "temperature",
                    "top_p",
                    "prompt_type",
                )
            },
        ),
        (
            "Generation Settings",
            {
                "fields": (
                    "do_research",
                    "do_generate_outline",
                    "do_generate_article",
                    "do_polish_article",
                    "remove_duplicate",
                    "post_processing",
                    "include_image",
                ),
                "classes": ("collapse",),
            },
        ),
        (
            "Advanced Parameters",
            {
                "fields": (
                    "max_conv_turn",
                    "max_perspective",
                    "search_top_k",
                    "initial_retrieval_k",
                    "final_context_k",
                    "reranker_threshold",
                    "max_thread_num",
                ),
                "classes": ("collapse",),
            },
        ),
        (
            "Search Configuration",
            {
                "fields": (
                    "time_range",
                    "include_domains",
                    "skip_rewrite_outline",
                    "domain_list",
                    "search_depth",
                ),
                "classes": ("collapse",),
            },
        ),
        (
            "Results",
            {
                "fields": (
                    "result_content",
                    "main_report_object_key",
                    "generated_files",
                    "processing_logs",
                    "error_message",
                ),
                "classes": ("collapse",),
            },
        ),
        (
            "System Information",
            {
                "fields": ("job_id", "created_at", "updated_at"),
                "classes": ("collapse",),
            },
        ),
    )

    def get_queryset(self, request):
        """Optimize queryset with select_related."""
        return super().get_queryset(request).select_related("user", "notebooks")

    def has_change_permission(self, request, obj=None):
        """Allow changes only to non-running reports."""
        if obj and obj.status == Report.STATUS_RUNNING:
            return False
        return super().has_change_permission(request, obj)

    def has_delete_permission(self, request, obj=None):
        """Allow deletion only of non-running reports."""
        if obj and obj.status == Report.STATUS_RUNNING:
            return False
        return super().has_delete_permission(request, obj)


class ReportImageInline(admin.TabularInline):
    """Inline admin for ReportImage to show images within Report admin."""
    model = ReportImage
    extra = 0
    readonly_fields = (
        'figure_id', 
        'image_caption', 
        'report_figure_minio_object_key',
        'content_type',
        'file_size',
        'created_at'
    )
    can_delete = False
    
    def has_add_permission(self, request, obj=None):
        return False


# Update ReportAdmin to include the inline
ReportAdmin.inlines = [ReportImageInline]


@admin.register(ReportImage)
class ReportImageAdmin(admin.ModelAdmin):
    list_display = (
        'figure_id',
        'report',
        'image_caption_truncated',
        'content_type',
        'file_size',
        'created_at'
    )
    list_filter = (
        'content_type',
        'created_at',
        'report__user'
    )
    search_fields = (
        'figure_id',
        'image_caption',
        'report__article_title',
        'report_figure_minio_object_key'
    )
    readonly_fields = (
        'figure_id',
        'report_figure_minio_object_key',
        'image_metadata',
        'created_at',
        'updated_at',
        'get_image_preview'
    )
    raw_id_fields = ('report',)
    
    def image_caption_truncated(self, obj):
        """Truncate long captions for list display."""
        return obj.image_caption[:50] + '...' if len(obj.image_caption) > 50 else obj.image_caption
    image_caption_truncated.short_description = 'Caption'
    
    def get_image_preview(self, obj):
        """Display image preview in admin."""
        if obj.report_figure_minio_object_key:
            url = obj.get_image_url(expires=3600)
            if url:
                from django.utils.html import format_html
                return format_html(
                    '<img src="{}" style="max-width: 300px; max-height: 300px;" />',
                    url
                )
        return "No image available"
    get_image_preview.short_description = 'Image Preview'
    
    def has_add_permission(self, request):
        """Prevent manual addition of report images."""
        return False
    
    def has_change_permission(self, request, obj=None):
        """Prevent editing of report images."""
        return False
