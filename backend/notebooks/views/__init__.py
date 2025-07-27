"""
Views package - Organized into focused modules by responsibility
"""

# Import all views from each focused module
from .notebook_views import (
    NotebookListCreateAPIView,
    NotebookRetrieveUpdateDestroyAPIView,
)

from .file_views import (
    FileUploadView,
    FileListView,
    FileStatusView,
    FileStatusStreamView,
    NotebookFileListStreamView,
    NotebookFileStatusStreamView,
    FileDeleteView,
    FileContentView,
    FileContentMinIOView,
    FileRawView,
    FileRawSimpleView,
    VideoImageExtractionView,
    FileImageView,
)

from .url_views import (
    URLParseView,
    URLParseWithMediaView,
    URLParseDocumentView,
    SimpleTestView,
)

from .chat_views import (
    RAGChatFromKBView,
    ChatHistoryView,
    ClearChatHistoryView,
    SuggestedQuestionsView,
)

from .knowledge_views import (
    KnowledgeBaseView,
    KnowledgeBaseImagesView,
)

from .batch_views import (
    BatchJobStatusView,
)

# Explicit exports for clarity
__all__ = [
    # Notebook views
    "NotebookListCreateAPIView",
    "NotebookRetrieveUpdateDestroyAPIView",
    
    # File views
    "FileUploadView",
    "FileListView", 
    "FileStatusView",
    "FileStatusStreamView",
    "NotebookFileListStreamView",
    "NotebookFileStatusStreamView",
    "FileDeleteView",
    "FileContentView",
    "FileContentMinIOView",
    "FileRawView",
    "FileRawSimpleView",
    "VideoImageExtractionView",
    "FileImageView",
    
    # URL views
    "URLParseView",
    "URLParseWithMediaView",
    "URLParseDocumentView",
    "SimpleTestView",
    
    # Chat views
    "RAGChatFromKBView",
    "ChatHistoryView",
    "ClearChatHistoryView",
    "SuggestedQuestionsView",
    
    # Knowledge base views
    "KnowledgeBaseView",
    "KnowledgeBaseImagesView",
    
    # Batch job views
    "BatchJobStatusView",
] 