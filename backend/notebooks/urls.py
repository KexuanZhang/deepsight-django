# notebooks/urls.py

from django.urls import path
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
    MarkdownBatchContentView,
    RAGChatFromKBView,
)

urlpatterns = [
    # Notebooks
    path('', 
         NotebookListCreateAPIView.as_view(), 
         name='notebook-list-create'),
    path('<int:pk>/', 
         NotebookRetrieveUpdateDestroyAPIView.as_view(), 
         name='notebook-detail'),

    # File endpoints for a given notebook
    # 1) list all processed files
    path(
        '<int:notebook_id>/files/',
        FileListView.as_view(),
        name='file-list'
    ),

    path(
        '<int:notebook_id>/files/md-batch-contents/',
        MarkdownBatchContentView.as_view(),
        name='file-md-batch-contents'
    ),

    path('chat/', RAGChatFromKBView.as_view(), name='chat-rag'),

    # 2) upload & parse a new file
    path(
        '<int:notebook_id>/files/upload/',
        FileUploadView.as_view(),
        name='file-upload'
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
        '<int:notebook_id>/files/<str:upload_file_id>/status/',
        FileStatusView.as_view(),
        name='file-status'
    ),

    # 5.1) SSE streaming status updates for an in‐flight upload
    path(
        '<int:notebook_id>/files/<str:upload_file_id>/status/stream',
        FileStatusStreamView.as_view(),
        name='file-status-stream'
    ),

    # 6) delete either an in‐flight upload or a completed file
    path(
        '<int:notebook_id>/files/<str:file_or_upload_id>/',
        FileDeleteView.as_view(),
        name='file-delete'
    ),

    # 7) knowledge base management
    path(
        '<int:notebook_id>/knowledge-base/',
        KnowledgeBaseView.as_view(),
        name='knowledge-base'
    ),

    # 8) file content serving (parsed content)
    path(
        'files/<str:file_id>/content/',
        FileContentView.as_view(),
        name='file-content'
    ),

    # 9) raw file serving (PDFs, videos, audio, etc.)
    path(
        '<int:notebook_id>/files/<str:file_id>/raw/',
        FileRawView.as_view(),
        name='file-raw'
    ),

    # 10) simplified raw file serving (without notebook context)
    path(
        'files/<str:file_id>/raw/',
        FileRawSimpleView.as_view(),
        name='file-raw-simple'
    ),
]
