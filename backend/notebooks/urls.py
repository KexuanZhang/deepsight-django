# notebooks/urls.py

from django.urls import path, include
from django.views.decorators.csrf import csrf_exempt

# Import views from podcast and reports apps
from podcast import views as podcast_views
from reports import views as report_views

urlpatterns = [
    # API v1 - Primary API endpoints (new structure)
    path("", include("notebooks.api.v1.urls")),

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