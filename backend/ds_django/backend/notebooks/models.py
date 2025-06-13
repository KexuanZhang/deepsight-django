# notebooks/models.py
from django.db import models
from django.conf import settings

class Notebook(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='notebooks'
    )
    name = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

class UploadedPDF(models.Model):
    notebook = models.ForeignKey(
        Notebook,
        on_delete=models.CASCADE,
        related_name='uploaded_pdfs'
    )
    file = models.FileField(upload_to='notebooks/pdfs/')
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.file.name

class NotebookSource(models.Model):
    SOURCE_TYPE_PUBLICATION = 'publication'
    SOURCE_TYPE_EVENT = 'event'
    SOURCE_TYPE_CHOICES = [
        (SOURCE_TYPE_PUBLICATION, 'Publication'),
        (SOURCE_TYPE_EVENT, 'Event'),
    ]

    notebook = models.ForeignKey(
        Notebook,
        on_delete=models.CASCADE,
        related_name='sources'
    )
    source_type = models.CharField(
        max_length=50,
        choices=SOURCE_TYPE_CHOICES
    )
    publication = models.ForeignKey(
        'publications.Publication',
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    event = models.ForeignKey(
        'events.Event',
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )

    def __str__(self):
        return f"{self.get_source_type_display()} in {self.notebook.name}"
