# Notebooks Module Refactor Plan

## Executive Summary

The notebooks module has overly large files that are hard to maintain and test. This refactor breaks down the monolithic files into focused, manageable modules using standard Django patterns.

## Current Issues

**Main Problems:**
- `views.py` (2,413 lines) - Too many responsibilities in one file
- `upload_processor.py` (1,377 lines) - Handles too many different file types and operations
- `url_extractor.py` (883 lines) - Mixes URL validation, crawling, and processing

**Impact:** 
- Hard to test individual features
- Difficult to modify without breaking other functionality
- Code duplication and inconsistent error handling

## Refactor Structure

```
notebooks/
├── models.py                    # Keep existing models (well-structured)
├── admin.py
├── urls.py
├── migrations/
├── management/commands/
├── views/
│   ├── __init__.py
│   ├── notebook_views.py        # Notebook CRUD only
│   ├── file_views.py           # File upload/management only  
│   ├── url_views.py            # URL processing only
│   └── chat_views.py           # Chat functionality only
├── services/
│   ├── __init__.py
│   ├── file_service.py         # File processing logic
│   ├── url_service.py          # URL processing logic
│   └── notebook_service.py     # Notebook business logic
├── serializers/
│   ├── __init__.py
│   ├── notebook_serializers.py
│   ├── file_serializers.py
│   └── url_serializers.py
├── processors/
│   ├── __init__.py
│   ├── file_processors.py      # File type specific processors
│   └── url_processors.py       # URL type specific processors
├── utils/
│   ├── __init__.py
│   ├── validators.py           # Input validation
│   ├── storage.py              # Storage operations
│   └── helpers.py              # Common utilities
├── exceptions.py               # Custom exceptions
└── tasks.py                    # Celery tasks
```

## Implementation Steps

### Step 1: Split Views
1. **Create views/ directory**
2. **Split views.py into 4 focused files**:
   - `notebook_views.py` - Notebook CRUD only
   - `file_views.py` - File upload/management only  
   - `url_views.py` - URL processing only
   - `chat_views.py` - Chat functionality only
3. **Update urls.py** to import from new view modules
4. **Test each view works independently**

### Step 2: Extract Services  
1. **Create services/ directory**
2. **Extract business logic from views into services**:
   - `notebook_service.py` - Notebook operations
   - `file_service.py` - File processing logic
   - `url_service.py` - URL processing logic
3. **Update views to use services**
4. **Add error handling and validation**

### Step 3: Extract Processors
1. **Create processors/ directory** 
2. **Move file processing logic from utils/ to processors/**:
   - `file_processors.py` - File type specific processing
   - `url_processors.py` - URL domain specific processing
3. **Simplify existing upload_processor.py and url_extractor.py**
4. **Update services to use new processors**

### Step 4: Create Utilities
1. **Refactor utils/ directory**:
   - `validators.py` - Input validation only
   - `storage.py` - Storage operations only  
   - `helpers.py` - Common utilities only
2. **Remove duplicate code across modules**
3. **Add comprehensive validation**

### Step 5: Complete API Layer
1. **Create focused serializers**
2. **Simplify Celery tasks**
3. **Add custom exceptions**  
4. **Update URL patterns**
5. **Add comprehensive tests**

## Key Components

### Views Structure
```python
# views/notebook_views.py
from rest_framework import viewsets, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.shortcuts import get_object_or_404

from ..models import Notebook
from ..serializers.notebook_serializers import NotebookSerializer
from ..services.notebook_service import NotebookService

class NotebookViewSet(viewsets.ModelViewSet):
    """Handle notebook CRUD operations only"""
    serializer_class = NotebookSerializer
    permission_classes = [IsAuthenticated]
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.notebook_service = NotebookService()
    
    def get_queryset(self):
        return self.notebook_service.get_user_notebooks(self.request.user)
    
    def perform_create(self, serializer):
        self.notebook_service.create_notebook(serializer, self.request.user)

# views/file_views.py  
from rest_framework.views import APIView
from rest_framework.parsers import MultiPartParser
from rest_framework.response import Response
from rest_framework import status

from ..serializers.file_serializers import FileUploadSerializer
from ..services.file_service import FileService

class FileUploadView(APIView):
    """Handle file uploads only"""
    parser_classes = [MultiPartParser]
    permission_classes = [IsAuthenticated]
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.file_service = FileService()
    
    def post(self, request, notebook_id):
        serializer = FileUploadSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        result = self.file_service.upload_file(
            file=serializer.validated_data['file'],
            notebook_id=notebook_id,
            user=request.user
        )
        
        return Response(result, status=status.HTTP_201_CREATED)

# views/url_views.py
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from ..serializers.url_serializers import URLProcessingSerializer
from ..services.url_service import URLService

class URLProcessingView(APIView):
    """Handle URL processing only"""
    permission_classes = [IsAuthenticated]
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.url_service = URLService()
    
    def post(self, request, notebook_id):
        serializer = URLProcessingSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        result = self.url_service.process_url(
            url=serializer.validated_data['url'],
            notebook_id=notebook_id,
            user=request.user
        )
        
        return Response(result, status=status.HTTP_202_ACCEPTED)
```

### Services Structure
```python
# services/file_service.py
from django.shortcuts import get_object_or_404
from ..models import Notebook

class NotebookService:
    """Handle notebook business logic"""
    
    def get_user_notebooks(self, user):
        """Get all notebooks for user"""
        return Notebook.objects.filter(user=user).order_by('-created_at')
    
    def create_notebook(self, serializer, user):
        """Create new notebook"""
        return serializer.save(user=user)
    
    def get_notebook_or_404(self, notebook_id, user):
        """Get notebook with permission check"""
        return get_object_or_404(Notebook, id=notebook_id, user=user)

# services/file_service.py
from django.db import transaction
from ..models import Source, KnowledgeBaseItem
from ..processors.file_processors import FileProcessor
from ..utils.validators import FileValidator
from ..tasks import process_file_task

class FileService:
    """Handle file processing business logic"""
    
    def __init__(self):
        self.validator = FileValidator()
        self.processor = FileProcessor()
    
    @transaction.atomic
    def upload_file(self, file, notebook_id, user):
        """Process file upload"""
        # Validate file
        self.validator.validate_file(file)
        
        # Create source record
        source = Source.objects.create(
            notebook_id=notebook_id,
            source_type='file',
            title=file.name,
            processing_status='pending'
        )
        
        # Queue processing task
        process_file_task.delay(
            file_data=file.read(),
            filename=file.name,
            source_id=str(source.id),
            user_id=user.id
        )
        
        return {
            'source_id': str(source.id),
            'status': 'queued',
            'message': 'File upload queued for processing'
        }

# services/url_service.py
from django.db import transaction
from ..models import Source
from ..processors.url_processors import URLProcessor
from ..utils.validators import URLValidator
from ..tasks import process_url_task

class URLService:
    """Handle URL processing business logic"""
    
    def __init__(self):
        self.validator = URLValidator()
        self.processor = URLProcessor()
    
    @transaction.atomic
    def process_url(self, url, notebook_id, user):
        """Process URL"""
        # Validate URL
        self.validator.validate_url(url)
        
        # Create source record
        source = Source.objects.create(
            notebook_id=notebook_id,
            source_type='url',
            title=url,
            processing_status='pending'
        )
        
        # Queue processing task
        process_url_task.delay(
            url=url,
            source_id=str(source.id),
            user_id=user.id
        )
        
        return {
            'source_id': str(source.id),
            'status': 'queued',
            'message': 'URL queued for processing'
        }
```

### Processors Structure
```python
# processors/file_processors.py
import os
import tempfile
from typing import Dict, Any
from django.core.files.uploadedfile import UploadedFile

class FileProcessor:
    """Handle file type specific processing"""
    
    def __init__(self):
        self.processors = {
            'application/pdf': self._process_pdf,
            'text/plain': self._process_text,
            'text/markdown': self._process_markdown,
            'image/jpeg': self._process_image,
            'image/png': self._process_image,
            'video/mp4': self._process_video,
        }
    
    def process_file(self, file_path: str, content_type: str) -> Dict[str, Any]:
        """Process file based on its type"""
        processor = self.processors.get(content_type)
        if not processor:
            raise ValueError(f"Unsupported file type: {content_type}")
        
        return processor(file_path)
    
    def _process_pdf(self, file_path: str) -> Dict[str, Any]:
        """Extract text and images from PDF"""
        try:
            import fitz  # PyMuPDF
            doc = fitz.open(file_path)
            
            text_content = ""
            images = []
            
            for page_num in range(doc.page_count):
                page = doc[page_num]
                text_content += page.get_text()
                
                # Extract images
                image_list = page.get_images()
                for img_index, img in enumerate(image_list):
                    # Process images if needed
                    pass
            
            return {
                'content': text_content,
                'images': images,
                'page_count': doc.page_count
            }
        except ImportError:
            # Fallback to PyPDF2
            return self._process_pdf_fallback(file_path)
    
    def _process_text(self, file_path: str) -> Dict[str, Any]:
        """Process plain text files"""
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        return {
            'content': content,
            'word_count': len(content.split())
        }
    
    def _process_image(self, file_path: str) -> Dict[str, Any]:
        """Process images with OCR"""
        try:
            import pytesseract
            from PIL import Image
            
            image = Image.open(file_path)
            text = pytesseract.image_to_string(image)
            
            return {
                'content': text,
                'dimensions': image.size,
                'format': image.format
            }
        except ImportError:
            return {'content': '', 'error': 'OCR not available'}

# processors/url_processors.py
import asyncio
from typing import Dict, Any
from urllib.parse import urlparse

class URLProcessor:
    """Handle URL type specific processing"""
    
    def __init__(self):
        self.processors = {
            'youtube.com': self._process_youtube,
            'arxiv.org': self._process_arxiv,
            'github.com': self._process_github,
            'default': self._process_webpage
        }
    
    async def process_url(self, url: str) -> Dict[str, Any]:
        """Process URL based on domain"""
        parsed = urlparse(url)
        domain = parsed.netloc.lower()
        
        # Find specific processor or use default
        processor = self.processors.get(domain, self.processors['default'])
        return await processor(url)
    
    async def _process_webpage(self, url: str) -> Dict[str, Any]:
        """Extract content from general webpage"""
        try:
            from crawl4ai import AsyncWebCrawler
            
            async with AsyncWebCrawler() as crawler:
                result = await crawler.arun(url=url)
                
                return {
                    'content': result.markdown,
                    'title': result.title,
                    'url': url,
                    'success': result.success
                }
        except ImportError:
            return {'content': '', 'error': 'Web crawler not available'}
    
    async def _process_youtube(self, url: str) -> Dict[str, Any]:
        """Extract video info and transcript"""
        try:
            import yt_dlp
            
            opts = {
                'quiet': True,
                'no_warnings': True,
                'writesubtitles': True,
                'writeautomaticsub': True,
            }
            
            with yt_dlp.YoutubeDL(opts) as ydl:
                info = ydl.extract_info(url, download=False)
                
                return {
                    'title': info.get('title', ''),
                    'description': info.get('description', ''),
                    'duration': info.get('duration', 0),
                    'view_count': info.get('view_count', 0),
                    'url': url
                }
        except ImportError:
            return await self._process_webpage(url)
```

### Utilities Structure
```python
# utils/validators.py
from django.core.exceptions import ValidationError
from django.core.validators import URLValidator
from urllib.parse import urlparse
import mimetypes

class FileValidator:
    """Validate uploaded files"""
    
    MAX_FILE_SIZE = 100 * 1024 * 1024  # 100MB
    ALLOWED_TYPES = {
        'application/pdf',
        'text/plain',
        'text/markdown',
        'image/jpeg',
        'image/png',
        'video/mp4',
        'audio/mpeg',
        'audio/wav'
    }
    
    def validate_file(self, file):
        """Validate file size and type"""
        if file.size > self.MAX_FILE_SIZE:
            raise ValidationError(f"File too large: {file.size} bytes")
        
        if file.content_type not in self.ALLOWED_TYPES:
            raise ValidationError(f"Unsupported file type: {file.content_type}")
        
        return True

class URLValidator:
    """Validate URLs"""
    
    BLOCKED_DOMAINS = {'localhost', '127.0.0.1'}
    
    def __init__(self):
        self.django_validator = URLValidator()
    
    def validate_url(self, url: str):
        """Validate URL format and domain"""
        self.django_validator(url)
        
        parsed = urlparse(url)
        if parsed.netloc in self.BLOCKED_DOMAINS:
            raise ValidationError("Blocked domain")
        
        return True

# utils/storage.py
from django.conf import settings
from minio import Minio
from minio.error import S3Error
import io
import uuid

class StorageManager:
    """Handle file storage operations"""
    
    def __init__(self):
        self.client = Minio(
            endpoint=settings.MINIO_ENDPOINT,
            access_key=settings.MINIO_ACCESS_KEY,
            secret_key=settings.MINIO_SECRET_KEY,
            secure=settings.MINIO_USE_SSL
        )
        self.bucket_name = settings.MINIO_BUCKET_NAME
    
    def store_file(self, file_content: bytes, filename: str) -> str:
        """Store file and return object key"""
        object_key = f"{uuid.uuid4()}/{filename}"
        
        try:
            self.client.put_object(
                bucket_name=self.bucket_name,
                object_name=object_key,
                data=io.BytesIO(file_content),
                length=len(file_content)
            )
            return object_key
        except S3Error as e:
            raise Exception(f"Storage error: {e}")
    
    def get_file_url(self, object_key: str, expires: int = 3600) -> str:
        """Get pre-signed URL for file access"""
        try:
            return self.client.presigned_get_object(
                bucket_name=self.bucket_name,
                object_name=object_key,
                expires=timedelta(seconds=expires)
            )
        except S3Error as e:
            raise Exception(f"URL generation error: {e}")

# utils/helpers.py
import hashlib
import mimetypes
from typing import Dict, Any

def calculate_file_hash(file_content: bytes) -> str:
    """Calculate SHA256 hash of file content"""
    return hashlib.sha256(file_content).hexdigest()

def get_file_extension(filename: str) -> str:
    """Get file extension from filename"""
    return filename.split('.')[-1].lower() if '.' in filename else ''

def extract_metadata(file) -> Dict[str, Any]:
    """Extract metadata from uploaded file"""
    return {
        'filename': file.name,
        'size': file.size,
        'content_type': file.content_type,
        'extension': get_file_extension(file.name),
        'hash': calculate_file_hash(file.read())
    }
```

## Migration Strategy

### Backward Compatibility
1. Implement new architecture alongside existing code
2. Create adapter layers for existing endpoints
3. Gradually migrate endpoints to new architecture
4. Remove old code once migration is complete

### Testing Strategy
1. Comprehensive unit tests for all new services
2. Integration tests for use cases
3. End-to-end tests for critical workflows
4. Performance regression tests

## Benefits

### ✅ **Maintainability**
- **Small, focused files** - Easy to understand and modify
- **Clear responsibilities** - Each module has one job
- **Standard Django patterns** - Familiar to Django developers

### ✅ **Testability**  
- **Isolated components** - Test services independently
- **Mocked dependencies** - Easy to mock processors and storage
- **Django test framework** - Use built-in testing tools

### ✅ **Scalability**
- **Modular structure** - Add new file types or URL handlers easily
- **Background processing** - Celery tasks handle heavy operations
- **Caching support** - Django cache framework integration

### ✅ **Developer Experience**
- **Familiar Django patterns** - Uses ViewSets, serializers, services
- **Clear file organization** - Easy to find relevant code
- **Type hints** - Better IDE support and documentation

## URL Configuration

```python
# urls.py - Clean, focused URL patterns
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import notebook_views, file_views, url_views, chat_views

router = DefaultRouter()
router.register(r'', notebook_views.NotebookViewSet, basename='notebook')

urlpatterns = [
    path('', include(router.urls)),
    path('<str:notebook_id>/files/', file_views.FileUploadView.as_view(), name='file-upload'),
    path('<str:notebook_id>/urls/', url_views.URLProcessingView.as_view(), name='url-processing'),
    path('<str:notebook_id>/chat/', chat_views.ChatView.as_view(), name='chat'),
]
```

## Conclusion

This refactor addresses the core issues in the notebooks module:

- **Breaks down monolithic files** into manageable, focused modules
- **Uses standard Django patterns** that developers already know  
- **Maintains existing functionality** while improving structure
- **Enables incremental migration** with minimal risk
- **Follows Django best practices** throughout

**The result**: A clean, maintainable codebase that's easy to understand, test, and extend while leveraging Django's powerful built-in features. 