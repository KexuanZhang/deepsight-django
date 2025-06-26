from django.urls import path
from django.views.decorators.csrf import csrf_exempt
from . import views

urlpatterns = [
    # Notebook-specific podcast endpoints
    path("notebooks/<int:notebook_id>/podcast-jobs/", views.NotebookPodcastJobListCreateView.as_view(), name="notebook-podcast-jobs"),
    path("notebooks/<int:notebook_id>/podcast-jobs/<str:job_id>/", views.NotebookPodcastJobDetailView.as_view(), name="notebook-podcast-job-detail"),
    path("notebooks/<int:notebook_id>/podcast-jobs/<str:job_id>/cancel/", views.NotebookPodcastJobCancelView.as_view(), name="notebook-podcast-job-cancel"),
    path("notebooks/<int:notebook_id>/podcast-jobs/<str:job_id>/audio/", views.NotebookPodcastJobAudioView.as_view(), name="notebook-podcast-job-audio"),
    
    # Stream endpoint for job status updates
    path(
        "notebooks/<int:notebook_id>/podcast-jobs/<str:job_id>/stream/",
        csrf_exempt(views.notebook_job_status_stream),
        name="notebook-podcast-job-status-stream",
    ),
]
