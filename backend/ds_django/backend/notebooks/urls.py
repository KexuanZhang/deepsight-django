# notebooks/urls.py

from django.urls import path
from .views import (
    NotebookListCreateAPIView,
    NotebookRetrieveUpdateDestroyAPIView,
    FileUploadView,
)

urlpatterns = [
    path('notebooks/', NotebookListCreateAPIView.as_view(), name='notebook-list-create'),
    path('notebooks/<int:pk>/', NotebookRetrieveUpdateDestroyAPIView.as_view(), name='notebook-detail'),
    path("sources/upload/"   , FileUploadView.as_view(), name="source-file-upload"),
]
