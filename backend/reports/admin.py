from django.contrib import admin
from .models import Report


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
