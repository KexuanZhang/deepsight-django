import os
import json
import asyncio
from django.db import transaction
from django.core.files.base import ContentFile
from rest_framework import status, permissions, authentication, generics 
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser
from django.shortcuts import get_object_or_404
from uuid import uuid4    

from .models import Source, UploadedFile, PastedTextFile, URLProcessingResult, KnowledgeItem, Notebook
from .serializers import (
    NotebookSerializer,
    FileUploadSerializer,
    # TextUploadSerializer,
    # URLUploadSerializer,
)
from .utils.upload_processor import UploadProcessor
from .utils.services.file_storage import FileStorageService

upload_processor = UploadProcessor()
file_storage     = FileStorageService()

class FileUploadView(APIView):
    permission_classes     = [permissions.IsAuthenticated]
    authentication_classes = [authentication.SessionAuthentication]
    parser_classes         = [MultiPartParser]

    @transaction.atomic
    def post(self, request, notebook_id):
        """Handle /api/sources/upload/"""
        print(request.data)
        ser = FileUploadSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        notebook = get_object_or_404(Notebook, pk=notebook_id, user=request.user)
        inbound_file = ser.validated_data["file"]
        upload_id    = ser.validated_data.get("upload_file_id") or uuid4().hex

        result = asyncio.run(
            upload_processor.process_upload(inbound_file, upload_id)
        )

        source = Source.objects.create(
            notebook=notebook,
            source_type="file",
            title=inbound_file.name,
            needs_processing=False,
            processing_status="done",
        )
        UploadedFile.objects.create(source=source, file=inbound_file)

        content_md = asyncio.run(
            file_storage.get_file_content(result['file_id'])
        )
        ki = KnowledgeItem(notebook=notebook, source=source)
        ki.file.save(
            f"{result['file_id']}.md",
            ContentFile(content_md.encode("utf-8")),
            save=True
        )

        return Response({
            "success": True,
            "file_id": result['file_id'],
            "knowledge_item_id": ki.id,
        }, status=status.HTTP_201_CREATED)
    
class FileListView(APIView):
    """
    GET /api/notebooks/{notebook_id}/files/
    Return the list of all files (processed) for this notebook.
    """
    permission_classes     = [permissions.IsAuthenticated]
    authentication_classes = [authentication.SessionAuthentication]

    def get(self, request, notebook_id):
        # only include files for notebooks the user owns
        if not Notebook.objects.filter(id=notebook_id, user=request.user).exists():
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)

        # look up all Sources of type=file for this notebook
        sources = Source.objects.filter(
            notebook_id=notebook_id, source_type="file"
        ).order_by("-id")

        files = []
        for src in sources:
            # find the UploadedFile to get its upload_file_id
            try:
                upl = UploadedFile.objects.get(source=src)
            except UploadedFile.DoesNotExist:
                continue
            meta = asyncio.run(file_storage.get_file_metadata(upl.file.name))  # file.name holds our file_id
            files.append({
                "file_id": upl.file.name,
                "upload_file_id": meta.get("upload_file_id") if meta else None,
                "original_filename": meta.get("original_filename") if meta else src.title,
                "file_extension": meta.get("file_extension") if meta else "",
                "file_size": meta.get("file_size") if meta else None,
                "parsing_status": meta.get("parsing_status") if meta else None,
                "uploaded_at": meta.get("upload_timestamp") if meta else None,
            })

        return Response({"success": True, "data": files})


class FileStatusView(APIView):
    """
    GET /api/notebooks/{notebook_id}/files/{upload_file_id}/status/
    Return a one‐time snapshot of parsing status, or 404 if unknown.
    """
    permission_classes     = [permissions.IsAuthenticated]
    authentication_classes = [authentication.SessionAuthentication]

    async def get(self, request, notebook_id, upload_file_id):
        # verify notebook ownership
        if not Notebook.objects.filter(id=notebook_id, user=request.user).exists():
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)

        status_obj = await upload_processor.get_upload_status(upload_file_id)
        if not status_obj:
            return Response({"detail": "Status not found."}, status=status.HTTP_404_NOT_FOUND)
        return Response({"success": True, **status_obj})


class FileDeleteView(APIView):
    """
    DELETE /api/notebooks/{notebook_id}/files/{file_or_upload_id}/
    If that ID matches an upload_file_id → cancel+delete
    otherwise if it matches a stored file_id → delete
    """
    permission_classes     = [permissions.IsAuthenticated]
    authentication_classes = [authentication.SessionAuthentication]

    @transaction.atomic
    async def delete(self, request, notebook_id, file_or_upload_id):
        # verify notebook ownership
        if not Notebook.objects.filter(id=notebook_id, user=request.user).exists():
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)

        # 1) try as an in‐flight upload
        deleted = await file_storage.delete_file_by_upload_id(file_or_upload_id)
        if deleted:
            # also delete any matching Source/KnowledgeItem
            Source.objects.filter(
                uploadedfile__file__icontains=file_or_upload_id
            ).delete()
            KnowledgeItem.objects.filter(
                file__icontains=file_or_upload_id
            ).delete()
            return Response({"success": True}, status=status.HTTP_204_NO_CONTENT)

        # 2) else, try as a completed file
        deleted = await file_storage.delete_file(file_or_upload_id)
        if deleted:
            Source.objects.filter(
                uploadedfile__file=file_or_upload_id
            ).delete()
            KnowledgeItem.objects.filter(
                file__icontains=file_or_upload_id
            ).delete()
            return Response({"success": True}, status=status.HTTP_204_NO_CONTENT)

        return Response({"detail": "File not found."}, status=status.HTTP_404_NOT_FOUND)



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
        return Notebook.objects.filter(user=self.request.user).order_by('-created_at')

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
    serializer_class    = NotebookSerializer
    permission_classes  = [permissions.IsAuthenticated]

    def get_queryset(self):
        # Users can only operate on their own notebooks
        return Notebook.objects.filter(user=self.request.user)
