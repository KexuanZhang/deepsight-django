# notebooks/urls.py

from django.urls import path
from .views import (
    NotebookListCreateAPIView,
    NotebookRetrieveUpdateDestroyAPIView,
    FileListView,
    FileUploadView,
    FileStatusView,
    FileStatusStreamView,
    FileDeleteView,
    KnowledgeBaseView,
    FileContentView,
    FileRawView,
    FileRawSimpleView,
    RAGChatFromKBView,
    ChatHistoryView,
    ClearChatHistoryView
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
        '<int:notebook_id>/chat-history/', ChatHistoryView.as_view(), name="chat-history"
    ),

    path('chat/', RAGChatFromKBView.as_view(), name='chat-rag'),

    # 2) upload & parse a new file
    path(
        '<int:notebook_id>/files/upload/',
        FileUploadView.as_view(),
        name='file-upload'
    ),

    # 3) get one‐time status snapshot for an in‐flight upload
    path(
        '<int:notebook_id>/files/<str:upload_file_id>/status/',
        FileStatusView.as_view(),
        name='file-status'
    ),

    # 3.1) SSE streaming status updates for an in‐flight upload
    path(
        '<int:notebook_id>/files/<str:upload_file_id>/status/stream',
        FileStatusStreamView.as_view(),
        name='file-status-stream'
    ),

    # 4) delete either an in‐flight upload or a completed file
    path(
        '<int:notebook_id>/files/<str:file_or_upload_id>/',
        FileDeleteView.as_view(),
        name='file-delete'
    ),

    # 5) knowledge base management
    path(
        '<int:notebook_id>/knowledge-base/',
        KnowledgeBaseView.as_view(),
        name='knowledge-base'
    ),

    # 6) file content serving (parsed content)
    path(
        'files/<str:file_id>/content/',
        FileContentView.as_view(),
        name='file-content'
    ),

    path(
        "<int:notebook_id>/chat/clear/", 
         ClearChatHistoryView.as_view(), 
         name="clear-chat-history"
    ),


    # 7) raw file serving (PDFs, videos, audio, etc.)
    path(
        '<int:notebook_id>/files/<str:file_id>/raw/',
        FileRawView.as_view(),
        name='file-raw'
    ),

    # 8) simplified raw file serving (without notebook context)
    path(
        'files/<str:file_id>/raw/',
        FileRawSimpleView.as_view(),
        name='file-raw-simple'
    ),
]
