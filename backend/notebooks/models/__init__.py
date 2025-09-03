"""
Notebooks models package.

This package organizes notebook-related models following Django best practices.
Each model is in its own focused module for better maintainability.
"""

from .notebook import Notebook
from .knowledge_item import KnowledgeBaseItem, KnowledgeBaseImage
from .batch_processing import BatchJob, BatchJobItem
from .chat import NotebookChatMessage
from .ragflow_dataset import RagFlowDataset

# Maintain backward compatibility
__all__ = [
    'Notebook',
    'KnowledgeBaseItem', 
    'KnowledgeBaseImage',
    'BatchJob',
    'BatchJobItem',
    'NotebookChatMessage',
    'RagFlowDataset',
]