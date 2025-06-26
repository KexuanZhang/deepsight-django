# reports/views.py
import json
import shutil
import logging
from pathlib import Path
from typing import Optional
from datetime import datetime

from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404
from django.conf import settings
from django.core.cache import cache

from rest_framework import viewsets, permissions, status
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework.pagination import PageNumberPagination

from .models import Report
from .serializers import (
    ReportSerializer,
    ReportCreateSerializer,
    ReportGenerationRequestSerializer,
    ReportStatusSerializer,
)
from .queue_service import report_queue_service

logger = logging.getLogger(__name__)


class ReportPagination(PageNumberPagination):
    page_size = 50
    page_size_query_param = "limit"
    max_page_size = 100


class ReportViewSet(viewsets.ModelViewSet):
    queryset = Report.objects.all()
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = ReportPagination

    def get_serializer_class(self):
        if self.action in ["create", "update", "partial_update"]:
            return ReportCreateSerializer
        elif self.action == "generate":
            return ReportGenerationRequestSerializer
        elif self.action in ["status", "list_jobs"]:
            return ReportStatusSerializer
        return ReportSerializer

    def get_queryset(self):
        # Users can see only their own reports
        return Report.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        # Tie report to requesting user
        serializer.save(user=self.request.user)

    def destroy(self, request, *args, **kwargs):
        """Delete a report and all its associated files."""
        instance = self.get_object()

        # Cancel if running
        if instance.status == Report.STATUS_RUNNING:
            return Response(
                {"detail": "Cannot delete a running report."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            deleted_files = 0
            deleted_metadata = False

            # Delete generated files if they exist
            if instance.main_report_file:
                try:
                    # Get the directory containing the report files
                    report_dir = Path(instance.main_report_file.path).parent
                    if report_dir.exists():
                        deleted_files = len(list(report_dir.rglob("*")))
                        shutil.rmtree(report_dir)
                        logger.info(f"Deleted report directory: {report_dir}")
                except Exception as e:
                    logger.warning(
                        f"Could not delete report files for {instance.id}: {e}"
                    )

            # Remove job metadata if exists
            if instance.job_id:
                deleted_metadata = report_queue_service.delete_job(instance.job_id)

            # Delete the report instance
            report_id = instance.id
            super().destroy(request, *args, **kwargs)

            return Response(
                {
                    "message": f"Report {report_id} deleted successfully",
                    "report_id": report_id,
                    "deleted_files": deleted_files,
                    "deleted_metadata": deleted_metadata,
                }
            )

        except Exception as e:
            logger.error(f"Error deleting report {instance.id}: {e}")
            return Response(
                {"detail": f"Error deleting report: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    @action(detail=False, methods=["post"], url_path="generate")
    def generate(self, request):
        """
        Generate a research report based on the provided configuration.
        """
        try:
            # Validate input params
            serializer = ReportGenerationRequestSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)

            # Create a new Report with status 'pending'
            report_data = serializer.validated_data.copy()

            # Create the report first without article_title to get the ID
            report = Report.objects.create(
                user=request.user,
                status=Report.STATUS_PENDING,
                progress="Report generation job has been queued",
                article_title="Generating...",  # Temporary title
                **report_data,
            )

            # Set simple article_title using report ID only
            # This prevents duplicate filenames and follows the user's requirement
            report.article_title = f"Report_r_{report.id}"
            report.save(update_fields=["article_title"])

            # Add job to queue
            job_id = report_queue_service.add_report_job(report)

            logger.info(
                f"Report generation job {job_id} queued successfully for report {report.id}"
            )

            return Response(
                {
                    "job_id": job_id,
                    "report_id": report.id,
                    "status": report.status,
                    "message": "Report generation job has been queued",
                },
                status=status.HTTP_201_CREATED,
            )

        except Exception as e:
            logger.error(f"Error generating report: {e}")
            return Response(
                {"detail": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=False, methods=["get"], url_path="status/(?P<job_id>[^/.]+)")
    def status(self, request, job_id=None):
        """
        Get the status of a report generation job.
        This replaces the FastAPI /reports/status/{job_id} endpoint.
        """
        try:
            job_data = report_queue_service.get_job_status(job_id)

            if not job_data:
                return Response(
                    {"detail": "Job not found"}, status=status.HTTP_404_NOT_FOUND
                )

            # Ensure user can only see their own jobs
            try:
                report = Report.objects.get(job_id=job_id, user=request.user)

                # Return detailed status information
                response_data = {
                    "job_id": job_id,
                    "report_id": report.id,
                    "status": report.status,
                    "progress": report.progress,
                    "result": job_data.get("result"),
                    "error": report.error_message,
                    "created_at": report.created_at.isoformat(),
                    "updated_at": report.updated_at.isoformat(),
                }

                return Response(response_data)

            except Report.DoesNotExist:
                return Response(
                    {"detail": "Job not found or access denied"},
                    status=status.HTTP_404_NOT_FOUND,
                )

        except Exception as e:
            logger.error(f"Error getting job status for {job_id}: {e}")
            return Response(
                {"detail": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=False, methods=["get"], url_path="jobs")
    def list_jobs(self, request):
        """
        List report generation jobs for the current user.
        This replaces the FastAPI /reports/jobs endpoint.
        """
        try:
            limit = int(request.query_params.get("limit", 50))
            limit = min(limit, 100)  # Cap at 100

            # Get reports for current user
            reports = Report.objects.filter(user=request.user).order_by("-created_at")[
                :limit
            ]

            # Filter out phantom jobs (completed jobs without actual files)
            validated_jobs = []
            for report in reports:
                if report.status == Report.STATUS_COMPLETED:
                    # Check if the job has actual files
                    if report.main_report_file or report.result_content:
                        validated_jobs.append(self._format_job_data(report))
                    else:
                        logger.warning(
                            f"Skipping phantom job {report.job_id} - no files found"
                        )
                else:
                    # Include non-completed jobs as-is
                    validated_jobs.append(self._format_job_data(report))

            return Response({"jobs": validated_jobs})

        except Exception as e:
            logger.error(f"Error listing jobs: {e}")
            return Response(
                {"detail": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=False, methods=["get"], url_path="(?P<job_id>[^/.]+)/download")
    def download_report(self, request, job_id=None):
        """
        Download generated report files.
        This replaces the FastAPI /reports/{job_id}/download endpoint.
        """
        try:
            # Get the report and verify ownership
            report = get_object_or_404(Report, job_id=job_id, user=request.user)

            if report.status != Report.STATUS_COMPLETED:
                return Response(
                    {"detail": "Job is not completed yet"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            filename = request.query_params.get("filename")

            # If filename is specified, return that specific file
            if filename:
                if report.main_report_file:
                    report_dir = Path(report.main_report_file.path).parent
                    file_path = report_dir / filename

                    if file_path.exists() and file_path.is_file():
                        return FileResponse(
                            open(file_path, "rb"), as_attachment=True, filename=filename
                        )

                return Response(
                    {"detail": "File not found"}, status=status.HTTP_404_NOT_FOUND
                )

            # Otherwise, return the main report file
            if report.main_report_file:
                return FileResponse(
                    report.main_report_file.open("rb"),
                    as_attachment=True,
                    filename=Path(report.main_report_file.name).name,
                )

            return Response(
                {"detail": "No downloadable report files found"},
                status=status.HTTP_404_NOT_FOUND,
            )

        except Http404:
            return Response(
                {"detail": "Job not found"}, status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            logger.error(f"Error downloading report for job {job_id}: {e}")
            return Response(
                {"detail": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=False, methods=["get"], url_path="(?P<job_id>[^/.]+)/files")
    def list_job_files(self, request, job_id=None):
        """
        List all files generated for a specific job.
        This replaces the FastAPI /reports/{job_id}/files endpoint.
        """
        try:
            # Get the report and verify ownership
            report = get_object_or_404(Report, job_id=job_id, user=request.user)

            files = []

            if report.main_report_file:
                try:
                    report_dir = Path(report.main_report_file.path).parent

                    if report_dir.exists():
                        for file_path in report_dir.rglob("*"):
                            if file_path.is_file():
                                relative_path = file_path.relative_to(report_dir)
                                files.append(
                                    {
                                        "filename": str(relative_path),
                                        "size": file_path.stat().st_size,
                                        "type": file_path.suffix.lower(),
                                        "download_url": f"/api/reports/{job_id}/download?filename={relative_path}",
                                    }
                                )
                except Exception as e:
                    logger.warning(f"Error listing files for job {job_id}: {e}")

            return Response({"files": files})

        except Http404:
            return Response(
                {"detail": "Job not found"}, status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            logger.error(f"Error listing files for job {job_id}: {e}")
            return Response(
                {"detail": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=False, methods=["get"], url_path="(?P<job_id>[^/.]+)/content")
    def get_report_content(self, request, job_id=None):
        """
        Get the main report content as text/markdown.
        This replaces the FastAPI /reports/{job_id}/content endpoint.
        """
        try:
            # Get the report and verify ownership
            report = get_object_or_404(Report, job_id=job_id, user=request.user)

            if report.status != Report.STATUS_COMPLETED:
                return Response(
                    {"detail": "Job is not completed yet"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            # Try to get content from database first
            if report.result_content:
                return Response(
                    {
                        "job_id": job_id,
                        "report_id": report.id,
                        "content": report.result_content,
                        "article_title": report.result_metadata.get(
                            "article_title", report.article_title
                        ),
                        "generated_files": report.generated_files,
                    }
                )

            # Fallback: read from file
            if report.main_report_file:
                try:
                    with report.main_report_file.open("r", encoding="utf-8") as f:
                        content = f.read()

                    return Response(
                        {
                            "job_id": job_id,
                            "report_id": report.id,
                            "content": content,
                            "article_title": report.result_metadata.get(
                                "article_title", report.article_title
                            ),
                            "generated_files": report.generated_files,
                        }
                    )
                except Exception as e:
                    logger.error(f"Error reading report file for {job_id}: {e}")

            return Response(
                {"detail": "Report content not found"}, status=status.HTTP_404_NOT_FOUND
            )

        except Http404:
            return Response(
                {"detail": "Job not found"}, status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            logger.error(f"Error getting report content for job {job_id}: {e}")
            return Response(
                {"detail": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=False, methods=["post"], url_path="(?P<job_id>[^/.]+)/cancel")
    def cancel_job(self, request, job_id=None):
        """
        Cancel a running or pending job.
        This adds cancellation functionality to the Django implementation.
        """
        try:
            # Get the report and verify ownership
            report = get_object_or_404(Report, job_id=job_id, user=request.user)

            if report.status not in [Report.STATUS_PENDING, Report.STATUS_RUNNING]:
                return Response(
                    {"detail": f"Cannot cancel job in status: {report.status}"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            # Cancel the job
            success = report_queue_service.cancel_job(job_id)

            if success:
                return Response(
                    {
                        "message": f"Job {job_id} cancelled successfully",
                        "job_id": job_id,
                        "status": Report.STATUS_CANCELLED,
                    }
                )
            else:
                return Response(
                    {"detail": "Failed to cancel job"},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR,
                )

        except Http404:
            return Response(
                {"detail": "Job not found"}, status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            logger.error(f"Error cancelling job {job_id}: {e}")
            return Response(
                {"detail": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=False, methods=["get"], url_path="models")
    def available_models(self, request):
        """
        Get available models and configuration options.
        This provides the same information as the FastAPI /reports/models endpoint.
        """
        try:
            return Response(
                {
                    "model_providers": [
                        choice[0] for choice in Report.MODEL_PROVIDER_CHOICES
                    ],
                    "retrievers": [choice[0] for choice in Report.RETRIEVER_CHOICES],
                    "time_ranges": [choice[0] for choice in Report.TIME_RANGE_CHOICES],
                    "prompt_types": [
                        choice[0] for choice in Report.PROMPT_TYPE_CHOICES
                    ],
                    "search_depths": [
                        choice[0] for choice in Report.SEARCH_DEPTH_CHOICES
                    ],
                }
            )
        except Exception as e:
            logger.error(f"Error getting available models: {e}")
            return Response(
                {"detail": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def _format_job_data(self, report: Report) -> dict:
        """Format report data for job listing."""
        return {
            "job_id": report.job_id,
            "report_id": report.id,
            "status": report.status,
            "progress": report.progress,
            "article_title": report.article_title,
            "created_at": report.created_at.isoformat(),
            "updated_at": report.updated_at.isoformat(),
            "error": report.error_message,
            "has_files": bool(report.main_report_file),
            "has_content": bool(report.result_content),
        }
