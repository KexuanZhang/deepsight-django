import os
import json
import time
import mimetypes
from uuid import uuid4
import asyncio
import logging
from asgiref.sync import sync_to_async, async_to_sync
from datetime import datetime
from pathlib import Path
from typing import Dict, Any
import traceback

logger = logging.getLogger(__name__)

from django.db import transaction
from django.http import StreamingHttpResponse, Http404, FileResponse
from django.shortcuts import get_object_or_404
from django.core.exceptions import PermissionDenied, ValidationError
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator

from rest_framework import status, permissions, authentication, generics
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, JSONParser
from rest_framework.decorators import action
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
import tempfile
import logging

from .models import Source, URLProcessingResult, KnowledgeItem, KnowledgeBaseItem, Notebook, BatchJob, BatchJobItem, NotebookChatMessage
from .serializers import (
    NotebookSerializer, 
    FileUploadSerializer, 
    URLParseSerializer, 
    URLParseWithMediaSerializer,
    URLParseDocumentSerializer,
    VideoImageExtractionSerializer,
    BatchURLParseSerializer,
    BatchURLParseWithMediaSerializer,
    BatchFileUploadSerializer,
    BatchJobSerializer,
    BatchJobItemSerializer
)
from .utils.upload_processor import UploadProcessor
from .utils.storage_adapter import get_storage_adapter
from .utils.url_extractor import URLExtractor
from .utils.media_extractor import MediaFeatureExtractor
from .utils.image_processing import clean_title
from .utils.view_mixins import (
    StandardAPIView,
    NotebookPermissionMixin,
    KnowledgeBasePermissionMixin,
    FileAccessValidatorMixin,
    PaginationMixin,
    FileListResponseMixin,
)
from rag.rag import (
    RAGChatbot, 
    SuggestionRAGAgent, 
    add_user_files, 
    add_user_content_documents,
    user_collection,
    ensure_user_collection,
)
from langchain_milvus import Milvus
from langchain_openai import OpenAIEmbeddings
from langchain.schema import Document
from pymilvus import Collection
from pymilvus.exceptions import SchemaNotReadyException, CollectionNotExistException
from backend.settings import MILVUS_COLLECTION_NAME
from .tasks import process_file_upload_task  # your Celery task
from PyPDF2 import PdfReader


upload_processor = UploadProcessor()
storage_adapter = get_storage_adapter()
url_extractor = URLExtractor()
media_extractor = MediaFeatureExtractor()

logger = logging.getLogger(__name__)

# class FileUploadView(NotebookPermissionMixin, APIView):
#     """Handle file uploads to notebooks - supports both single and batch uploads."""
#     parser_classes = [MultiPartParser]

#     def post(self, request, notebook_id):
#         try:
#             notebook = self.get_user_notebook(notebook_id, request.user)

#             batch_serializer = BatchFileUploadSerializer(data=request.data)
#             if batch_serializer.is_valid():
#                 validated = batch_serializer.validated_data
#                 if 'files' in validated:
#                     return self._handle_batch_file_upload(
#                         validated['files'], notebook, request.user
#                     )

#             serializer = FileUploadSerializer(data=request.data)
#             serializer.is_valid(raise_exception=True)
#             file_obj  = serializer.validated_data['file']
#             upload_id = serializer.validated_data.get('upload_file_id') or uuid4().hex

#             return self._handle_single_file_upload(
#                 file_obj, upload_id, notebook, request.user
#             )

#         except ValidationError as e:
#             return self.error_response(
#                 "File validation failed",
#                 status_code=status.HTTP_400_BAD_REQUEST,
#                 details={"error": str(e)},
#             )
#         except Exception as e:
#             logger.exception("File upload failed for notebook %s user %s", notebook_id, request.user.pk)
#             return Response(
#                 {"error": "File upload failed", "details": str(e)},
#                 status=status.HTTP_500_INTERNAL_SERVER_ERROR,
#             )

#     def _handle_single_file_upload(self, inbound_file, upload_id, notebook, user):
#         logger.info(f"Starting single file upload: user={user.pk}, notebook={notebook.id}, name={inbound_file.name}")
#         # 1) process & save to KnowledgeBaseItem
#         result = async_to_sync(upload_processor.process_upload)(
#             inbound_file, upload_id, user_pk=user.pk, notebook_id=notebook.id
#         )
#         kb_item = get_object_or_404(
#             KnowledgeBaseItem, id=result["file_id"], user=user
#         )

#         # 2) link in KnowledgeItem
#         source = Source.objects.create(
#             notebook=notebook,
#             source_type="file",
#             title=inbound_file.name,
#             needs_processing=False,
#             processing_status="done",
#         )
#         ki, created = KnowledgeItem.objects.get_or_create(
#             notebook=notebook,
#             knowledge_base_item=kb_item,
#             defaults={"source": source, "notes": f"Processed {inbound_file.name}"},
#         )
#         if not created and not ki.source:
#             ki.source = source
#             ki.save(update_fields=["source"])

#         # 3) embed into Milvus
#         coll_name = user_collection(user.pk)
#         from pymilvus import utility
#         first_time = not utility.has_collection(coll_name, using="default")
#         ensure_user_collection(coll_name)

#         # Build Document(s) depending on available content
#         docs = []
#         # 3a) Processed content file (md/txt)
#         if kb_item.file:
#             logger.debug("Reading processed file from S3: %s", kb_item.file.name)
#             # Read binary and decode since FileField.open() doesn't accept encoding
#             f = kb_item.file.open('rb')
#             raw = f.read()
#             text = raw.decode('utf-8')
#             docs.append(Document(
#                 page_content=text,
#                 metadata={"user_id": user.pk, "source": kb_item.file.name},
#             ))
#         # 3b) Inline text
#         elif kb_item.content:
#             logger.debug("Using inline content for KB item %s", kb_item.id)
#             docs.append(Document(
#                 page_content=kb_item.content,
#                 metadata={"user_id": user.pk, "source": "inline_content"},
#             ))
#         # 3c) Original PDF extraction
#         elif kb_item.original_file:
#             logger.debug("Downloading original file from S3: %s", kb_item.original_file.name)
#             tmp = tempfile.NamedTemporaryFile(delete=False, suffix='.pdf')
#             with kb_item.original_file.open('rb') as src:
#                 tmp.write(src.read())
#             tmp.flush()
#             tmp_path = tmp.name
#             tmp.close()

#             reader = PdfReader(tmp_path)
#             text = "\n".join(page.extract_text() or "" for page in reader.pages)
#             docs.append(Document(
#                 page_content=text,
#                 metadata={"user_id": user.pk, "source": kb_item.original_file.name},
#             ))
#         else:
#             logger.warning("No content found for KB item %s; skipping ingestion", kb_item.id)

#         # Ingest into Milvus if any docs
#         if docs:
#             add_user_content_documents(user.pk, docs)
#         else:
#             logger.info("Skipping Milvus ingestion for KB item %s (no docs)", kb_item.id)

#         return Response(
#             {
#                 "success": True,
#                 "file_id": kb_item.id,
#                 "knowledge_item_id": ki.id,
#                 "first_time": first_time,
#             },
#             status=status.HTTP_201_CREATED,
#         )

#     def _handle_batch_file_upload(self, files, notebook, user):
#         batch_job = BatchJob.objects.create(
#             notebook=notebook,
#             job_type='file_upload',
#             total_items=len(files),
#             status='processing',
#         )

#         for file_obj in files:
#             upload_id = uuid4().hex
#             data = file_obj.read()
#             file_obj.seek(0)

#             batch_item = BatchJobItem.objects.create(
#                 batch_job=batch_job,
#                 item_data={'filename': file_obj.name, 'size': len(data)},
#                 upload_id=upload_id,
#                 status='pending',
#             )

#             process_file_upload_task.delay(
#                 file_data=data,
#                 filename=file_obj.name,
#                 notebook_id=notebook.id,
#                 user_id=user.pk,
#                 upload_file_id=upload_id,
#                 batch_job_id=batch_job.id,
#                 batch_item_id=batch_item.id,
#             )

#         return Response(
#             {
#                 'success': True,
#                 'batch_job_id': batch_job.id,
#                 'total_items': len(files),
#                 'message': f'Batch upload started for {len(files)} files',
#             },
#             status=status.HTTP_202_ACCEPTED,
#         )
    

class FileUploadView(NotebookPermissionMixin, APIView):
    """Handle file uploads to notebooks - supports both single and batch uploads."""
    parser_classes = [MultiPartParser]

    def post(self, request, notebook_id):
        try:
            notebook = self.get_user_notebook(notebook_id, request.user)

            batch_serializer = BatchFileUploadSerializer(data=request.data)
            if batch_serializer.is_valid():
                validated = batch_serializer.validated_data
                if 'files' in validated:
                    return self._handle_batch_file_upload(validated['files'], notebook, request.user)
                # else fall‐through to single

            serializer = FileUploadSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            file_obj     = serializer.validated_data['file']
            upload_id    = serializer.validated_data.get('upload_file_id') or uuid4().hex
            return self._handle_single_file_upload(file_obj, upload_id, notebook, request.user)

        except ValidationError as e:
            return self.error_response(
                "File validation failed",
                status_code=status.HTTP_400_BAD_REQUEST,
                details={"error": str(e)},
            )
        except Exception as e:
            logger.exception(
                "Unhandled exception in FileUploadView POST for notebook %s: %s",
                notebook_id, e
            )
            # Optionally, also log the raw traceback
            logger.error("Traceback:\n%s", traceback.format_exc())

            return Response(
                {
                    "error": "File upload failed",
                    "details": str(e),
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


    def _handle_single_file_upload(self, inbound_file, upload_id, notebook, user):
        # 1) process & save to KnowledgeBaseItem
        result = async_to_sync(upload_processor.process_upload)(
            inbound_file, upload_id, user_pk=user.pk, notebook_id=notebook.id
        )
        kb_item = get_object_or_404(KnowledgeBaseItem, id=result["file_id"], user=user)

        # 2) create or update the link in KnowledgeItem
        source = Source.objects.create(
            notebook=notebook,
            source_type="file",
            title=inbound_file.name,
            needs_processing=False,
            processing_status="done",
        )
        ki, created = KnowledgeItem.objects.get_or_create(
            notebook=notebook,
            knowledge_base_item=kb_item,
            defaults={"source": source, "notes": f"Processed {inbound_file.name}"}
        )
        if not created and not ki.source:
            ki.source = source
            ki.save(update_fields=["source"])
        
        print("!!!kb item", kb_item)
        
        add_user_files(
            user_id=user.pk,
            kb_items=[kb_item],
        )

        return Response({
            "success": True,
            "file_id": kb_item.id,
            "knowledge_item_id": ki.id,
            # "first_time": existing == 0,
        }, status=status.HTTP_201_CREATED)

    def _handle_batch_file_upload(self, files, notebook, user):
        # create batch job
        batch_job = BatchJob.objects.create(
            notebook=notebook, job_type='file_upload',
            total_items=len(files), status='processing'
        )

        for file_obj in files:
            upload_id = uuid4().hex
            data = file_obj.read()
            file_obj.seek(0)

            batch_item = BatchJobItem.objects.create(
                batch_job=batch_job,
                item_data={'filename': file_obj.name, 'size': len(data)},
                upload_id=upload_id,
                status='pending'
            )

            # enqueue a Celery task that will:
            # 1) call upload_processor.process_upload
            # 2) link the KB item (like above)
            # 3) call add_user_files(user.pk, [new_file_path])
            process_file_upload_task.delay(
                file_data=data,
                filename=file_obj.name,
                notebook_id=notebook.id,
                user_id=user.pk,
                upload_file_id=upload_id,
                batch_job_id=batch_job.id,
                batch_item_id=batch_item.id
            )

        return Response(
            {
                'success': True,
                'batch_job_id': batch_job.id,
                'total_items': len(files),
                'message': f'Batch upload started for {len(files)} files'
            },
            status=status.HTTP_202_ACCEPTED
        )


class URLParseView(StandardAPIView, NotebookPermissionMixin):
    """Handle URL parsing without media extraction - supports both single and batch processing."""
    
    parser_classes = [JSONParser]

    def post(self, request, notebook_id):
        """Parse URL content using crawl4ai only - supports single URL or multiple URLs."""
        try:
            # Verify notebook access
            notebook = self.get_user_notebook(notebook_id, request.user)
            
            # Try batch serializer first
            batch_serializer = BatchURLParseSerializer(data=request.data)
            if batch_serializer.is_valid():
                validated_data = batch_serializer.validated_data
                
                # Check if this is a batch request (multiple URLs)
                if 'urls' in validated_data:
                    return self._handle_batch_url_parse(validated_data, notebook, request.user)
                else:
                    # Single URL - convert to single URL format for backward compatibility
                    url = validated_data.get('url')
                    upload_url_id = validated_data.get('upload_url_id', uuid4().hex)
                    return self._handle_single_url_parse(url, upload_url_id, notebook, request.user)
            
            # Fallback to original serializer for backward compatibility
            serializer = URLParseSerializer(data=request.data)
            if not serializer.is_valid():
                return self.error_response(
                    "Invalid request data", 
                    details=serializer.errors
                )
            
            # Handle single URL with original logic
            url = serializer.validated_data["url"]
            upload_url_id = serializer.validated_data.get("upload_url_id") or uuid4().hex
            return self._handle_single_url_parse(url, upload_url_id, notebook, request.user)

        except Exception as e:
            return self.error_response(
                "URL parsing failed",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                details={"error": str(e)},
            )
    
    def _handle_single_url_parse(self, url, upload_url_id, notebook, user):
        """Handle single URL parsing (original behavior)."""
        # Process the URL using async function
        async def process_url_async():
            return await url_extractor.process_url(
                url=url,
                upload_url_id=upload_url_id,
                user_id=user.pk,
                notebook_id=notebook.id
            )

        # Run async processing using async_to_sync
        result = async_to_sync(process_url_async)()

        # Create source record
        source = Source.objects.create(
            notebook=notebook,
            source_type="url",
            title=url,
            needs_processing=False,
            processing_status="done",
        )

        # Create URL processing result
        URLProcessingResult.objects.create(
            source=source,
            content_md=result.get("content_preview", ""),
        )

        # Link to knowledge base
        kb_item_id = result['file_id']
        kb_item = get_object_or_404(KnowledgeBaseItem, id=kb_item_id, user=user)
        
        ki, created = KnowledgeItem.objects.get_or_create(
            notebook=notebook,
            knowledge_base_item=kb_item,
            defaults={
                'source': source,
                'notes': f"Processed from URL: {url}"
            }
        )

        return Response(
            {
                "success": True,
                "file_id": kb_item_id,
                "knowledge_item_id": ki.id,
                "url": result.get("url", url),
                "title": result.get("title", ""),
                "extraction_method": result.get("extraction_method", "crawl4ai"),
                "content_preview": result.get("content_preview", ""),
            },
            status=status.HTTP_201_CREATED,
        )
    
    def _handle_batch_url_parse(self, validated_data, notebook, user):
        """Handle batch URL parsing using Celery."""
        from .tasks import process_url_task
        
        urls = validated_data['urls']
        
        # Create batch job
        batch_job = BatchJob.objects.create(
            notebook=notebook,
            job_type='url_parse',
            total_items=len(urls),
            status='processing'
        )
        
        # Create batch items and queue Celery tasks
        batch_items = []
        for url in urls:
            upload_url_id = uuid4().hex
            
            # Create batch item
            batch_item = BatchJobItem.objects.create(
                batch_job=batch_job,
                item_data={'url': url},
                upload_id=upload_url_id,
                status='pending'
            )
            batch_items.append(batch_item)
            
            # Queue Celery task
            process_url_task.delay(
                url=url,
                notebook_id=notebook.id,
                user_id=user.pk,
                upload_url_id=upload_url_id,
                batch_job_id=batch_job.id,
                batch_item_id=batch_item.id
            )
        
        return Response({
            'success': True,
            'batch_job_id': batch_job.id,
            'total_items': len(urls),
            'message': f'Batch processing started for {len(urls)} URLs'
        }, status=status.HTTP_202_ACCEPTED)


class URLParseWithMediaView(StandardAPIView, NotebookPermissionMixin):
    """Handle URL parsing for media content only using faster-whisper transcription - supports both single and batch processing.
    
    This endpoint specifically processes URLs with downloadable media (audio/video)
    and does NOT fallback to web scraping if media processing fails.
    Uses faster-whisper model for transcription, same as DeepSight project.
    """
    
    parser_classes = [JSONParser]

    def post(self, request, notebook_id):
        """Parse URL media content using yt-dlp and faster-whisper - supports single URL or multiple URLs."""
        try:
            # Verify notebook access
            notebook = self.get_user_notebook(notebook_id, request.user)
            
            # Try batch serializer first
            batch_serializer = BatchURLParseWithMediaSerializer(data=request.data)
            if batch_serializer.is_valid():
                validated_data = batch_serializer.validated_data
                
                # Check if this is a batch request (multiple URLs)
                if 'urls' in validated_data:
                    return self._handle_batch_url_media_parse(validated_data, notebook, request.user)
                else:
                    # Single URL - convert to single URL format for backward compatibility
                    url = validated_data.get('url')
                    upload_url_id = validated_data.get('upload_url_id', uuid4().hex)
                    return self._handle_single_url_media_parse(url, upload_url_id, notebook, request.user)
            
            # Fallback to original serializer for backward compatibility
            serializer = URLParseWithMediaSerializer(data=request.data)
            if not serializer.is_valid():
                return self.error_response(
                    "Invalid request data", 
                    details=serializer.errors
                )
            
            # Handle single URL with original logic
            url = serializer.validated_data["url"]
            upload_url_id = serializer.validated_data.get("upload_url_id") or uuid4().hex
            return self._handle_single_url_media_parse(url, upload_url_id, notebook, request.user)

        except Exception as e:
            return self.error_response(
                "URL media parsing failed",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                details={"error": str(e)},
            )
    
    def _handle_single_url_media_parse(self, url, upload_url_id, notebook, user):
        """Handle single URL media parsing (original behavior)."""
        # Process the URL using async function
        async def process_url_media_only_async():
            return await url_extractor.process_url_media_only(
                url=url,
                upload_url_id=upload_url_id,
                user_id=user.pk,
                notebook_id=notebook.id
            )

        # Run async processing using async_to_sync
        result = async_to_sync(process_url_media_only_async)()

        # Create source record
        source = Source.objects.create(
            notebook=notebook,
            source_type="url",
            title=url,
            needs_processing=False,
            processing_status="done",
        )

        # Create URL processing result
        URLProcessingResult.objects.create(
            source=source,
            content_md=result.get("content_preview", ""),
        )

        # Link to knowledge base
        kb_item_id = result['file_id']
        kb_item = get_object_or_404(KnowledgeBaseItem, id=kb_item_id, user=user)
        
        ki, created = KnowledgeItem.objects.get_or_create(
            notebook=notebook,
            knowledge_base_item=kb_item,
            defaults={
                'source': source,
                'notes': f"Processed from URL with media: {url}"
            }
        )

        return Response(
            {
                "success": True,
                "file_id": kb_item_id,
                "knowledge_item_id": ki.id,
                "url": result.get("url", url),
                "title": result.get("title", ""),
                "has_media": result.get("has_media", True),
                "processing_type": result.get("processing_type", "media"),
                "content_preview": result.get("content_preview", ""),
            },
            status=status.HTTP_201_CREATED,
        )
    
    def _handle_batch_url_media_parse(self, validated_data, notebook, user):
        """Handle batch URL media parsing using Celery."""
        from .tasks import process_url_media_task
        
        urls = validated_data['urls']
        
        # Create batch job
        batch_job = BatchJob.objects.create(
            notebook=notebook,
            job_type='url_parse_media',
            total_items=len(urls),
            status='processing'
        )
        
        # Create batch items and queue Celery tasks
        batch_items = []
        for url in urls:
            upload_url_id = uuid4().hex
            
            # Create batch item
            batch_item = BatchJobItem.objects.create(
                batch_job=batch_job,
                item_data={'url': url},
                upload_id=upload_url_id,
                status='pending'
            )
            batch_items.append(batch_item)
            
            # Queue Celery task
            process_url_media_task.delay(
                url=url,
                notebook_id=notebook.id,
                user_id=user.pk,
                upload_url_id=upload_url_id,
                batch_job_id=batch_job.id,
                batch_item_id=batch_item.id
            )
        
        return Response({
            'success': True,
            'batch_job_id': batch_job.id,
            'total_items': len(urls),
            'message': f'Batch media processing started for {len(urls)} URLs'
        }, status=status.HTTP_202_ACCEPTED)


class URLParseDocumentView(StandardAPIView, NotebookPermissionMixin):
    """Parse document URLs and validate file format (PDF/PPTX only)."""

    parser_classes = [JSONParser]

    def post(self, request, notebook_id):
        """Parse a document URL and validate its format."""
        try:
            # Verify notebook access
            notebook = self.get_user_notebook(notebook_id, request.user)
            
            # Validate input
            serializer = URLParseDocumentSerializer(data=request.data)
            if not serializer.is_valid():
                return self.error_response(
                    "Invalid input data",
                    details=serializer.errors,
                    status_code=status.HTTP_400_BAD_REQUEST
                )
            
            validated_data = serializer.validated_data
            url = validated_data['url']
            upload_url_id = validated_data.get('upload_url_id')
            
            # Process document URL asynchronously
            result = async_to_sync(url_extractor.process_url_document_only)(
                url=url,
                upload_url_id=upload_url_id,
                user_id=request.user.pk,
                notebook_id=notebook.id
            )
            
            return Response({
                'success': True,
                'file_id': result['file_id'],
                'url': result['url'],
                'status': result['status'],
                'title': result['title'],
                'processing_type': result['processing_type'],
                'file_extension': result['file_extension'],
                'file_size': result['file_size'],
                'content_preview': result.get('content_preview', ''),
                'upload_url_id': upload_url_id
            }, status=status.HTTP_201_CREATED)
            
        except ValueError as e:
            # File format validation errors - provide user-friendly messages
            error_msg = str(e)
            if "Invalid document format" in error_msg:
                if "text/html" in error_msg:
                    error_msg = "This URL points to a webpage, not a document file. Please use a direct link to a PDF or PowerPoint file instead."
                elif "Unknown" in error_msg:
                    error_msg = "This URL does not point to a valid PDF or PowerPoint file. Please check the URL and ensure it links directly to a document file."
                else:
                    error_msg = f"Invalid file format. The document URL processor only accepts PDF and PowerPoint files. {error_msg}"
            elif "Invalid URL" in error_msg:
                error_msg = "Please enter a valid URL that starts with http:// or https://"
            
            return self.error_response(
                error_msg,
                status_code=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            # Other processing errors (download failures, etc.)
            import traceback
            logger.error(f"Document URL processing failed for {validated_data.get('url', 'unknown URL')}: {str(e)}")
            logger.error(f"Full traceback: {traceback.format_exc()}")
            
            # Provide user-friendly error messages for common issues
            error_msg = str(e)
            if "Failed to download document" in error_msg:
                if "HTTP 404" in error_msg:
                    error_msg = "Document not found at this URL. Please check the URL and try again."
                elif "HTTP 403" in error_msg:
                    error_msg = "Access denied. The document may require authentication or may not be publicly accessible."
                else:
                    error_msg = "Unable to download the document from this URL. Please check if the URL is accessible and try again."
            elif "connection" in error_msg.lower() or "timeout" in error_msg.lower():
                error_msg = "Network connection issue. Please check your internet connection and try again."
            elif "You cannot call this from an async context" in error_msg:
                error_msg = "Internal server error. Please try again in a moment."
            else:
                error_msg = f"Failed to process document URL: {error_msg}"
            
            return self.error_response(
                error_msg,
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class FileListView(StandardAPIView, NotebookPermissionMixin, FileListResponseMixin):
    """List all knowledge items linked to a notebook."""

    def get(self, request, notebook_id):
        """Get all files linked to the notebook."""
        try:
            # Verify notebook access
            notebook = self.get_user_notebook(notebook_id, request.user)

            # Get all KnowledgeItems for this notebook with optimized query
            knowledge_items = (
                KnowledgeItem.objects.filter(notebook=notebook)
                .select_related("knowledge_base_item", "source", "source__url_result")
                .order_by("-added_at")
            )

            # Build response data using mixin
            files = [self.build_file_response_data(ki) for ki in knowledge_items]

            return self.success_response(files)

        except Exception as e:
            return self.error_response(
                "Failed to retrieve files",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                details={"error": str(e)},
            )


class RAGChatFromKBView(NotebookPermissionMixin, APIView):
    """
    POST /api/v1/notebooks/{notebook_id}/chat/
    {
      "question":       "Explain quantum tunneling",
      "mode":           "local"|"global"|"hybrid",
      "filter_sources": ["paper1.pdf","notes.md"]
    }
    """
    def post(self, request, notebook_id):
        question       = request.data.get("question")
        mode           = request.data.get("mode", "hybrid")
        filter_sources = request.data.get("filter_sources", None)

        # 1) validate inputs
        if not question:
            return Response(
                {"error": "Question is required."},
                status=status.HTTP_400_BAD_REQUEST
            )
        if mode not in ("local", "global", "hybrid"):
            return Response(
                {"error": f"Invalid mode '{mode}'."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # 2) fetch & authorize
        try:
            notebook = self.get_user_notebook(notebook_id, request.user)
        except:
            return Response({"error": "Notebook not found."}, status=status.HTTP_404_NOT_FOUND)

        # 3) ensure there are files
        # kb_qs = KnowledgeBaseItem.objects.filter(
        #     notebook_links__notebook=notebook,
        #     user=request.user,
        #     file__isnull=False
        # ).exclude(file="").distinct()
        # if not kb_qs.exists():
        #     return Response({"error": "No valid documents in this notebook."},
        #                     status=status.HTTP_404_NOT_FOUND)

        # file_paths = [item.file.path for item in kb_qs if hasattr(item.file, "path")]
        # if not file_paths:
        #     return Response({"error": "No file paths available."},
        #                     status=status.HTTP_404_NOT_FOUND)

        # 4) verify user's Milvus collection exists & has data
        user_id  = request.user.pk
        coll_name = user_collection(user_id)
        try:
            coll     = Collection(coll_name)
            existing = coll.num_entities
        except (CollectionNotExistException, SchemaNotReadyException):
            existing = 0

        if existing == 0:
            return Response(
                {"error": "Your knowledge base is empty. Please upload files first."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # 5) load chat history and record user question
        history = list(
            NotebookChatMessage.objects
                .filter(notebook=notebook)
                .order_by("timestamp")
                .values_list("sender", "message")
        )
        NotebookChatMessage.objects.create(
            notebook=notebook, sender="user", message=question
        )

        # 6) get the chatbot singleton
        bot = RAGChatbot(user_id=user_id)

        # 7) wrap the SSE stream to capture assistant tokens
        raw_stream = bot.stream(
            question=question,
            history=history,
            mode=mode,
            filter_sources=filter_sources
        )

        def wrapped_stream():
            buffer = []
            for chunk in raw_stream:
                yield chunk
                # parse only token events
                if chunk.startswith("data: "):
                    payload = json.loads(chunk[len("data: "):])
                    if payload.get("type") == "token":
                        buffer.append(payload.get("text", ""))
                # ignore metadata and done
            # once stream finishes, save the full assistant response
            full_response = "".join(buffer).strip()
            if full_response:
                NotebookChatMessage.objects.create(
                    notebook=notebook,
                    sender="assistant",
                    message=full_response
                )

        return StreamingHttpResponse(
            wrapped_stream(),
            content_type="text/event-stream",
        )


class ChatHistoryView(StandardAPIView, NotebookPermissionMixin):
    
    def get(self, request, notebook_id):
        try:
            notebook = self.get_user_notebook(notebook_id, request.user)
        except Exception as e:
            return Response({"error": "Notebook not found"}, status=404)
        
        messages = NotebookChatMessage.objects.filter(notebook=notebook).order_by("timestamp")
        history = []
        for message in messages:
            history.append({"id": message.id, "sender": message.sender, "message": message.message, "timestamp": message.timestamp})
        return Response({"history": history})
    

class ClearChatHistoryView(StandardAPIView, NotebookPermissionMixin):

    def delete(self, request, notebook_id):
        try:
            notebook = self.get_user_notebook(notebook_id, request.user)
        except Exception as e:
            return Response({"error": "Notebook not found"}, status=404)
        NotebookChatMessage.objects.filter(notebook=notebook).delete()
        return Response({"success": True, "message": "Chat history cleared"})
    
class SuggestedQuestionsView(StandardAPIView, NotebookPermissionMixin):

    def get(self, request, notebook_id):
        try:
            notebook = Notebook.objects.get(id=notebook_id, user=request.user)
            history = NotebookChatMessage.objects.filter(notebook=notebook).order_by("timestamp")
            history_text = "\n".join([f"{msg.sender}: {msg.message}" for msg in history])

            agent = SuggestionRAGAgent()  # see below
            suggestions = agent.generate_suggestions(history_text)

            return Response({"suggestions": suggestions})
        except Exception as e:
            return Response({"error": str(e)}, status=400)


class KnowledgeBaseView(StandardAPIView, NotebookPermissionMixin, PaginationMixin):
    """Manage user's knowledge base items."""

    parser_classes = [JSONParser, MultiPartParser]

    def get(self, request, notebook_id):
        """Get user's entire knowledge base with linkage status."""
        try:
            # Verify notebook ownership
            notebook = self.get_user_notebook(notebook_id, request.user)

            # Get query parameters
            content_type = request.GET.get("content_type")
            limit, offset = self.get_pagination_params(request)

            # Get knowledge base items
            knowledge_base = storage_adapter.get_user_knowledge_base(
                user_id=request.user.pk,
                content_type=content_type,
                limit=limit,
                offset=offset,
            )

            # Check which items are already linked to this notebook
            linked_kb_item_ids = set(
                KnowledgeItem.objects.filter(notebook=notebook).values_list(
                    "knowledge_base_item_id", flat=True
                )
            )

            # Add linked status to each item
            for item in knowledge_base:
                item["linked_to_notebook"] = item["id"] in linked_kb_item_ids

            return self.success_response(
                {
                    "items": knowledge_base,
                    "notebook_id": notebook_id,
                    "pagination": {"limit": limit, "offset": offset},
                }
            )

        except Exception as e:
            return self.error_response(
                "Failed to retrieve knowledge base",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                details={"error": str(e)},
            )

    def post(self, request, notebook_id):
        """Link a knowledge base item to this notebook."""
        try:
            # Verify notebook ownership
            notebook = self.get_user_notebook(notebook_id, request.user)

            # Validate request data
            kb_item_id = request.data.get("knowledge_base_item_id")
            notes = request.data.get("notes", "")

            if not kb_item_id:
                return self.error_response("knowledge_base_item_id is required")

            # Link the item
            success = storage_adapter.link_knowledge_item_to_notebook(
                kb_item_id=kb_item_id,
                notebook_id=notebook_id,
                user_id=request.user.pk,
                notes=notes,
            )

            if success:
                return self.success_response({"linked": True})
            else:
                return self.error_response("Failed to link knowledge item")

        except Exception as e:
            return self.error_response(
                "Link operation failed",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                details={"error": str(e)},
            )

    def delete(self, request, notebook_id):
        """Delete a knowledge base item entirely from user's knowledge base."""
        try:
            # Verify notebook ownership (for permission check)
            self.get_user_notebook(notebook_id, request.user)

            # Validate request data
            kb_item_id = request.data.get("knowledge_base_item_id")
            if not kb_item_id:
                return self.error_response("knowledge_base_item_id is required")

            # Delete the knowledge base item entirely
            success = storage_adapter.delete_knowledge_base_item(
                kb_item_id, request.user.pk
            )

            if success:
                return Response(status=status.HTTP_204_NO_CONTENT)
            else:
                return self.error_response(
                    "Knowledge base item not found or access denied",
                    status_code=status.HTTP_404_NOT_FOUND,
                )

        except Exception as e:
            return self.error_response(
                "Delete operation failed",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                details={"error": str(e)},
            )


class FileStatusView(APIView):
    """
    GET /api/notebooks/{notebook_id}/files/{upload_file_id}/status/
    Return a one‐time snapshot of parsing status, or 404 if unknown.
    """

    permission_classes = [permissions.IsAuthenticated]
    authentication_classes = [authentication.SessionAuthentication]

    def get(self, request, notebook_id, upload_file_id):
        # verify notebook ownership
        if not Notebook.objects.filter(id=notebook_id, user=request.user).exists():
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)

        status_obj = upload_processor.get_upload_status(upload_file_id, request.user.pk)
        if not status_obj:
            return Response(
                {"detail": "Status not found."}, status=status.HTTP_404_NOT_FOUND
            )
        return Response({"success": True, **status_obj})


class FileStatusStreamView(APIView):
    """
    GET /api/notebooks/{notebook_id}/files/{upload_file_id}/status/stream
    Server-Sent Events streaming endpoint for real-time upload status updates.
    """

    permission_classes = [permissions.IsAuthenticated]
    authentication_classes = [authentication.SessionAuthentication]

    def get(self, request, notebook_id, upload_file_id):
        # Verify notebook ownership
        if not Notebook.objects.filter(id=notebook_id, user=request.user).exists():
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)

        def event_stream():
            """Generator function for SSE events"""
            max_duration = 300  # 5 minutes maximum
            start_time = time.time()
            poll_interval = 2  # Check every 2 seconds

            while time.time() - start_time < max_duration:
                try:
                    # Get current status synchronously
                    status_obj = upload_processor.get_upload_status(
                        upload_file_id, request.user.pk
                    )

                    if status_obj:
                        # Send status update as SSE event
                        event_data = {
                            "status": status_obj.get("status", "unknown"),
                            "job_details": {
                                "progress_percentage": status_obj.get(
                                    "progress_percentage", 0
                                ),
                                "result": status_obj.get("metadata", {}),
                                "error": status_obj.get("error"),
                            },
                        }

                        yield f"data: {json.dumps(event_data)}\n\n"

                        # If upload is complete, send final event and close
                        if status_obj.get("status") in [
                            "completed",
                            "error",
                            "cancelled",
                            "unsupported",
                        ]:
                            break
                    else:
                        # No status found, might be completed or doesn't exist
                        yield f"data: {json.dumps({'status': 'not_found', 'job_details': {}})}\n\n"
                        break

                except Exception as e:
                    # Send error event
                    error_data = {"status": "error", "job_details": {"error": str(e)}}
                    yield f"data: {json.dumps(error_data)}\n\n"
                    break

                # Wait before next poll
                time.sleep(poll_interval)

            # Send final close event
            yield f"data: {json.dumps({'status': 'stream_closed', 'job_details': {}})}\n\n"

        response = StreamingHttpResponse(
            event_stream(), content_type="text/event-stream"
        )
        response["Cache-Control"] = "no-cache"
        response["Connection"] = "keep-alive"
        response["Access-Control-Allow-Origin"] = "*"
        response["Access-Control-Allow-Headers"] = "Cache-Control"

        return response


class FileDeleteView(APIView):
    """
    DELETE /api/notebooks/{notebook_id}/files/{file_or_upload_id}/
    Delete a knowledge item link from notebook or delete from knowledge base entirely.
    """

    permission_classes = [permissions.IsAuthenticated]
    authentication_classes = [authentication.SessionAuthentication]

    def delete(self, request, notebook_id, file_or_upload_id):
        # verify notebook ownership
        notebook = get_object_or_404(Notebook, id=notebook_id, user=request.user)

        force_delete = request.GET.get("force", "false").lower() == "true"

        deleted = False

        # Strategy 1: Try to find by knowledge_item_id (direct database ID)
        if not deleted:
            try:
                # Try as UUID string directly (no int conversion needed)
                ki = KnowledgeItem.objects.filter(
                    id=file_or_upload_id, notebook=notebook
                ).first()

                if ki:
                    if force_delete:
                        # Delete the knowledge base item entirely
                        success = storage_adapter.delete_knowledge_base_item(
                            str(ki.knowledge_base_item.id), request.user.pk
                        )
                        if success:
                            deleted = True
                    else:
                        # Just delete the link
                        ki.delete()
                        deleted = True
            except Exception:
                pass  # Not a valid UUID or other error

        # Strategy 2: Try to find by knowledge_base_item_id (UUID string)
        if not deleted:
            try:
                # Try as UUID string directly (no int conversion needed)
                ki = KnowledgeItem.objects.filter(
                    notebook=notebook, knowledge_base_item_id=file_or_upload_id
                ).first()

                if ki:
                    if force_delete:
                        # Delete the knowledge base item entirely
                        success = storage_adapter.delete_knowledge_base_item(
                            str(kb_item_id), request.user.pk
                        )
                        if success:
                            deleted = True
                    else:
                        # Just unlink from this notebook
                        success = storage_adapter.unlink_knowledge_item_from_notebook(
                            str(kb_item_id), notebook_id, request.user.pk
                        )
                        if success:
                            deleted = True
            except (ValueError, TypeError):
                pass  # Not a valid integer ID

        # Strategy 3: Handle upload IDs by searching in metadata
        if not deleted and str(file_or_upload_id).startswith("upload_"):
            try:
                # Find knowledge items in this notebook that have the upload ID in metadata
                knowledge_items = KnowledgeItem.objects.filter(
                    notebook=notebook
                ).select_related("knowledge_base_item", "source")

                for ki in knowledge_items:
                    kb_item = ki.knowledge_base_item
                    source = ki.source

                    # Check if this knowledge item is related to the upload ID
                    upload_id_match = False

                    # Check metadata for upload ID references
                    if kb_item.metadata and isinstance(kb_item.metadata, dict):
                        metadata_str = str(kb_item.metadata)
                        if file_or_upload_id in metadata_str:
                            upload_id_match = True

                    # Check source metadata if available (legacy upload system - commented out)
                    # if source and hasattr(source, "upload") and source.upload:
                    #     # Check if source file contains the upload ID pattern
                    #     if file_or_upload_id in str(source.upload.file.name):
                    #         upload_id_match = True

                    if upload_id_match:
                        if force_delete:
                            # Delete the knowledge base item entirely
                            success = storage_adapter.delete_knowledge_base_item(
                                str(kb_item.id), request.user.pk
                            )
                            if success:
                                deleted = True
                                break
                        else:
                            # Just delete the link
                            ki.delete()
                            deleted = True
                            break

            except Exception as e:
                print(f"Error handling upload ID {file_or_upload_id}: {e}")

        # Strategy 4: Legacy fallback - try as string knowledge base item ID
        if not deleted:
            try:
                # Some systems might pass KB item IDs as strings
                ki = KnowledgeItem.objects.filter(
                    notebook=notebook, knowledge_base_item_id=file_or_upload_id
                ).first()

                if ki:
                    if force_delete:
                        # Delete the knowledge base item entirely
                        success = storage_adapter.delete_knowledge_base_item(
                            str(ki.knowledge_base_item.id), request.user.pk
                        )
                        if success:
                            deleted = True
                    else:
                        # Just delete the link
                        ki.delete()
                        deleted = True

            except Exception as e:
                print(f"Error in legacy fallback for {file_or_upload_id}: {e}")

        if deleted:
            return Response(status=status.HTTP_204_NO_CONTENT)
        else:
            return Response(
                {"detail": "File not found."}, status=status.HTTP_404_NOT_FOUND
            )


class NotebookListCreateAPIView(generics.ListCreateAPIView):
    """
    GET  /api/notebooks/      → list all notebooks for request.user
    POST /api/notebooks/      → create a new notebook for request.user
    """

    serializer_class = NotebookSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        # Only the current user's notebooks
        print(self.request.user)
        return Notebook.objects.filter(user=self.request.user).order_by("-created_at")

    def perform_create(self, serializer):
        # Auto-assign the creating user
        print(self.request.user)
        serializer.save(user=self.request.user)


class NotebookRetrieveUpdateDestroyAPIView(generics.RetrieveUpdateDestroyAPIView):
    """
    GET    /api/notebooks/{pk}/   → retrieve a notebook
    PUT    /api/notebooks/{pk}/   → update name & description
    PATCH  /api/notebooks/{pk}/   → partial update
    DELETE /api/notebooks/{pk}/   → delete the notebook
    """

    serializer_class = NotebookSerializer
    permission_classes = [permissions.IsAuthenticated]
    authentication_classes = [authentication.SessionAuthentication]

    def get_queryset(self):
        # Users can only operate on their own notebooks
        return Notebook.objects.filter(user=self.request.user)


class FileContentView(StandardAPIView, KnowledgeBasePermissionMixin):
    """Serve parsed content from knowledge base items."""

    def get(self, request, file_id):
        """Get processed content for a knowledge base item."""
        try:
            # Get the knowledge base item (verifies ownership)
            kb_item = self.get_user_kb_item(file_id, request.user)

            # Get content from storage service
            content = storage_adapter.get_file_content(file_id, user_id=request.user.pk)

            if content is None:
                return self.error_response(
                    "Content not found or not accessible",
                    status_code=status.HTTP_404_NOT_FOUND,
                )

            return self.success_response(
                {
                    "content": content,
                    "title": kb_item.title,
                    "content_type": kb_item.content_type,
                    "metadata": kb_item.metadata or {},
                }
            )

        except Exception as e:
            return self.error_response(
                "Failed to retrieve content",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                details={"error": str(e)},
            )


@method_decorator(csrf_exempt, name="dispatch")
class FileRawView(StandardAPIView, FileAccessValidatorMixin):
    """Serve raw file content (PDFs, videos, audio, etc.)."""

    def get(self, request, notebook_id, file_id):
        """Serve raw file through notebook context."""
        try:
            # Validate access through notebook
            notebook, kb_item, knowledge_item = self.validate_notebook_file_access(
                notebook_id, file_id, request.user
            )

            # Try to serve original file first
            if kb_item.original_file_object_key:
                return self._serve_minio_file(kb_item.original_file_object_key, kb_item.title)

            # Fallback to processed file
            if kb_item.file_object_key:
                return self._serve_minio_file(kb_item.file_object_key, kb_item.title)

            raise Http404("Raw file not found")

        except PermissionDenied as e:
            return self.error_response(str(e), status_code=status.HTTP_403_FORBIDDEN)
        except Http404 as e:
            return self.error_response(str(e), status_code=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return self.error_response(
                "File access failed",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                details={"error": str(e)},
            )

    def _serve_minio_file(self, object_key, title):
        """Serve a file from MinIO through Django's FileResponse."""
        try:
            from .utils.minio_backend import get_minio_backend
            from io import BytesIO
            
            minio_backend = get_minio_backend()
            file_content = minio_backend.get_file_content(object_key)
            
            # Guess content type from the title/filename
            content_type, _ = mimetypes.guess_type(title)
            if not content_type:
                content_type = "application/octet-stream"

            # Create a BytesIO stream from the content
            file_stream = BytesIO(file_content)
            
            response = FileResponse(
                file_stream, content_type=content_type, as_attachment=False
            )
            response["Content-Disposition"] = f'inline; filename="{title}"'
            response["X-Content-Type-Options"] = "nosniff"
            response["X-Frame-Options"] = "DENY"
            return response
        except Exception as e:
            raise Http404(f"File not accessible: {str(e)}")


@method_decorator(csrf_exempt, name="dispatch")
class FileRawSimpleView(StandardAPIView, KnowledgeBasePermissionMixin):
    """Serve raw file content without requiring notebook context."""

    def get(self, request, file_id):
        """Serve raw file directly by knowledge base item ID."""
        try:
            # Get the knowledge base item (verifies ownership)
            kb_item = self.get_user_kb_item(file_id, request.user)

            # Try to serve original file first
            if kb_item.original_file_object_key:
                file_url = kb_item.get_original_file_url()
                if file_url:
                    return Response({"file_url": file_url}, status=status.HTTP_200_OK)

            # Fallback to processed file
            if kb_item.file_object_key:
                file_url = kb_item.get_file_url()
                if file_url:
                    return Response({"file_url": file_url}, status=status.HTTP_200_OK)

            raise Http404("Raw file not found")

        except Http404 as e:
            return self.error_response(str(e), status_code=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return self.error_response(
                "File access failed",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                details={"error": str(e)},
            )

    def _serve_minio_file(self, object_key, title):
        """Helper to serve a file from MinIO with proper headers."""
        try:
            from .utils.minio_backend import get_minio_backend
            from io import BytesIO
            
            minio_backend = get_minio_backend()
            file_content = minio_backend.get_file_content(object_key)
            
            # Guess content type from the title/filename
            content_type, _ = mimetypes.guess_type(title)
            if not content_type:
                content_type = "application/octet-stream"

            # Create a BytesIO stream from the content
            file_stream = BytesIO(file_content)
            
            response = FileResponse(
                file_stream, content_type=content_type, as_attachment=False
            )
            response["Content-Disposition"] = f'inline; filename="{title}"'
            response["X-Content-Type-Options"] = "nosniff"
            response["X-Frame-Options"] = "DENY"
            return response
        except Exception as e:
            raise Http404(f"File not accessible: {str(e)}")


class VideoImageExtractionView(StandardAPIView, NotebookPermissionMixin):
    """Handle video image extraction with deduplication and captioning for notebook files."""

    parser_classes = [JSONParser]
    serializer_class = VideoImageExtractionSerializer

    @swagger_auto_schema(
        operation_description="Extract and process images from a video file with deduplication and captioning",
        request_body=VideoImageExtractionSerializer,
        responses={
            200: openapi.Response(
                description="Video image extraction completed successfully",
                examples={
                    "application/json": {
                        "success": True,
                        "message": "Video image extraction completed successfully",
                        "file_id": "f_12345",
                        "notebook_id": 1,
                        "result": {
                            "success": True,
                            "extraction_type": "image_dedup_captions",
                            "statistics": {
                                "initial_frames": 100,
                                "final_frames": 25,
                                "removed_pixel_global": 20,
                                "removed_deep_sequential": 15,
                                "removed_deep_global": 10,
                                "removed_text_ocr": 30,
                                "total_removed": 75,
                                "captions_generated": 25
                            }
                        }
                    }
                }
            ),
            400: openapi.Response(description="Invalid request data"),
            404: openapi.Response(description="Video file or notebook not found"),
            500: openapi.Response(description="Video image extraction failed")
        },
        manual_parameters=[
            openapi.Parameter(
                'notebook_id',
                openapi.IN_PATH,
                description="ID of the notebook containing the video file",
                type=openapi.TYPE_INTEGER,
                required=True
            ),
        ]
    )
    def post(self, request, notebook_id):
        """Extract and process images from a video file with deduplication and captioning."""
        try:
            # Validate request data
            serializer = VideoImageExtractionSerializer(data=request.data)
            if not serializer.is_valid():
                return self.error_response(
                    "Invalid request data", details=serializer.errors
                )

            # Verify notebook access
            notebook = self.get_user_notebook(notebook_id, request.user)

            # Extract video file ID and processing parameters
            video_file_id = serializer.validated_data["video_file_id"]
            
            # Remove 'f_' prefix if present
            if video_file_id.startswith('f_'):
                actual_file_id = video_file_id[2:]
            else:
                actual_file_id = video_file_id

            # Get the knowledge base item for metadata
            kb_item = get_object_or_404(
                KnowledgeBaseItem, id=actual_file_id, user=request.user
            )

            # Get the original video file from MinIO and download to temp location
            import tempfile
            import requests
            
            # Get pre-signed URL for the video file
            video_file_url = storage_adapter.get_original_file_url(actual_file_id, request.user.pk)
            if not video_file_url:
                return self.error_response(
                    f"Video file not found for ID: {video_file_id}",
                    status_code=status.HTTP_404_NOT_FOUND
                )

            # Download the video file to a temporary location
            try:
                response = requests.get(video_file_url, stream=True)
                response.raise_for_status()
                
                # Create temporary file with appropriate extension
                original_filename = kb_item.metadata.get('original_filename', 'video.mp4') if kb_item.metadata else 'video.mp4'
                file_extension = os.path.splitext(original_filename)[1] or '.mp4'
                
                temp_video_file = tempfile.NamedTemporaryFile(delete=False, suffix=file_extension)
                for chunk in response.iter_content(chunk_size=8192):
                    temp_video_file.write(chunk)
                temp_video_file.close()
                
                video_file_path = temp_video_file.name
                
            except Exception as e:
                return self.error_response(
                    f"Failed to download video file: {str(e)}",
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
                )

            # Validate that the file is a video
            if not self._is_video_file(video_file_path):
                # Clean up temp file
                os.unlink(video_file_path)
                return self.error_response(
                    f"File is not a video: {original_filename}",
                    status_code=status.HTTP_400_BAD_REQUEST
                )

            # Build extraction options
            extraction_options = self._build_extraction_options(serializer.validated_data)

            # Generate clean title from filename
            video_title = clean_title(Path(original_filename).stem)

            # Use temporary directory for processing instead of local user directory
            temp_base_dir = tempfile.mkdtemp(prefix=f"video_extraction_{actual_file_id}_")
            base_file_dir = temp_base_dir

            try:
                # Process the video for image extraction
                async def process_video_async():
                    return await media_extractor.process_video_for_images(
                        file_path=video_file_path,
                        output_dir=base_file_dir,  # Pass base directory, not images directory
                        video_title=video_title,
                        extraction_options=extraction_options,
                        final_images_dir_name="images"  # This will create images/ folder in base_file_dir
                    )

                # Run async processing
                result = async_to_sync(process_video_async)()

                # Calculate final output paths
                final_images_dir = os.path.join(base_file_dir, 'images')  # This will be f_{file_id}/images/
                caption_file = os.path.join(final_images_dir, f"{video_title}_caption.json")  # Inside images folder
                
                # Upload extracted images to MinIO
                if result.get('success') and os.path.exists(final_images_dir):
                    self._upload_extracted_images_to_minio(final_images_dir, kb_item)
                    
                    # Process caption data if available
                    self._process_uploaded_caption_data(kb_item)
                    
                    # Clean up temporary processing directory after upload
                    import shutil
                    try:
                        shutil.rmtree(base_file_dir)
                        logger.info(f"Cleaned up temporary directory: {base_file_dir}")
                    except Exception as e:
                        logger.warning(f"Failed to clean up temporary directory {base_file_dir}: {str(e)}")

                # Update knowledge base item metadata with extraction info
                if kb_item.metadata is None:
                    kb_item.metadata = {}
                
                kb_item.metadata.update({
                    'video_image_extraction': {
                        'completed': result.get('success', False),
                        'timestamp': datetime.now().isoformat(),
                        'extraction_options': extraction_options,
                        'processing_info': {
                            'processing_type': 'temporary_directory',
                            'images_stored_in_minio': True,
                            'temp_processing_completed': True
                        },
                        'statistics': result.get('statistics', {})
                    }
                })
                kb_item.save(update_fields=['metadata'])

                return Response({
                    "success": True,
                    "message": "Video image extraction completed successfully",
                    "file_id": f"f_{actual_file_id}",
                    "notebook_id": notebook_id,
                    "result": result,
                    "output_paths": {
                        "images_uploaded_to_minio": True,
                        "temp_processing_directory": base_file_dir,
                        "processing_type": "temporary_directory"
                    }
                }, status=status.HTTP_200_OK)
                
            finally:
                # Clean up temporary video file
                if 'video_file_path' in locals() and os.path.exists(video_file_path):
                    try:
                        os.unlink(video_file_path)
                        logger.info(f"Cleaned up temporary video file: {video_file_path}")
                    except Exception as e:
                        logger.warning(f"Failed to clean up temporary video file: {e}")
                
                # Clean up temporary processing directory if it still exists
                if 'temp_base_dir' in locals() and os.path.exists(temp_base_dir):
                    try:
                        import shutil
                        shutil.rmtree(temp_base_dir)
                        logger.info(f"Final cleanup of temporary directory: {temp_base_dir}")
                    except Exception as e:
                        logger.warning(f"Failed final cleanup of temporary directory: {e}")

        except Exception as e:
            return self.error_response(
                "Video image extraction failed",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                details={"error": str(e)},
            )

    def _is_video_file(self, file_path: str) -> bool:
        """Check if the file is a video based on its extension and MIME type."""
        video_extensions = {'.mp4', '.avi', '.mov', '.mkv', '.webm', '.flv', '.m4v', '.wmv', '.3gp'}
        file_ext = Path(file_path).suffix.lower()
        
        if file_ext in video_extensions:
            return True
            
        # Also check MIME type
        mime_type, _ = mimetypes.guess_type(file_path)
        if mime_type and mime_type.startswith('video/'):
            return True
            
        return False

    def _build_extraction_options(self, validated_data: Dict[str, Any]) -> Dict[str, Any]:
        """Build extraction options dictionary from validated form data."""
        options = {}
        
        # Extract processing parameters
        for param in ['extract_interval', 'pixel_threshold', 'sequential_deep_threshold', 
                      'global_deep_threshold', 'min_words']:
            if param in validated_data:
                options[param] = validated_data[param]
        
        return options

    def _upload_extracted_images_to_minio(self, local_images_dir: str, kb_item):
        """Upload extracted images from local directory to MinIO with proper structure."""
        try:
            import glob
            from .models import KnowledgeBaseImage
            
            # Find all image files in the local directory
            image_extensions = ['*.jpg', '*.jpeg', '*.png', '*.gif', '*.svg']
            image_files = []
            for ext in image_extensions:
                image_files.extend(glob.glob(os.path.join(local_images_dir, ext)))
            
            # Also look for JSON files (captions, figure data, etc.)
            json_files = glob.glob(os.path.join(local_images_dir, '*.json'))
            all_files = image_files + json_files
            
            if not all_files:
                logger.info(f"No images or data files found in {local_images_dir}")
                return
            
            logger.info(f"Uploading {len(all_files)} files from {local_images_dir} to MinIO")
            
            # Upload each file to MinIO
            image_id = 1
            for file_path in all_files:
                try:
                    filename = os.path.basename(file_path)
                    
                    # Read file content
                    with open(file_path, 'rb') as f:
                        file_content = f.read()
                    
                    # Determine content type
                    import mimetypes
                    content_type, _ = mimetypes.guess_type(filename)
                    content_type = content_type or 'application/octet-stream'
                    
                    # Store in MinIO using file ID structure with images subfolder
                    object_key = storage_adapter.storage_service.minio_backend.save_file_with_auto_key(
                        content=file_content,
                        filename=filename,
                        prefix="kb",
                        content_type=content_type,
                        metadata={
                            'kb_item_id': str(kb_item.id),
                            'user_id': str(kb_item.user.id),
                            'file_type': 'video_extracted_image' if filename.lower().endswith(('.jpg', '.jpeg', '.png', '.gif', '.svg')) else 'video_extracted_data',
                            'extracted_from': 'video_processing',
                        },
                        user_id=str(kb_item.user.id),
                        file_id=str(kb_item.id),
                        subfolder="images"
                    )
                    
                    # Create KnowledgeBaseImage record for image files
                    if filename.lower().endswith(('.jpg', '.jpeg', '.png', '.gif', '.svg')):
                        KnowledgeBaseImage.objects.create(
                            knowledge_base_item=kb_item,
                            image_file=filename,
                            image_caption="",  # Will be populated from figure_data.json if available
                            image_id=image_id,
                            figure_name=f"Figure {image_id}",
                            minio_object_key=object_key,
                            content_type=content_type,
                            file_size=len(file_content),
                            image_metadata={
                                'original_filename': filename,
                                'file_size': len(file_content),
                                'content_type': content_type,
                                'kb_item_id': str(kb_item.id),
                                'extracted_from': 'video_processing',
                            }
                        )
                        image_id += 1
                    
                    logger.info(f"Uploaded {filename} to MinIO: {object_key}")
                    
                except Exception as e:
                    logger.error(f"Failed to upload {filename} to MinIO: {str(e)}")
                    continue
            
            logger.info(f"Successfully uploaded {len(all_files)} files to MinIO for kb_item {kb_item.id}")
            
        except Exception as e:
            logger.error(f"Error uploading extracted images to MinIO: {str(e)}")

    def _process_uploaded_caption_data(self, kb_item):
        """Process uploaded caption data from figure_data.json and update image records."""
        try:
            import json
            from .utils.minio_backend import get_minio_backend
            from .models import KnowledgeBaseImage
            
            backend = get_minio_backend()
            
            # Try to find and download figure_data.json
            prefix = f"{kb_item.user.id}/kb/{kb_item.id}/images/"
            
            try:
                objects = backend.client.list_objects(backend.bucket_name, prefix=prefix)
                figure_data_key = None
                
                for obj in objects:
                    if obj.object_name.endswith('figure_data.json'):
                        figure_data_key = obj.object_name
                        break
                
                if not figure_data_key:
                    logger.info(f"No figure_data.json found for kb_item {kb_item.id}")
                    return
                
                # Download and parse the JSON data
                content = backend.get_file_content(figure_data_key)
                caption_data = json.loads(content.decode('utf-8'))
                
                # Update KnowledgeBaseImage records with captions
                if isinstance(caption_data, list):
                    for item in caption_data:
                        if isinstance(item, dict) and 'figure_name' in item and 'caption' in item:
                            # Try to find matching image record
                            # The figure_name might be like 'img_0007' while image_file is 'img_0007.png'
                            figure_name = item['figure_name']
                            caption = item['caption']
                            
                            # Try exact match first
                            image_record = KnowledgeBaseImage.objects.filter(
                                knowledge_base_item=kb_item,
                                image_file__icontains=figure_name
                            ).first()
                            
                            if image_record:
                                image_record.image_caption = caption
                                image_record.save()
                                logger.info(f"Updated caption for {figure_name}: {caption[:50]}...")
                            else:
                                logger.warning(f"No image record found for figure: {figure_name}")
                
                logger.info(f"Processed caption data for kb_item {kb_item.id}")
                
            except Exception as e:
                logger.error(f"Error processing caption data for kb_item {kb_item.id}: {e}")
                
        except Exception as e:
            logger.error(f"Error in _process_uploaded_caption_data: {e}")


@method_decorator(csrf_exempt, name="dispatch")
class FileImageView(StandardAPIView, FileAccessValidatorMixin):
    """Serve image files from knowledge base items using database storage."""

    def get(self, request, notebook_id, file_id, image_file):
        """Serve image file through notebook context from database/MinIO."""
        try:
            # Validate access through notebook
            notebook, kb_item, knowledge_item = self.validate_notebook_file_access(
                notebook_id, file_id, request.user
            )

            # Try to find the image in the database first
            from .models import KnowledgeBaseImage
            
            image_record = KnowledgeBaseImage.objects.filter(
                knowledge_base_item=kb_item,
                image_file=image_file
            ).first()
            
            if image_record:
                # Serve from MinIO using the database record
                return self._serve_image_from_minio(image_record)
            
            # For JSON files and other video extraction files, try to find them in MinIO directly
            if image_file.endswith(('.json', '.txt', '.md')):
                try:
                    return self._serve_file_from_minio_by_filename(kb_item, image_file)
                except Http404:
                    pass  # Fall through to filesystem fallback
            
            # Fallback: try to serve from legacy filesystem approach
            # This maintains backward compatibility during migration
            return self._serve_image_from_filesystem(kb_item, image_file)

        except PermissionDenied as e:
            return self.error_response(str(e), status_code=status.HTTP_403_FORBIDDEN)
        except Http404 as e:
            return self.error_response(str(e), status_code=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return self.error_response(
                "Image access failed",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                details={"error": str(e)},
            )
    
    def _serve_image_from_minio(self, image_record):
        """Serve image from MinIO using database record."""
        try:
            # Get pre-signed URL for the image
            image_url = image_record.get_image_url(expires=3600)  # 1 hour expiration
            
            if not image_url:
                raise Http404("Image file not accessible in storage")
            
            # Return redirect to pre-signed URL
            from django.http import HttpResponseRedirect
            return HttpResponseRedirect(image_url)
            
        except Exception as e:
            logger.error(f"Error serving image from MinIO: {e}")
            raise Http404("Image file not accessible")
    
    def _serve_file_from_minio_by_filename(self, kb_item, filename):
        """Serve file from MinIO by searching for object keys that contain the filename."""
        try:
            from .utils.minio_backend import get_minio_backend
            from django.http import HttpResponseRedirect
            
            backend = get_minio_backend()
            
            # Search for objects that match the knowledge base item and filename pattern
            # The object key pattern is: user_id/kb/file_id/subfolder/filename (for video extraction files)
            prefix = f"{kb_item.user.id}/kb/{kb_item.id}/images/"
            
            try:
                # List objects with the prefix for this knowledge base item
                objects = backend.client.list_objects(backend.bucket_name, prefix=prefix)
                
                # Find the object that ends with our filename
                for obj in objects:
                    if obj.object_name.endswith(filename):
                        # Generate pre-signed URL
                        file_url = backend.get_file_url(obj.object_name, expires=3600)
                        
                        # Return redirect to pre-signed URL
                        return HttpResponseRedirect(file_url)
                
                # If no object found, try alternative prefix patterns
                # For backward compatibility with different object key structures
                alternative_prefixes = [
                    f"{kb_item.user.id}/kb/{kb_item.id}/",  # Files in root kb folder (no subfolder)
                    f"kb/{kb_item.user.id}/{kb_item.id}/images/",  # Alternative structure 1
                    f"kb/images/{kb_item.user.id}/{kb_item.id}/",  # Alternative structure 2
                ]
                
                for alt_prefix in alternative_prefixes:
                    try:
                        objects = backend.client.list_objects(backend.bucket_name, prefix=alt_prefix)
                        for obj in objects:
                            if obj.object_name.endswith(filename):
                                file_url = backend.get_file_url(obj.object_name, expires=3600)
                                return HttpResponseRedirect(file_url)
                    except Exception:
                        continue
                
                raise Http404(f"File not found in MinIO: {filename}")
                
            except Exception as e:
                logger.error(f"Error searching for file in MinIO: {filename} - {e}")
                raise Http404(f"File not accessible: {filename}")
            
        except Exception as e:
            logger.error(f"Error serving file from MinIO: {filename} - {e}")
            raise Http404(f"File not accessible: {filename}")
    
    def _serve_image_from_filesystem(self, kb_item, image_file):
        """Fallback method to serve image from filesystem (legacy support)."""
        try:
            # Import inside the method to avoid potential circular dependencies
            from reports.core.figure_service import FigureDataService

            images_dir = FigureDataService._get_knowledge_base_images_path(
                user_id=kb_item.user.id,
                file_id=str(kb_item.id),
            )

            if not images_dir:
                raise Http404(f"Image not found: {image_file}")
            
            image_path = Path(images_dir) / image_file
            
            # Check if image exists
            if not image_path.exists():
                raise Http404(f"Image not found: {image_file}")
            
            # Serve the image file
            return self._serve_image(image_path, image_file)

        except Exception as e:
            logger.error(f"Error serving image from filesystem: {e}")
            raise Http404(f"Image not found: {image_file}")

    def _serve_image(self, image_path: Path, image_file: str):
        """Serve an image file through Django's FileResponse."""
        try:
            response = FileResponse(
                open(image_path, 'rb'),
                as_attachment=False,
            )
            
            # Set content type based on file extension
            content_type, _ = mimetypes.guess_type(str(image_path))
            if not content_type:
                content_type = "application/octet-stream"
            
            response["Content-Type"] = content_type
            response["Content-Disposition"] = f'inline; filename="{image_file}"'
            response["Cache-Control"] = "public, max-age=3600"  # Cache for 1 hour
            response["X-Content-Type-Options"] = "nosniff"
            
            return response
        except Exception as e:
            raise Http404(f"Image not accessible: {str(e)}")


class BatchJobStatusView(StandardAPIView, NotebookPermissionMixin):
    """Get batch job status and progress."""
    
    def get(self, request, notebook_id, batch_job_id):
        """Get batch job status with item details."""
        try:
            # Verify notebook access
            notebook = self.get_user_notebook(notebook_id, request.user)
            
            # Get batch job
            batch_job = get_object_or_404(
                BatchJob, 
                id=batch_job_id, 
                notebook=notebook
            )
            
            # Get batch items with their status
            items = batch_job.items.all().order_by('created_at')
            
            # Calculate progress
            total_items = batch_job.total_items
            completed_items = items.filter(status='completed').count()
            failed_items = items.filter(status='failed').count()
            processing_items = items.filter(status='processing').count()
            pending_items = items.filter(status='pending').count()
            
            # Update batch job counts
            batch_job.completed_items = completed_items
            batch_job.failed_items = failed_items
            batch_job.save(update_fields=['completed_items', 'failed_items'])
            
            # Prepare item details
            item_details = []
            for item in items:
                item_data = {
                    'id': item.id,
                    'status': item.status,
                    'item_data': item.item_data,
                    'upload_id': item.upload_id,
                    'created_at': item.created_at.isoformat(),
                    'updated_at': item.updated_at.isoformat(),
                }
                
                if item.result_data:
                    item_data['result'] = item.result_data
                    
                if item.error_message:
                    item_data['error'] = item.error_message
                    
                item_details.append(item_data)
            
            return Response({
                'batch_job': {
                    'id': batch_job.id,
                    'job_type': batch_job.job_type,
                    'status': batch_job.status,
                    'total_items': total_items,
                    'completed_items': completed_items,
                    'failed_items': failed_items,
                    'processing_items': processing_items,
                    'pending_items': pending_items,
                    'progress_percentage': round((completed_items + failed_items) / total_items * 100, 1) if total_items > 0 else 0,
                    'created_at': batch_job.created_at.isoformat(),
                    'updated_at': batch_job.updated_at.isoformat(),
                },
                'items': item_details
            })
            
        except Exception as e:
            return self.error_response(
                "Failed to get batch job status",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                details={"error": str(e)},
            )
