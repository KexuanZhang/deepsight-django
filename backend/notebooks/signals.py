"""
Real-time event signals for notebook file changes
"""
import logging
import threading
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.core.cache import cache
from .models import KnowledgeItem, KnowledgeBaseItem

logger = logging.getLogger(__name__)

# Thread-local storage for SSE event broadcasting
_thread_local = threading.local()

class NotebookFileChangeNotifier:
    """Manages real-time notifications for notebook file changes"""
    
    @staticmethod
    def notify_file_change(notebook_id, change_type, file_data=None):
        """Notify SSE streams about file changes"""
        cache_key = f"notebook_file_changes_{notebook_id}"
        
        # Store change event in cache with timestamp
        import time
        change_event = {
            'type': change_type,
            'timestamp': time.time(),
            'file_data': file_data,
            'notebook_id': str(notebook_id)
        }
        
        # Store in cache for SSE streams to pick up
        cache.set(cache_key, change_event, timeout=30)  # 30 second timeout
        logger.info(f"File change notification: {change_type} for notebook {notebook_id}")

@receiver(post_save, sender=KnowledgeItem)
def on_knowledge_item_saved(sender, instance, created, **kwargs):
    """Handle KnowledgeItem creation/updates"""
    try:
        if created:
            # New file added to notebook
            NotebookFileChangeNotifier.notify_file_change(
                notebook_id=instance.notebook.id,
                change_type='file_added',
                file_data={
                    'file_id': str(instance.knowledge_base_item.id),
                    'title': instance.knowledge_base_item.title,
                    'status': instance.knowledge_base_item.processing_status
                }
            )
        else:
            # File updated in notebook
            NotebookFileChangeNotifier.notify_file_change(
                notebook_id=instance.notebook.id,
                change_type='file_updated',
                file_data={
                    'file_id': str(instance.knowledge_base_item.id),
                    'title': instance.knowledge_base_item.title,
                    'status': instance.knowledge_base_item.processing_status
                }
            )
    except Exception as e:
        logger.error(f"Error in knowledge_item post_save signal: {e}")

@receiver(post_delete, sender=KnowledgeItem)
def on_knowledge_item_deleted(sender, instance, **kwargs):
    """Handle KnowledgeItem deletion"""
    try:
        NotebookFileChangeNotifier.notify_file_change(
            notebook_id=instance.notebook.id,
            change_type='file_removed',
            file_data={
                'file_id': str(instance.knowledge_base_item.id),
                'title': instance.knowledge_base_item.title
            }
        )
    except Exception as e:
        logger.error(f"Error in knowledge_item post_delete signal: {e}")

@receiver(post_save, sender=KnowledgeBaseItem)
def on_knowledge_base_item_saved(sender, instance, created, **kwargs):
    """Handle KnowledgeBaseItem status changes"""
    try:
        if not created:
            # Check if processing status changed
            update_fields = kwargs.get('update_fields') or []
            if 'processing_status' in update_fields or not update_fields:
                # Find all notebooks this item is linked to
                knowledge_items = KnowledgeItem.objects.filter(knowledge_base_item=instance)
                logger.info(f"[SSE_DEBUG] KnowledgeBaseItem {instance.id} status updated to '{instance.processing_status}', found {knowledge_items.count()} linked notebooks")
                
                for ki in knowledge_items:
                    logger.info(f"[SSE_DEBUG] Sending file_status_updated signal for notebook {ki.notebook.id}")
                    # Map processing status to parsing status for consistency with API
                    parsing_status = "completed"  # Default for completed items
                    if instance.processing_status == "in_progress":
                        parsing_status = "in_progress"
                    elif instance.processing_status == "error":
                        parsing_status = "error"
                    elif instance.processing_status == "pending":
                        parsing_status = "pending"
                    elif instance.processing_status == "done":
                        parsing_status = "completed"
                    
                    NotebookFileChangeNotifier.notify_file_change(
                        notebook_id=ki.notebook.id,
                        change_type='file_status_updated',
                        file_data={
                            'file_id': str(instance.id),
                            'title': instance.title,
                            'status': parsing_status,  # Use mapped status
                            'processing_status': instance.processing_status  # Include original for debugging
                        }
                    )
    except Exception as e:
        logger.error(f"Error in knowledge_base_item post_save signal: {e}")