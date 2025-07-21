# reports/models.py
import uuid
from django.db import models
from django.conf import settings
from django.db.models.signals import pre_delete
from django.dispatch import receiver


class Report(models.Model):
    # Associations
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="reports"
    )
    # Optional linking to a notebook (if relevant)
    notebooks = models.ForeignKey(
        "notebooks.Notebook",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="reports",
    )

    # Core input parameters
    topic = models.CharField(max_length=500, blank=True, help_text="Research topic")
    article_title = models.CharField(max_length=255, default="Research Report")
    old_outline = models.TextField(
        blank=True, help_text="User-provided outline content to use as starting point"
    )

    # Content inputs from knowledge base
    selected_files_paths = models.JSONField(
        default=list,
        blank=True,
        help_text="List of file folder paths from knowledge base",
    )

    # CSV processing options
    csv_session_code = models.CharField(max_length=100, blank=True)
    csv_date_filter = models.CharField(max_length=20, blank=True)

    # Model and retriever configuration
    MODEL_PROVIDER_OPENAI = "openai"
    MODEL_PROVIDER_GOOGLE = "google"
    MODEL_PROVIDER_CHOICES = [
        (MODEL_PROVIDER_OPENAI, "OpenAI"),
        (MODEL_PROVIDER_GOOGLE, "Google"),
    ]
    model_provider = models.CharField(
        max_length=50, choices=MODEL_PROVIDER_CHOICES, default=MODEL_PROVIDER_OPENAI
    )

    RETRIEVER_TAVILY = "tavily"
    RETRIEVER_BRAVE = "brave"
    RETRIEVER_SERPER = "serper"
    RETRIEVER_YOU = "you"
    RETRIEVER_BING = "bing"
    RETRIEVER_DUCKDUCKGO = "duckduckgo"
    RETRIEVER_SEARXNG = "searxng"
    RETRIEVER_AZURE_AI_SEARCH = "azure_ai_search"
    RETRIEVER_CHOICES = [
        (RETRIEVER_TAVILY, "Tavily"),
        (RETRIEVER_BRAVE, "Brave"),
        (RETRIEVER_SERPER, "Serper"),
        (RETRIEVER_YOU, "You"),
        (RETRIEVER_BING, "Bing"),
        (RETRIEVER_DUCKDUCKGO, "DuckDuckGo"),
        (RETRIEVER_SEARXNG, "SearXNG"),
        (RETRIEVER_AZURE_AI_SEARCH, "Azure AI Search"),
    ]
    retriever = models.CharField(
        max_length=50, choices=RETRIEVER_CHOICES, default=RETRIEVER_TAVILY
    )

    # Generation parameters
    temperature = models.FloatField(
        default=0.2, help_text="Temperature for LLM generation (0.0-2.0)"
    )
    top_p = models.FloatField(
        default=0.4, help_text="Top-p for LLM generation (0.0-1.0)"
    )

    PROMPT_TYPE_GENERAL = "general"
    PROMPT_TYPE_FINANCIAL = "financial"
    PROMPT_TYPE_PAPER = "paper"
    PROMPT_TYPE_CHOICES = [
        (PROMPT_TYPE_GENERAL, "General"),
        (PROMPT_TYPE_FINANCIAL, "Financial"),
        (PROMPT_TYPE_PAPER, "Paper"),
    ]
    prompt_type = models.CharField(
        max_length=50, choices=PROMPT_TYPE_CHOICES, default=PROMPT_TYPE_GENERAL
    )

    # Generation flags
    do_research = models.BooleanField(default=True)
    do_generate_outline = models.BooleanField(default=True)
    do_generate_article = models.BooleanField(default=True)
    do_polish_article = models.BooleanField(default=True)
    remove_duplicate = models.BooleanField(default=True)
    post_processing = models.BooleanField(default=True)

    # Search and generation parameters
    max_conv_turn = models.PositiveIntegerField(
        default=3, help_text="Maximum conversation turns (1-10)"
    )
    max_perspective = models.PositiveIntegerField(
        default=3, help_text="Maximum perspectives (1-10)"
    )
    search_top_k = models.PositiveIntegerField(
        default=10, help_text="Top K search results (5-50)"
    )
    initial_retrieval_k = models.PositiveIntegerField(
        default=150, help_text="Initial retrieval K (50-500)"
    )
    final_context_k = models.PositiveIntegerField(
        default=20, help_text="Final context K (10-100)"
    )
    reranker_threshold = models.FloatField(
        default=0.5, help_text="Reranker threshold (0.0-1.0)"
    )
    max_thread_num = models.PositiveIntegerField(
        default=10, help_text="Maximum threads (1-20)"
    )

    # Optional parameters
    TIME_RANGE_ALL = "ALL"
    TIME_RANGE_DAY = "day"
    TIME_RANGE_WEEK = "week"
    TIME_RANGE_MONTH = "month"
    TIME_RANGE_YEAR = "year"
    TIME_RANGE_CHOICES = [
        (TIME_RANGE_ALL, "All Time"),
        (TIME_RANGE_DAY, "Day"),
        (TIME_RANGE_WEEK, "Week"),
        (TIME_RANGE_MONTH, "Month"),
        (TIME_RANGE_YEAR, "Year"),
    ]
    time_range = models.CharField(
        max_length=20, choices=TIME_RANGE_CHOICES, blank=True, null=True
    )

    include_domains = models.BooleanField(default=False)
    skip_rewrite_outline = models.BooleanField(default=False)
    domain_list = models.JSONField(
        default=list, blank=True, help_text="Whitelist domains"
    )

    # New flag to control inclusion of figure data/image in report generation
    include_image = models.BooleanField(
        default=True,
        help_text="Whether to include figure data (images) during report generation",
    )

    SEARCH_DEPTH_BASIC = "basic"
    SEARCH_DEPTH_ADVANCED = "advanced"
    SEARCH_DEPTH_CHOICES = [
        (SEARCH_DEPTH_BASIC, "Basic"),
        (SEARCH_DEPTH_ADVANCED, "Advanced"),
    ]
    search_depth = models.CharField(
        max_length=20, choices=SEARCH_DEPTH_CHOICES, default=SEARCH_DEPTH_BASIC
    )

    # Status tracking
    STATUS_PENDING = "pending"
    STATUS_RUNNING = "running"
    STATUS_COMPLETED = "completed"
    STATUS_FAILED = "failed"
    STATUS_CANCELLED = "cancelled"
    STATUS_CHOICES = [
        (STATUS_PENDING, "Pending"),
        (STATUS_RUNNING, "Running"),
        (STATUS_COMPLETED, "Completed"),
        (STATUS_FAILED, "Failed"),
        (STATUS_CANCELLED, "Cancelled"),
    ]
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default=STATUS_PENDING
    )

    progress = models.CharField(
        max_length=500, blank=True, help_text="Current progress message"
    )

    # Results and files
    result_content = models.TextField(blank=True, help_text="Generated report content")
    error_message = models.TextField(blank=True)

    # MinIO-native storage (replaces Django FileField)
    main_report_object_key = models.CharField(
        max_length=255, 
        blank=True, 
        null=True, 
        db_index=True,
        help_text="MinIO object key for main report file"
    )
    
    # All file metadata stored in JSON (replaces multiple file fields)
    file_metadata = models.JSONField(
        default=dict, 
        help_text="All file paths, names, sizes, etc."
    )
    
    generated_files = models.JSONField(
        default=list, blank=True, help_text="List of generated file object keys"
    )
    processing_logs = models.JSONField(
        default=list, blank=True, help_text="Processing log messages"
    )

    # Celery task tracking (optional – used for cancellation of background task)
    celery_task_id = models.CharField(max_length=255, null=True, blank=True)
    

    # Job management
    job_id = models.CharField(
        max_length=100,
        unique=True,
        blank=True,
        help_text="Background job ID for tracking",
    )

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["user", "status"]),
            models.Index(fields=["job_id"]),
            # MinIO-specific indexes
            models.Index(fields=["main_report_object_key"]),
        ]

    def __str__(self):
        return f"Report: {self.article_title} ({self.status})"
    
    def get_report_url(self, expires=86400):
        """Get pre-signed URL for report access"""
        if self.main_report_object_key:
            try:
                from notebooks.utils.storage import get_minio_backend
                backend = get_minio_backend()
                return backend.get_presigned_url(self.main_report_object_key, expires)
            except Exception:
                return None
        return None
    
    def get_figure_data_url(self, expires=86400):
        """Get pre-signed URL for figure data access"""
        if self.figure_data_object_key:
            try:
                from notebooks.utils.storage import get_minio_backend
                backend = get_minio_backend()
                return backend.get_presigned_url(self.figure_data_object_key, expires)
            except Exception:
                return None
        return None

    def get_configuration_dict(self):
        """Return configuration as a dictionary for passing to the report generator."""
        return {
            "model_provider": self.model_provider,
            "retriever": self.retriever,
            "temperature": self.temperature,
            "top_p": self.top_p,
            "prompt_type": self.prompt_type,
            "do_research": self.do_research,
            "do_generate_outline": self.do_generate_outline,
            "do_generate_article": self.do_generate_article,
            "do_polish_article": self.do_polish_article,
            "remove_duplicate": self.remove_duplicate,
            "post_processing": self.post_processing,
            "max_conv_turn": self.max_conv_turn,
            "max_perspective": self.max_perspective,
            "search_top_k": self.search_top_k,
            "initial_retrieval_k": self.initial_retrieval_k,
            "final_context_k": self.final_context_k,
            "reranker_threshold": self.reranker_threshold,
            "max_thread_num": self.max_thread_num,
            "time_range": self.time_range,
            "include_domains": self.include_domains,
            "skip_rewrite_outline": self.skip_rewrite_outline,
            "domain_list": self.domain_list,
            "include_image": self.include_image,
            "search_depth": self.search_depth,
            # Content input fields
            "topic": self.topic,
            "selected_files_paths": self.selected_files_paths,
        }

    def update_status(self, status, progress=None, error=None):
        """Update the status of this report."""
        self.status = status
        if progress is not None:
            self.progress = progress
        if error is not None:
            self.error_message = error
        self.save(update_fields=["status", "progress", "error_message", "updated_at"])


class ReportImage(models.Model):
    """
    Store image metadata for report items, similar to KnowledgeBaseImage but for reports.
    Each image is linked to a report and stored in the report's MinIO folder.
    """
    
    # Use standard auto-generated id as primary key to match database
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Separate figure_id field (not primary key)
    figure_id = models.UUIDField(default=uuid.uuid4, editable=False, help_text="Unique figure identifier from knowledge base")
    
    # Link to report instead of knowledge_base_item
    report = models.ForeignKey(
        Report,
        on_delete=models.CASCADE,
        related_name="images",
        help_text="Report this image belongs to"
    )
    
    # Image identification and metadata (copied from KnowledgeBaseImage)
    image_caption = models.TextField(
        blank=True,
        help_text="Description or caption for the image"
    )
    
    # MinIO storage fields - use correct field name from database
    report_figure_minio_object_key = models.CharField(
        max_length=255,
        db_index=True,
        help_text="MinIO object key for the image file in report folder"
    )
    
    # Image metadata and properties
    image_metadata = models.JSONField(
        default=dict,
        help_text="Image metadata including dimensions, format, size, etc."
    )
    content_type = models.CharField(
        max_length=100,
        blank=True,
        help_text="MIME type of the image (image/png, image/jpeg, etc.)"
    )
    file_size = models.PositiveIntegerField(
        default=0,
        help_text="File size in bytes"
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ["report", "created_at"]
        verbose_name = "Report Image"
        verbose_name_plural = "Report Images"
        indexes = [
            models.Index(fields=["report", "created_at"]),
            models.Index(fields=["report_figure_minio_object_key"]),
        ]
    
    def __str__(self):
        return f"Image {self.figure_id} for Report {self.report.article_title}"
    
    def get_image_url(self, expires=86400):
        """Get pre-signed URL for image access"""
        if self.report_figure_minio_object_key:
            try:
                from notebooks.utils.storage import get_minio_backend
                backend = get_minio_backend()
                return backend.get_presigned_url(self.report_figure_minio_object_key, expires)
            except Exception:
                return None
        return None
    
    def get_image_content(self):
        """Get image content as bytes from MinIO"""
        if self.report_figure_minio_object_key:
            try:
                from notebooks.utils.storage import get_minio_backend
                backend = get_minio_backend()
                return backend.get_file_content(self.report_figure_minio_object_key)
            except Exception:
                return None
        return None


# Signal handlers
@receiver(pre_delete, sender=Report)
def cleanup_report_images(sender, instance, **kwargs):
    """Clean up associated images when a report is deleted"""
    try:
        from reports.core.report_image_service import ReportImageService
        image_service = ReportImageService()
        image_service.cleanup_report_images(instance)
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Error cleaning up images for report {instance.id}: {e}")
