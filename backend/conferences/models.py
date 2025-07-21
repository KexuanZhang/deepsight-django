import uuid
from django.db import models
from storages.backends.s3boto3 import S3Boto3Storage

def publication_file_path(instance, filename):
    """
    e.g. publications/CVPR/2017/3303/3D_Bounding_Box_Estimation.pdf
    """
    venue   = instance.instance.venue.name.replace(" ", "_")
    year    = instance.instance.year
    pid     = instance.publication_id or "new"
    return f"publications/{venue}/{year}/{pid}/{filename}"

class Venue(models.Model):
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=255)
    type = models.CharField(max_length=255)
    description = models.TextField()

    def __str__(self):
        return self.name


class Instance(models.Model):
    instance_id = models.AutoField(primary_key=True)
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
    publication_id = models.AutoField(primary_key=True)
    instance = models.ForeignKey(Instance, on_delete=models.CASCADE, related_name='publications')
    title = models.CharField(max_length=255)
    authors = models.CharField(max_length=255)
    orgnizations = models.CharField(max_length=255)
    publish_date = models.DateField()
    summary = models.TextField()
    keywords = models.CharField(max_length=500)
    research_topic = models.CharField(max_length=500)
    abstract       = models.TextField()

    raw_file = models.FileField(
        upload_to=publication_file_path,
        storage=S3Boto3Storage(),    # uses your MinIO‐configured S3 backend
        blank=True,
        null=True,
        help_text="PDF file stored in MinIO",
    )

    tag      = models.CharField(max_length=255)
    doi      = models.CharField(max_length=255)
    pdf_url  = models.CharField(max_length=255)

    def __str__(self):
        return self.title


class Session(models.Model):
    event_id = models.AutoField(primary_key=True)
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
