import uuid
from django.db import models


class Venue(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    type = models.CharField(max_length=255)
    description = models.TextField()

    def __str__(self):
        return self.name


class Instance(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    venue = models.ForeignKey(Venue, on_delete=models.CASCADE, related_name='instances')
    year = models.IntegerField()
    start_date = models.DateField()
    end_date = models.DateField()
    location = models.CharField(max_length=255)
    website = models.CharField(max_length=255)
    summary = models.TextField()

    def __str__(self):
        return f"{self.venue.name} {self.year}"


class Publication(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    instance = models.ForeignKey(Instance, on_delete=models.CASCADE, related_name='publications')
    title = models.CharField(max_length=255)
    authors = models.CharField(max_length=255)
    orgnizations = models.CharField(max_length=255)
    publish_date = models.DateField()
    summary = models.TextField()
    keywords = models.CharField(max_length=500)
    research_topic = models.CharField(max_length=500)
    abstract = models.TextField()
    raw_file = models.CharField(max_length=255)
    tag = models.CharField(max_length=255)
    doi = models.CharField(max_length=255)
    pdf_url = models.CharField(max_length=255)

    def __str__(self):
        return self.title


class Session(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    session_id = models.IntegerField()
    instance = models.ForeignKey(Instance, on_delete=models.CASCADE, related_name='sessions')
    publication = models.ForeignKey(Publication, on_delete=models.SET_NULL, null=True, blank=True, related_name='sessions')
    title = models.CharField(max_length=255)
    description = models.TextField()
    transcript = models.TextField()
    expert_view = models.TextField()
    ai_analysis = models.TextField()

    def __str__(self):
        return self.title
