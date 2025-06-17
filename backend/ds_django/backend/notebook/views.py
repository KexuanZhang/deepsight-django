# notebooks/views_file_upload.py

from rest_framework import status, permissions, generics
from rest_framework.views import APIView
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.response import Response
from django.shortcuts import get_object_or_404


from .models import Notebook, UploadedFile
from .serializers import UploadedFileUploadSerializer, UploadedFileSerializer, NotebookSerializer
from .utils.file_validator import FileValidator
from .utils.upload_processor import UploadProcessor

class UploadedFileListAPIView(generics.ListAPIView):
    """
    GET  /api/v1/notebooks/{notebook_pk}/files/
    Lists all files in notebook #{notebook_pk} for the authenticated user.
    """
    serializer_class = UploadedFileSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        nb_pk = self.kwargs["notebook_pk"]
        return UploadedFile.objects.filter(
            notebook__pk=nb_pk,
            notebook__user=self.request.user
        ).order_by("-created_at")

class FileUploadAPIView(APIView):
    """
    POST /api/v1/files/upload/
    Expects multipart/form-data with:
      - file: the uploaded file
      - notebook: the notebook ID to attach to
    """
    permission_classes = [permissions.IsAuthenticated]
    parser_classes    = [MultiPartParser, FormParser]

    def post(self, request):
        # 1) validate incoming form
        serializer = UploadedFileUploadSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        incoming = serializer.validated_data['file']

        # 2) find the notebook
        notebook_id = request.data.get('notebook')
        notebook = get_object_or_404(Notebook, pk=notebook_id, user=request.user)

        # 3) create the UploadedFile record
        uploaded = UploadedFile.objects.create(
            notebook=notebook,
            file=incoming,
            status=UploadedFile.STATUS_PENDING,
            parsing_status=UploadedFile.STATUS_PENDING,
        )

        # 4) run validation + processing (sync)
        try:
            validator = FileValidator()
            val = validator.validate_file(uploaded.file.path)
            uploaded.validation_result = val

            validator.validate_file_content(uploaded.file.path)

            uploaded.status, uploaded.parsing_status = (
                UploadedFile.STATUS_PROCESSING,
                UploadedFile.STATUS_PROCESSING,
            )
            uploaded.save()

            processor = UploadProcessor()
            proc = processor.process_upload(uploaded.file.path)

            uploaded.processing_result = proc
            uploaded.status = UploadedFile.STATUS_COMPLETED
            uploaded.parsing_status = UploadedFile.STATUS_COMPLETED
            uploaded.save()

        except Exception as e:
            uploaded.status = UploadedFile.STATUS_ERROR
            uploaded.parsing_status = UploadedFile.STATUS_ERROR
            uploaded.processing_result = {'error': str(e)}
            uploaded.save()
            return Response(
                {"detail": "Upload failed", "error": str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )

        # 5) return the complete record
        out = UploadedFileSerializer(uploaded, context={'request': request})
        return Response(out.data, status=status.HTTP_201_CREATED)


class NotebookListCreateAPIView(generics.ListCreateAPIView):
    """
    GET  /api/notebooks/       → list only notebooks of request.user
    POST /api/notebooks/       → create new notebook for request.user
    """
    serializer_class = NotebookSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Notebook.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class NotebookDetailAPIView(generics.RetrieveAPIView):
    """
    GET  /api/notebooks/{pk}/  → retrieve a single notebook if it belongs to request.user
    """
    serializer_class = NotebookSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        # ensures 404 if someone tries to fetch another user’s notebook
        return Notebook.objects.filter(user=self.request.user)
    
    def perform_destroy(self, instance):
        # Optional: if you need to do cleanup or soft-delete, override here
        instance.delete()
