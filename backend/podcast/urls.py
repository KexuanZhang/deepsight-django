from django.urls import path, include
from rest_framework.routers import DefaultRouter
from django.views.decorators.csrf import csrf_exempt
from . import views

router = DefaultRouter()
router.register(r'jobs', views.PodcastJobViewSet, basename='podcast-jobs')

urlpatterns = [
    # API endpoints
    path('', include(router.urls)),
    
    # Audio file serving
    path('audio/<str:filename>', views.podcast_audio_serve, name='podcast-audio-serve'),
    
    # Summary statistics
    path('summary', views.podcast_jobs_summary, name='podcast-jobs-summary'),
    
    # SSE endpoint for job status updates (CSRF exempt for CORS)
    path('stream/job-status/<str:job_id>', csrf_exempt(views.job_status_stream), name='podcast-job-status-stream'),
]