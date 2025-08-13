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
    NotebookFileListStreamView,
    NotebookFileStatusStreamView,
    FileDeleteView,
    KnowledgeBaseView,
    FileContentView,
    FileContentMinIOView,
    FileRawView,
    FileRawSimpleView,
    FileImageView,
    KnowledgeBaseImagesView,
    RAGChatFromKBView,
    VideoImageExtractionView,
    BatchJobStatusView,
    ChatHistoryView,
    ClearChatHistoryView,
    SuggestedQuestionsView,
    URLParseDocumentView
)

# Import views from podcast and reports apps
from podcast import views as podcast_views
from reports import views as report_views

urlpatterns = [
    # Notebooks
    path("", NotebookListCreateAPIView.as_view(), name="notebook-list-create"),
    path(
        "<str:pk>/",
        NotebookRetrieveUpdateDestroyAPIView.as_view(),
        name="notebook-detail",
    ),
    # File endpoints for a given notebook
    # 1) list all processed files
    path("<uuid:notebook_id>/files/", FileListView.as_view(), name="file-list"),
    path(
        "<uuid:notebook_id>/chat-history/", ChatHistoryView.as_view(), name="chat-history"
    ),
    path(
        "<uuid:notebook_id>/chat-history/clear/",
        ClearChatHistoryView.as_view(),
        name="clear-chat-history",
    ),
    path(
        "<uuid:notebook_id>/suggested-questions/",
        SuggestedQuestionsView.as_view(),
        name="question-suggestions",
    ),
    path("<uuid:notebook_id>/chat/", RAGChatFromKBView.as_view(), name="chat-rag"),
    # 2) upload & parse a new file
    path(
        "<uuid:notebook_id>/files/upload/", FileUploadView.as_view(), name="file-upload"
    ),

    # NEW: URL parsing endpoints
    # 3) parse URL content without media
    path(
        '<uuid:notebook_id>/files/parse_url/',
        URLParseView.as_view(),
        name='url-parse'
    ),

    # 4) parse URL content with media extraction
    path(
        '<uuid:notebook_id>/files/parse_url_media/',
        URLParseWithMediaView.as_view(),
        name='url-parse-media'
    ),

    # 4.1) parse document URL with format validation
    path(
        '<uuid:notebook_id>/files/parse_document_url/',
        URLParseDocumentView.as_view(),
        name='url-parse-document'
    ),

    # 5) get one‐time status snapshot for an in‐flight upload
    path(
        "<uuid:notebook_id>/files/<str:upload_file_id>/status/",
        FileStatusView.as_view(),
        name="file-status",
    ),

    # 5.1) SSE streaming status updates for an in‐flight upload
    path(
        "<uuid:notebook_id>/files/<str:upload_file_id>/status/stream",
        FileStatusStreamView.as_view(),
        name="file-status-stream",
    ),
    
    # 5.2) SSE streaming for notebook file list updates
    path(
        "<uuid:notebook_id>/files/stream",
        NotebookFileListStreamView.as_view(),
        name="notebook-files-stream",
    ),
    
    # 5.3) SSE streaming for individual file processing status
    path(
        "<uuid:notebook_id>/files/<uuid:file_id>/status-stream/",
        NotebookFileStatusStreamView.as_view(),
        name="notebook-file-status-stream",
    ),

    # 6) delete either an in‐flight upload or a completed file
    path(
        "<uuid:notebook_id>/files/<str:file_or_upload_id>/",
        FileDeleteView.as_view(),
        name="file-delete",
    ),

    # 7) knowledge base management
    path(
        "<uuid:notebook_id>/knowledge-base/",
        KnowledgeBaseView.as_view(),
        name="knowledge-base",
    ),

    # 8) file content serving (parsed content)
    path(
        "files/<str:file_id>/content/", FileContentView.as_view(), name="file-content"
    ),

    # 8.1) file content serving with direct MinIO URLs
    path(
        "files/<str:file_id>/content/minio/", FileContentMinIOView.as_view(), name="file-content-minio"
    ),

    # 9) raw file serving (PDFs, videos, audio, etc.)
    path(
        "<uuid:notebook_id>/files/<str:file_id>/raw/",
        FileRawView.as_view(),
        name="file-raw",
    ),

    # 10) simplified raw file serving (without notebook context)
    path(
        "files/<str:file_id>/raw/", FileRawSimpleView.as_view(), name="file-raw-simple"
    ),

    # 11) image serving for knowledge base items
    path(
        "<uuid:notebook_id>/files/<str:file_id>/images/<str:image_file>",
        FileImageView.as_view(),
        name="file-image",
    ),

    # 11b) REST API endpoint for knowledge base images
    path(
        "<uuid:notebook_id>/files/<str:file_id>/images/",
        KnowledgeBaseImagesView.as_view(),
        name="knowledge-base-images",
    ),

    # 12) video image extraction endpoint
    path(
        "<uuid:notebook_id>/extraction/video_image_extraction/",
        VideoImageExtractionView.as_view(),
        name="video-image-extraction",
    ),

    # 12) batch job status endpoint
    path(
        "<uuid:notebook_id>/batch-jobs/<str:batch_job_id>/status/",
        BatchJobStatusView.as_view(),
        name="batch-job-status",
    ),

    # ===============================
    # PODCAST ENDPOINTS
    # ===============================
    path("<uuid:notebook_id>/podcast-jobs/", podcast_views.NotebookPodcastListCreateView.as_view(), name="notebook-podcast-jobs"),
    path("<uuid:notebook_id>/podcast-jobs/<str:job_id>/", podcast_views.NotebookPodcastDetailView.as_view(), name="notebook-podcast-job-detail"),
    path("<uuid:notebook_id>/podcast-jobs/<str:job_id>/cancel/", podcast_views.NotebookPodcastCancelView.as_view(), name="notebook-podcast-job-cancel"),
    path("<uuid:notebook_id>/podcast-jobs/<str:job_id>/audio/", podcast_views.NotebookPodcastAudioView.as_view(), name="notebook-podcast-job-audio"),
    path("<uuid:notebook_id>/podcast-jobs/<str:job_id>/download/", podcast_views.NotebookPodcastDownloadView.as_view(), name="notebook-podcast-job-download"),
    
    # Stream endpoint for podcast job status updates
    path(
        "<uuid:notebook_id>/podcast-jobs/<str:job_id>/stream/",
        csrf_exempt(podcast_views.notebook_job_status_stream),
        name="notebook-podcast-job-status-stream",
    ),

    # ===============================
    # REPORTS ENDPOINTS
    # ===============================
    path("<uuid:notebook_id>/report-jobs/", report_views.NotebookReportListCreateView.as_view(), name="notebook-reports"),
    path("<uuid:notebook_id>/report-jobs/<str:job_id>/", report_views.NotebookReportDetailView.as_view(), name="notebook-report-detail"),
    path("<uuid:notebook_id>/report-jobs/<str:job_id>/cancel/", report_views.NotebookReportCancelView.as_view(), name="notebook-report-cancel"),
    path("<uuid:notebook_id>/report-jobs/<str:job_id>/download/", report_views.NotebookReportDownloadView.as_view(), name="notebook-report-download"),
    path("<uuid:notebook_id>/report-jobs/<str:job_id>/download-pdf/", report_views.NotebookReportPdfDownloadView.as_view(), name="notebook-report-pdf-download"),
    path("<uuid:notebook_id>/report-jobs/<str:job_id>/files/", report_views.NotebookReportFilesView.as_view(), name="notebook-report-files"),
    path("<uuid:notebook_id>/report-jobs/<str:job_id>/content/", report_views.NotebookReportContentView.as_view(), name="notebook-report-content"),
    
    # Stream endpoint for report job status updates
    path(
        "<uuid:notebook_id>/report-jobs/<str:job_id>/stream/",
        csrf_exempt(report_views.notebook_report_status_stream),
        name="notebook-report-status-stream",
    ),

    # ===============================
    # CONFIGURATION ENDPOINTS
    # ===============================
    # Report models/configuration (not notebook-specific)
    path("reports/models/", report_views.ReportModelsView.as_view(), name="report-models"),
]