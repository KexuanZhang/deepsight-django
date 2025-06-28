# notebooks/urls.py

from django.urls import path, include
from django.views.decorators.csrf import csrf_exempt
from .views import (
    NotebookListCreateAPIView,
    NotebookRetrieveUpdateDestroyAPIView,
    FileListView,
    FileUploadView,
    URLParseView,
    URLParseWithMediaView,
    FileStatusView,
    FileStatusStreamView,
    FileDeleteView,
    KnowledgeBaseView,
    FileContentView,
    FileRawView,
    FileRawSimpleView,
    FileImageView,
    MarkdownBatchContentView,
    RAGChatFromKBView,
    VideoImageExtractionView,
    BatchJobStatusView,
)

# Import views from podcast and reports apps
from podcast import views as podcast_views
from reports import views as report_views

urlpatterns = [
    # Notebooks
    path("", NotebookListCreateAPIView.as_view(), name="notebook-list-create"),
    path(
        "<int:pk>/",
        NotebookRetrieveUpdateDestroyAPIView.as_view(),
        name="notebook-detail",
    ),
    # File endpoints for a given notebook
    # 1) list all processed files
    path("<int:notebook_id>/files/", FileListView.as_view(), name="file-list"),
    path(
        "<int:notebook_id>/files/md-batch-contents/",
        MarkdownBatchContentView.as_view(),
        name="file-md-batch-contents",
    ),
    path("chat/", RAGChatFromKBView.as_view(), name="chat-rag"),
    # 2) upload & parse a new file
    path(
        "<int:notebook_id>/files/upload/", FileUploadView.as_view(), name="file-upload"
    ),

    # NEW: URL parsing endpoints
    # 3) parse URL content without media
    path(
        '<int:notebook_id>/files/parse_url/',
        URLParseView.as_view(),
        name='url-parse'
    ),

    # 4) parse URL content with media extraction
    path(
        '<int:notebook_id>/files/parse_url_media/',
        URLParseWithMediaView.as_view(),
        name='url-parse-media'
    ),

    # 5) get one‐time status snapshot for an in‐flight upload
    path(
        "<int:notebook_id>/files/<str:upload_file_id>/status/",
        FileStatusView.as_view(),
        name="file-status",
    ),

    # 5.1) SSE streaming status updates for an in‐flight upload
    path(
        "<int:notebook_id>/files/<str:upload_file_id>/status/stream",
        FileStatusStreamView.as_view(),
        name="file-status-stream",
    ),

    # 6) delete either an in‐flight upload or a completed file
    path(
        "<int:notebook_id>/files/<str:file_or_upload_id>/",
        FileDeleteView.as_view(),
        name="file-delete",
    ),

    # 7) knowledge base management
    path(
        "<int:notebook_id>/knowledge-base/",
        KnowledgeBaseView.as_view(),
        name="knowledge-base",
    ),

    # 8) file content serving (parsed content)
    path(
        "files/<str:file_id>/content/", FileContentView.as_view(), name="file-content"
    ),

    # 9) raw file serving (PDFs, videos, audio, etc.)
    path(
        "<int:notebook_id>/files/<str:file_id>/raw/",
        FileRawView.as_view(),
        name="file-raw",
    ),

    # 10) simplified raw file serving (without notebook context)
    path(
        "files/<str:file_id>/raw/", FileRawSimpleView.as_view(), name="file-raw-simple"
    ),

    # 11) image serving for knowledge base items
    path(
        "<int:notebook_id>/files/<str:file_id>/images/<str:image_name>",
        FileImageView.as_view(),
        name="file-image",
    ),

    # 12) video image extraction endpoint
    path(
        "<int:notebook_id>/extraction/video_image_extraction/",
        VideoImageExtractionView.as_view(),
        name="video-image-extraction",
    ),

    # 12) batch job status endpoint
    path(
        "<int:notebook_id>/batch-jobs/<int:batch_job_id>/status/",
        BatchJobStatusView.as_view(),
        name="batch-job-status",
    ),

    # ===============================
    # PODCAST ENDPOINTS
    # ===============================
    path("<int:notebook_id>/podcast-jobs/", podcast_views.NotebookPodcastJobListCreateView.as_view(), name="notebook-podcast-jobs"),
    path("<int:notebook_id>/podcast-jobs/<str:job_id>/", podcast_views.NotebookPodcastJobDetailView.as_view(), name="notebook-podcast-job-detail"),
    path("<int:notebook_id>/podcast-jobs/<str:job_id>/cancel/", podcast_views.NotebookPodcastJobCancelView.as_view(), name="notebook-podcast-job-cancel"),
    path("<int:notebook_id>/podcast-jobs/<str:job_id>/audio/", podcast_views.NotebookPodcastJobAudioView.as_view(), name="notebook-podcast-job-audio"),
    
    # Stream endpoint for podcast job status updates
    path(
        "<int:notebook_id>/podcast-jobs/<str:job_id>/stream/",
        csrf_exempt(podcast_views.notebook_job_status_stream),
        name="notebook-podcast-job-status-stream",
    ),

    # ===============================
    # REPORTS ENDPOINTS
    # ===============================
    path("<int:notebook_id>/report-jobs/", report_views.NotebookReportListCreateView.as_view(), name="notebook-reports"),
    path("<int:notebook_id>/report-jobs/<str:job_id>/", report_views.NotebookReportDetailView.as_view(), name="notebook-report-detail"),
    path("<int:notebook_id>/report-jobs/<str:job_id>/cancel/", report_views.NotebookReportCancelView.as_view(), name="notebook-report-cancel"),
    path("<int:notebook_id>/report-jobs/<str:job_id>/download/", report_views.NotebookReportDownloadView.as_view(), name="notebook-report-download"),
    path("<int:notebook_id>/report-jobs/<str:job_id>/files/", report_views.NotebookReportFilesView.as_view(), name="notebook-report-files"),
    path("<int:notebook_id>/report-jobs/<str:job_id>/content/", report_views.NotebookReportContentView.as_view(), name="notebook-report-content"),
    
    # Stream endpoint for report job status updates
    path(
        "<int:notebook_id>/report-jobs/<str:job_id>/stream/",
        csrf_exempt(report_views.notebook_report_status_stream),
        name="notebook-report-status-stream",
    ),

    # ===============================
    # CONFIGURATION ENDPOINTS
    # ===============================
    # Report models/configuration (not notebook-specific)
    path("reports/models/", report_views.ReportModelsView.as_view(), name="report-models"),
]
