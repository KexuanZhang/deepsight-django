import boto3

s3 = boto3.resource(
    's3',
    endpoint_url='http://localhost:9000',
    aws_access_key_id='minioadmin',
    aws_secret_access_key='minioadmin'
)

bucket = s3.Bucket('test-bucket')
bucket.objects.all().delete()  # Delete all objects first
bucket.delete()                # Then delete the bucket
