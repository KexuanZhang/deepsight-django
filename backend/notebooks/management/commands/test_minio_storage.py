"""
Django management command to test MinIO storage integration.
"""

from django.core.management.base import BaseCommand
from django.conf import settings
import tempfile
import os


class Command(BaseCommand):
    help = 'Test MinIO storage integration'

    def add_arguments(self, parser):
        parser.add_argument(
            '--storage-backend',
            type=str,
            default='minio',
            help='Storage backend to test (minio or local)',
        )
        parser.add_argument(
            '--test-upload',
            action='store_true',
            help='Test file upload functionality',
        )
        parser.add_argument(
            '--test-retrieval',
            action='store_true',
            help='Test file retrieval functionality',
        )

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Testing MinIO Storage Integration'))
        
        # Test storage adapter
        self.test_storage_adapter(options['storage_backend'])
        
        if options['test_upload']:
            self.test_file_upload()
        
        if options['test_retrieval']:
            self.test_file_retrieval()
    
    def test_storage_adapter(self, backend):
        """Test storage adapter initialization."""
        try:
            from notebooks.utils.storage_adapter import get_storage_adapter
            
            self.stdout.write(f"Testing storage adapter with backend: {backend}")
            
            # Temporarily override settings
            original_backend = getattr(settings, 'STORAGE_BACKEND', 'local')
            settings.STORAGE_BACKEND = backend
            
            try:
                adapter = get_storage_adapter()
                storage_info = adapter.get_storage_info()
                
                self.stdout.write(self.style.SUCCESS(f"✓ Storage adapter initialized successfully"))
                self.stdout.write(f"Backend: {storage_info['backend']}")
                self.stdout.write(f"Service: {storage_info['service_class']}")
                self.stdout.write(f"MinIO: {storage_info['is_minio']}")
                
                if storage_info['is_minio']:
                    self.stdout.write(f"MinIO Endpoint: {storage_info.get('minio_endpoint', 'N/A')}")
                    self.stdout.write(f"MinIO Bucket: {storage_info.get('minio_bucket', 'N/A')}")
                else:
                    self.stdout.write(f"Local Media Root: {storage_info.get('local_media_root', 'N/A')}")
                
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"✗ Failed to initialize storage adapter: {e}"))
            finally:
                # Restore original backend
                settings.STORAGE_BACKEND = original_backend
                
        except ImportError as e:
            self.stdout.write(self.style.ERROR(f"✗ Failed to import storage adapter: {e}"))
    
    def test_file_upload(self):
        """Test file upload functionality."""
        try:
            from notebooks.utils.storage_adapter import get_storage_adapter
            
            self.stdout.write("Testing file upload...")
            
            # Create a test file
            test_content = "This is a test file for MinIO storage integration."
            test_metadata = {
                'filename': 'test_file.txt',
                'original_filename': 'test_file.txt',
                'file_extension': '.txt',
                'content_type': 'text/plain',
                'file_size': len(test_content.encode()),
                'upload_timestamp': '2025-01-14T10:00:00Z',
            }
            test_processing_result = {
                'content_filename': 'test_extracted.md',
            }
            
            adapter = get_storage_adapter()
            
            # Note: This would require a real user and notebook in the database
            # For now, we'll just test the adapter initialization
            self.stdout.write(self.style.WARNING("Skipping actual upload test - requires database setup"))
            self.stdout.write("To test uploads, create a user and notebook first")
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"✗ Upload test failed: {e}"))
    
    def test_file_retrieval(self):
        """Test file retrieval functionality."""
        try:
            from notebooks.utils.storage_adapter import get_storage_adapter
            
            self.stdout.write("Testing file retrieval...")
            
            adapter = get_storage_adapter()
            
            # Test getting user knowledge base (empty is fine)
            knowledge_base = adapter.get_user_knowledge_base(user_id=1, limit=1)
            self.stdout.write(f"✓ Retrieved knowledge base items: {len(knowledge_base)}")
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"✗ Retrieval test failed: {e}"))
    
    def test_minio_backend_direct(self):
        """Test MinIO backend directly."""
        try:
            from notebooks.utils.storage import get_minio_backend
            
            self.stdout.write("Testing MinIO backend directly...")
            
            backend = get_minio_backend()
            
            # Test basic operations
            test_content = b"Hello MinIO!"
            object_key = backend.save_file_with_auto_key(
                content=test_content,
                filename="test.txt",
                prefix="test"
            )
            
            self.stdout.write(f"✓ Saved test file: {object_key}")
            
            # Retrieve content
            retrieved_content = backend.get_file_content(object_key)
            if retrieved_content == test_content:
                self.stdout.write("✓ Content retrieval successful")
            else:
                self.stdout.write(self.style.ERROR("✗ Content mismatch"))
            
            # Generate URL
            url = backend.get_presigned_url(object_key, expires=300)
            self.stdout.write(f"✓ Generated URL: {url[:50]}...")
            
            # Clean up
            if backend.delete_file(object_key):
                self.stdout.write("✓ File cleanup successful")
            else:
                self.stdout.write(self.style.WARNING("⚠ File cleanup failed"))
                
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"✗ MinIO backend test failed: {e}"))