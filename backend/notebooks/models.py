"""
Notebooks models - import from organized model package.

This file maintains backward compatibility while using the new
organized model structure following Django best practices.
"""

# Import all models from the organized package
from .models.notebook import Notebook
from .models.knowledge_item import KnowledgeBaseItem, KnowledgeBaseImage  
from .models.batch_processing import BatchJob, BatchJobItem
from .models.chat import NotebookChatMessage
from .models.ragflow_dataset import RagFlowDataset

# Export all models for backward compatibility
__all__ = [
    'Notebook',
    'KnowledgeBaseItem', 
    'KnowledgeBaseImage',
    'BatchJob',
    'BatchJobItem',
    'NotebookChatMessage',
    'RagFlowDataset',
]