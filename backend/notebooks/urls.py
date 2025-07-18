"""
URL patterns for notebooks app - organized by view categories
"""
from django.urls import path, include
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from .views import (
    # Notebook views
    NotebookListCreateAPIView,
    NotebookRetrieveUpdateDestroyAPIView,
    
    # File views
    FileUploadView,
    FileListView,
    FileStatusView,
    FileStatusStreamView,
    FileDeleteView,
    FileContentView,
    FileContentMinIOView,
    FileRawView,
    FileRawSimpleView,
    VideoImageExtractionView,
    FileImageView,
    
    # URL views
    URLParseView,
    URLParseWithMediaView,
    URLParseDocumentView,
    SimpleTestView,
    
    # Chat views
    RAGChatFromKBView,
    ChatHistoryView,
    ClearChatHistoryView,
    SuggestedQuestionsView,
    
    # Knowledge base views
    KnowledgeBaseView,
    KnowledgeBaseImagesView,
    
    # Batch job views
    BatchJobStatusView,
)

# Import views from podcast and reports apps
from podcast import views as podcast_views
from reports import views as report_views


def health_check(request):
    """Simple health check endpoint"""
    return JsonResponse({"status": "ok", "app": "notebooks"})


@csrf_exempt
@require_http_methods(["GET", "POST"])
def test_function_view(request, notebook_id):
    """Simple function-based view to test basic routing"""
    return JsonResponse({
        "message": f"Function view works with {request.method}",
        "notebook_id": notebook_id,
        "view_type": "function-based"
    })


urlpatterns = [
    # Health check
    path("health/", health_check, name="health"),
    
    # Notebook CRUD endpoints
    path("", NotebookListCreateAPIView.as_view(), name="notebook-list-create"),
    path("<str:pk>/", NotebookRetrieveUpdateDestroyAPIView.as_view(), name="notebook-detail"),
    
    # File management endpoints  
    path("<str:notebook_id>/files/", FileListView.as_view(), name="file-list"),
    path("<str:notebook_id>/files/upload/", FileUploadView.as_view(), name="file-upload"),
    
    # URL processing endpoints (MUST come before general file patterns)
    path("<str:notebook_id>/files/parse_url/", URLParseView.as_view(), name="url-parse"),
    path("<str:notebook_id>/files/parse_url_media/", URLParseWithMediaView.as_view(), name="url-parse-media"),
    path("<str:notebook_id>/files/parse_document_url/", URLParseDocumentView.as_view(), name="url-parse-document"),
    
    # File status and operations (specific patterns first)
    path("<str:notebook_id>/files/<str:upload_file_id>/status/", FileStatusView.as_view(), name="file-status"),
    path("<str:notebook_id>/files/<str:upload_file_id>/status/stream", FileStatusStreamView.as_view(), name="file-status-stream"),
    path("<str:notebook_id>/files/<str:file_id>/content/", FileContentView.as_view(), name="file-content"),
    path("<str:notebook_id>/files/<str:file_id>/content/minio/", FileContentMinIOView.as_view(), name="file-content-minio"),
    path("<str:notebook_id>/files/<str:file_id>/raw/", FileRawView.as_view(), name="file-raw"),
    path("<str:notebook_id>/files/<str:file_id>/images/<str:figure_id>", FileImageView.as_view(), name="file-image"),
    
    # General file pattern (MUST come last to avoid conflicts)
    path("<str:notebook_id>/files/<str:file_or_upload_id>/", FileDeleteView.as_view(), name="file-delete"),
    
    # Global file endpoints
    path("files/<str:file_id>/content/", FileContentView.as_view(), name="file-content-global"),
    path("files/<str:file_id>/content/minio/", FileContentMinIOView.as_view(), name="file-content-minio-global"),
    path("files/<str:file_id>/raw/", FileRawSimpleView.as_view(), name="file-raw-simple"),
    path("<str:notebook_id>/extraction/video_image_extraction/", VideoImageExtractionView.as_view(), name="video-image-extraction"),
    
    # Test endpoints
    path("<str:notebook_id>/test-url-parse/", URLParseView.as_view(), name="test-url-parse"),
    path("<str:notebook_id>/simple-test/", SimpleTestView.as_view(), name="simple-test"),
    path("<str:notebook_id>/function-test/", test_function_view, name="function-test"),
    
    # Chat endpoints
    path("<str:notebook_id>/chat/", RAGChatFromKBView.as_view(), name="rag-chat"),
    path("<str:notebook_id>/chat-history/", ChatHistoryView.as_view(), name="chat-history"),
    path("<str:notebook_id>/chat-history/clear/", ClearChatHistoryView.as_view(), name="clear-chat-history"), 
    path("<str:notebook_id>/suggested-questions/", SuggestedQuestionsView.as_view(), name="suggested-questions"),
    
    # Knowledge base endpoints
    path("<str:notebook_id>/knowledge-base/", KnowledgeBaseView.as_view(), name="knowledge-base"),
    path("<str:notebook_id>/files/<str:file_id>/images/", KnowledgeBaseImagesView.as_view(), name="knowledge-base-images"),
    
    # Batch job endpoints
    path("<str:notebook_id>/batch-jobs/<str:batch_job_id>/status/", BatchJobStatusView.as_view(), name="batch-job-status"),
    
    # ===============================
    # PODCAST ENDPOINTS
    # ===============================
    path("<str:notebook_id>/podcast-jobs/", podcast_views.NotebookPodcastJobListCreateView.as_view(), name="notebook-podcast-jobs"),
    path("<str:notebook_id>/podcast-jobs/<str:job_id>/", podcast_views.NotebookPodcastJobDetailView.as_view(), name="notebook-podcast-job-detail"),
    
    # ===============================
    # REPORTS ENDPOINTS  
    # ===============================
    path("<str:notebook_id>/report-jobs/", report_views.NotebookReportListCreateView.as_view(), name="notebook-reports"),
    path("<str:notebook_id>/report-jobs/<str:job_id>/", report_views.NotebookReportDetailView.as_view(), name="notebook-report-detail"),
    
    # ===============================
    # CONFIGURATION ENDPOINTS
    # ===============================
    # Report models/configuration (not notebook-specific)
    path("reports/models/", report_views.ReportModelsView.as_view(), name="report-models"),
] 