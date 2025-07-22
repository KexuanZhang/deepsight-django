import boto3
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = 'Delete the MinIO bucket and all its objects'

    def handle(self, *args, **options):
        s3 = boto3.resource(
            's3',
            endpoint_url='http://localhost:9000',
            aws_access_key_id='minioadmin',
            aws_secret_access_key='minioadmin'
        )

        bucket = s3.Bucket('deepsight-users')
        
        try:
            # Delete all objects first
            self.stdout.write('Deleting all objects from bucket...')
            bucket.objects.all().delete()
            
            # Then delete the bucket
            self.stdout.write('Deleting bucket...')
            bucket.delete()
            
            self.stdout.write(
                self.style.SUCCESS('Successfully deleted bucket "deepsight-users" and all its objects')
            )
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Error deleting bucket: {str(e)}')
            )
