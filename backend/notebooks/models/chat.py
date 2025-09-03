"""
Chat message models for notebook conversations.
"""

from django.db import models
from django.core.exceptions import ValidationError
from core.mixins import BaseModel


class NotebookChatMessage(BaseModel):
    """
    Chat messages within a notebook conversation.
    Stores both user messages and AI assistant responses.
    """
    
    SENDER_CHOICES = [
        ("user", "User"),
        ("assistant", "Assistant")
    ]
    
    notebook = models.ForeignKey(
        'notebooks.Notebook',
        on_delete=models.CASCADE,
        related_name="chat_messages",
        help_text="Notebook this chat message belongs to"
    )
    sender = models.CharField(
        max_length=10,
        choices=SENDER_CHOICES,
        help_text="Who sent this message"
    )
    message = models.TextField(
        help_text="Content of the chat message"
    )
    timestamp = models.DateTimeField(
        auto_now_add=True,
        help_text="When the message was sent"
    )
    
    # Additional metadata for AI responses
    metadata = models.JSONField(
        blank=True,
        null=True,
        help_text="Additional metadata like sources, confidence, etc."
    )

    class Meta:
        ordering = ["timestamp"]
        verbose_name = "Notebook Chat Message"
        verbose_name_plural = "Notebook Chat Messages"
        indexes = [
            models.Index(fields=["notebook", "timestamp"]),
            models.Index(fields=["notebook", "sender", "timestamp"]),
        ]
        constraints = [
            models.CheckConstraint(
                check=~models.Q(message=""),
                name='chat_message_not_empty'
            )
        ]

    def __str__(self):
        return f"{self.sender}: {self.message[:50]}..."
    
    def clean(self):
        """Django model validation."""
        if not self.message or not self.message.strip():
            raise ValidationError("Chat message cannot be empty")
        
        # Normalize the message
        self.message = self.message.strip()
        
        # Validate metadata is a dict if provided
        if self.metadata is not None and not isinstance(self.metadata, dict):
            raise ValidationError("Metadata must be a dictionary")
    
    def save(self, *args, **kwargs):
        """Override save to ensure validation."""
        self.full_clean()
        super().save(*args, **kwargs)
    
    def is_user_message(self):
        """Check if this message is from a user."""
        return self.sender == "user"
    
    def is_assistant_message(self):
        """Check if this message is from the assistant."""
        return self.sender == "assistant"
    
    def get_sources(self):
        """Get sources from metadata if available."""
        if self.metadata and isinstance(self.metadata, dict):
            return self.metadata.get('sources', [])
        return []
    
    def add_source(self, source_id, source_title=None):
        """Add a source reference to this message."""
        if not self.metadata:
            self.metadata = {}
        
        if 'sources' not in self.metadata:
            self.metadata['sources'] = []
        
        source_info = {'id': source_id}
        if source_title:
            source_info['title'] = source_title
        
        if source_info not in self.metadata['sources']:
            self.metadata['sources'].append(source_info)
            self.save(update_fields=['metadata', 'updated_at'])
    
    def set_confidence(self, confidence_score):
        """Set confidence score for AI responses."""
        if not self.metadata:
            self.metadata = {}
        
        self.metadata['confidence'] = confidence_score
        self.save(update_fields=['metadata', 'updated_at'])
    
    def get_confidence(self):
        """Get confidence score if available."""
        if self.metadata and isinstance(self.metadata, dict):
            return self.metadata.get('confidence')
        return None