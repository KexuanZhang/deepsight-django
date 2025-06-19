# notebooks/urls.py

from django.urls import path
from .views import (
    NotebookListCreateAPIView,
    NotebookRetrieveUpdateDestroyAPIView,
    FileListView,
    FileUploadView,
    FileStatusView,
    FileDeleteView,
)

urlpatterns = [
    # Notebooks
    path('notebooks/', 
         NotebookListCreateAPIView.as_view(), 
         name='notebook-list-create'),
    path('notebooks/<int:pk>/', 
         NotebookRetrieveUpdateDestroyAPIView.as_view(), 
         name='notebook-detail'),

    # File endpoints for a given notebook
    # 1) list all processed files
    path(
        'notebooks/<int:notebook_id>/files/',
        FileListView.as_view(),
        name='file-list'
    ),

    # 2) upload & parse a new file
    path(
        'notebooks/<int:notebook_id>/files/upload/',
        FileUploadView.as_view(),
        name='file-upload'
    ),

    # 3) get one‐time status snapshot for an in‐flight upload
    path(
        'notebooks/<int:notebook_id>/files/<str:upload_file_id>/status/',
        FileStatusView.as_view(),
        name='file-status'
    ),

    # 4) delete either an in‐flight upload or a completed file
    path(
        'notebooks/<int:notebook_id>/files/<str:file_or_upload_id>/',
        FileDeleteView.as_view(),
        name='file-delete'
    ),
]
