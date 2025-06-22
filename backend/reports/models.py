# reports/models.py
from django.db import models
from django.conf import settings

class Report(models.Model):
    # Associations
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='reports'
    )
    # Optional linking to a notebook (if relevant)
    notebooks = models.ForeignKey(
        'notebooks.Notebook',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='reports'
    )

    # Input parameters for report generation
    topic = models.CharField(max_length=255, blank=True)
    transcript_content = models.TextField(blank=True)
    paper_content = models.TextField(blank=True)
    article_title = models.CharField(max_length=255, default='Research Report')

    # Configuration choices
    MODEL_PROVIDER_OPENAI = 'openai'
    MODEL_PROVIDER_CHOICES = [
        (MODEL_PROVIDER_OPENAI, 'OpenAI'),
        # add other providers if needed
    ]
    model_provider = models.CharField(
        max_length=50,
        choices=MODEL_PROVIDER_CHOICES,
        default=MODEL_PROVIDER_OPENAI
    )

    RETRIEVER_TAVILY = 'tavily'
    RETRIEVER_CHOICES = [
        (RETRIEVER_TAVILY, 'Tavily'),
        # add other retriever options
    ]
    retriever = models.CharField(
        max_length=50,
        choices=RETRIEVER_CHOICES,
        default=RETRIEVER_TAVILY
    )

    temperature = models.FloatField(default=0.2)
    top_p = models.FloatField(default=0.4)
    max_conv_turn = models.PositiveIntegerField(default=3)

    # Status tracking
    STATUS_PENDING = 'pending'
    STATUS_RUNNING = 'running'
    STATUS_COMPLETED = 'completed'
    STATUS_FAILED = 'failed'
    STATUS_CHOICES = [
        (STATUS_PENDING, 'Pending'),
        (STATUS_RUNNING, 'Running'),
        (STATUS_COMPLETED, 'Completed'),
        (STATUS_FAILED, 'Failed'),
    ]
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_PENDING
    )

    # Result of generation (JSON or text)
    result_content = models.TextField(blank=True)
    error_message = models.TextField(blank=True)

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Report {self.id} ({self.status}) for {self.user.username}"
