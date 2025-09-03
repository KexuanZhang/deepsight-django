"""
URL configuration for notebooks API v1.

Provides RESTful API endpoints using Django REST Framework patterns
with proper ViewSet routing and nested resource handling.
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_nested import routers

from .views import (
    NotebookViewSet,
    FileViewSet,
    ChatViewSet,
    KnowledgeBaseViewSet,
    BatchJobViewSet
)

# Main router for top-level resources
router = DefaultRouter()
router.register(r'', NotebookViewSet, basename='notebook')

# Nested routers for notebook-related resources  
notebooks_router = routers.NestedDefaultRouter(router, r'', lookup='notebook')
notebooks_router.register(r'files', FileViewSet, basename='notebook-files')
notebooks_router.register(r'chat', ChatViewSet, basename='notebook-chat')
notebooks_router.register(r'knowledge', KnowledgeBaseViewSet, basename='notebook-knowledge')
notebooks_router.register(r'batches', BatchJobViewSet, basename='notebook-batches')

app_name = 'notebooks-api-v1'

from .views import ChatHistoryView

urlpatterns = [
    # Include main router URLs
    path('', include(router.urls)),
    
    # Include nested router URLs
    path('', include(notebooks_router.urls)),
    
    # Custom endpoints for API consistency with frontend expectations
    path('<uuid:notebook_pk>/chat-history/', ChatHistoryView.as_view(), name='chat-history'),
    
    # Additional custom endpoints (if needed)
    # path('health/', HealthCheckView.as_view(), name='health-check'),
]