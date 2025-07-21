# reports/views.py
import json
import shutil
import logging
import time
import redis
from pathlib import Path
from typing import Optional
from datetime import datetime

from django.http import FileResponse, Http404, StreamingHttpResponse, HttpResponse
from django.shortcuts import get_object_or_404
from django.conf import settings
from django.core.cache import cache

from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.decorators import api_view, permission_classes

from .models import Report
from .serializers import (
    ReportSerializer,
    ReportCreateSerializer,
    ReportGenerationRequestSerializer,
    ReportStatusSerializer,
)
from .orchestrator import report_orchestrator
from notebooks.models import Notebook
from .tasks import process_report_generation
from .core.pdf_service import PdfService

logger = logging.getLogger(__name__)


# Notebook-specific views
class NotebookReportListCreateView(APIView):
    """List and create reports for a specific notebook"""
    permission_classes = [permissions.IsAuthenticated]

    def get_notebook(self, notebook_id):
        """Get the notebook and verify user access"""
        return get_object_or_404(
            Notebook.objects.filter(user=self.request.user),
            pk=notebook_id
        )

    def get(self, request, notebook_id):
        """List reports for a specific notebook"""
        try:
            notebook = self.get_notebook(notebook_id)
            reports = Report.objects.filter(
                user=request.user,
                notebooks=notebook
            ).order_by('-created_at')
            
            # Calculate last modified time for caching
            last_modified = None
            if reports:
                last_modified = max(report.updated_at for report in reports)
            
            # Filter out phantom jobs (completed jobs without actual files)
            validated_reports = []
            for report in reports:
                if report.status == Report.STATUS_COMPLETED:
                    # Check if the job has actual files
                    if report.main_report_object_key or report.result_content:
                        validated_reports.append(self._format_report_data(report))
                    else:
                        logger.warning(
                            f"Skipping phantom job {report.job_id} - no files found"
                        )
                else:
                    # Include non-completed jobs as-is
                    validated_reports.append(self._format_report_data(report))
            
            response = Response({"reports": validated_reports})
            
            # Add caching headers
            if last_modified:
                response['Last-Modified'] = last_modified.strftime('%a, %d %b %Y %H:%M:%S GMT')
            
            # Use minimal caching to ensure delete operations are immediately reflected
            has_active_jobs = any(report.get('status') in ['pending', 'running'] for report in validated_reports)
            cache_timeout = 2 if has_active_jobs else 5
            response['Cache-Control'] = f'max-age={cache_timeout}, must-revalidate'
            
            return response
        except Exception as e:
            logger.error(f"Error listing reports for notebook {notebook_id}: {e}")
            return Response(
                {"detail": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def post(self, request, notebook_id):
        """Create a new report generation job for a specific notebook"""
        try:
            notebook = self.get_notebook(notebook_id)
            
            # Validate input params
            serializer = ReportGenerationRequestSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)

            # Create report job using orchestrator
            report_data = serializer.validated_data.copy()
            report = report_orchestrator.create_report_job(
                report_data, user=request.user, notebook=notebook
            )

            # Queue the job for background processing
            task_result = process_report_generation.delay(report.id)
            
            # Store the Celery task ID for cancellation purposes
            report.celery_task_id = task_result.id
            report.save(update_fields=["celery_task_id"])

            logger.info(
                f"Report generation job {report.job_id} created successfully for report {report.id} in notebook {notebook_id}"
            )

            return Response(
                {
                    "job_id": report.job_id,
                    "report_id": report.id,
                    "status": report.status,
                    "message": "Report generation job has been queued",
                },
                status=status.HTTP_201_CREATED,
            )

        except Exception as e:
            logger.error(f"Error creating report for notebook {notebook_id}: {e}")
            return Response(
                {"detail": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def _format_report_data(self, report: Report) -> dict:
        """Format report data for listing."""
        return {
            "job_id": report.job_id,
            "report_id": report.id,
            "status": report.status,
            "progress": report.progress,
            "title": report.article_title,  # Add title field for frontend compatibility
            "article_title": report.article_title,
            "created_at": report.created_at.isoformat(),
            "updated_at": report.updated_at.isoformat(),
            "error": report.error_message,
            "has_files": bool(report.main_report_object_key),
            "has_content": bool(report.result_content),
        }


class NotebookReportDetailView(APIView):
    """Get detailed information about a specific report"""
    permission_classes = [permissions.IsAuthenticated]

    def get_notebook_and_report(self, notebook_id, job_id):
        """Get the notebook and report, verify user access"""
        notebook = get_object_or_404(
            Notebook.objects.filter(user=self.request.user),
            pk=notebook_id
        )
        report = get_object_or_404(
            Report.objects.filter(user=self.request.user, notebooks=notebook),
            job_id=job_id
        )
        return notebook, report

    def get(self, request, notebook_id, job_id):
        """Get the status of a report generation job"""
        try:
            notebook, report = self.get_notebook_and_report(notebook_id, job_id)
            
            job_data = report_orchestrator.get_job_status(job_id)
            
            if not job_data:
                return Response(
                    {"detail": "Job not found"}, status=status.HTTP_404_NOT_FOUND
                )

            # Return detailed status information
            response_data = {
                "job_id": job_id,
                "report_id": report.id,
                "notebook_id": notebook_id,
                "status": report.status,
                "progress": report.progress,
                "result": job_data.get("result"),
                "error": report.error_message,
                "created_at": report.created_at.isoformat(),
                "updated_at": report.updated_at.isoformat(),
            }

            return Response(response_data)

        except Http404:
            return Response(
                {"detail": "Report not found"}, status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            logger.error(f"Error getting report status for {job_id}: {e}")
            return Response(
                {"detail": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def put(self, request, notebook_id, job_id):
        """Update report content"""
        try:
            notebook, report = self.get_notebook_and_report(notebook_id, job_id)

            # Only allow editing completed reports
            if report.status != Report.STATUS_COMPLETED:
                return Response(
                    {"detail": "Only completed reports can be edited"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            # Get the new content from request
            content = request.data.get('content')
            if content is None:
                return Response(
                    {"detail": "Content field is required"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            # Update the report content
            report.result_content = content
            report.save(update_fields=['result_content', 'updated_at'])

            # Also update the main report file if it exists
            if report.main_report_object_key:
                try:
                    # Save content to MinIO using the file storage service
                    from notebooks.utils.file_storage import FileStorageService
                    storage_service = FileStorageService()
                    storage_service.save_file_content(
                        object_key=report.main_report_object_key,
                        content=content.encode('utf-8'),
                        content_type='text/markdown'
                    )
                    logger.info(f"Updated report file for job {job_id}")
                except Exception as e:
                    logger.warning(f"Could not update report file for {job_id}: {e}")

            logger.info(f"Report content updated for job {job_id} by user {request.user.username}")

            return Response(
                {
                    "message": "Report updated successfully",
                    "job_id": job_id,
                    "report_id": report.id,
                    "updated_at": report.updated_at.isoformat(),
                }
            )

        except Http404:
            return Response(
                {"detail": "Report not found"}, status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            logger.error(f"Error updating report {job_id}: {e}")
            return Response(
                {"detail": f"Error updating report: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    def delete(self, request, notebook_id, job_id):
        """Delete a report and all its associated files"""
        try:
            notebook, report = self.get_notebook_and_report(notebook_id, job_id)

            # Cancel if running
            if report.status == Report.STATUS_RUNNING:
                return Response(
                    {"detail": "Cannot delete a running report."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            deleted_files = 0
            deleted_metadata = False

            # Delete generated files if they exist
            if report.main_report_object_key:
                try:
                    # Delete from MinIO storage
                    from notebooks.utils.file_storage import FileStorageService
                    storage_service = FileStorageService()
                    storage_service.minio_backend.delete_file(report.main_report_object_key)
                    deleted_files = 1
                    logger.info(f"Deleted report file from MinIO storage")
                except Exception as e:
                    logger.warning(
                        f"Could not delete report file for {report.id}: {e}"
                    )

            # Remove job metadata if exists
            if report.job_id:
                deleted_metadata = report_orchestrator.delete_report_job(
                    report.job_id, report.user.id
                )

            # Delete the report instance
            report_id = report.id
            report.delete()

            response = Response(
                {
                    "message": f"Report {report_id} deleted successfully",
                    "report_id": report_id,
                    "deleted_files": deleted_files,
                    "deleted_metadata": deleted_metadata,
                }
            )
            
            # Add cache-busting headers to ensure browsers don't cache delete responses
            response['Cache-Control'] = 'no-cache, no-store, must-revalidate'
            response['Pragma'] = 'no-cache'
            response['Expires'] = '0'
            
            return response

        except Http404:
            return Response(
                {"detail": "Report not found"}, status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            logger.error(f"Error deleting report {job_id}: {e}")
            return Response(
                {"detail": f"Error deleting report: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class NotebookReportCancelView(APIView):
    """Cancel a running or pending report job"""
    permission_classes = [permissions.IsAuthenticated]

    def get_notebook_and_report(self, notebook_id, job_id):
        """Get the notebook and report, verify user access"""
        notebook = get_object_or_404(
            Notebook.objects.filter(user=self.request.user),
            pk=notebook_id
        )
        report = get_object_or_404(
            Report.objects.filter(user=self.request.user, notebooks=notebook),
            job_id=job_id
        )
        return notebook, report

    def post(self, request, notebook_id, job_id):
        """Cancel a running or pending job"""
        try:
            notebook, report = self.get_notebook_and_report(notebook_id, job_id)

            if report.status not in [Report.STATUS_PENDING, Report.STATUS_RUNNING]:
                return Response(
                    {"detail": f"Cannot cancel job in status: {report.status}"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            # Cancel the job
            success = report_orchestrator.cancel_report_job(job_id)

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
                {"detail": "Report not found"}, status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            logger.error(f"Error cancelling job {job_id}: {e}")
            return Response(
                {"detail": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class NotebookReportDownloadView(APIView):
    """Download generated report files"""
    permission_classes = [permissions.IsAuthenticated]

    def get_notebook_and_report(self, notebook_id, job_id):
        """Get the notebook and report, verify user access"""
        notebook = get_object_or_404(
            Notebook.objects.filter(user=self.request.user),
            pk=notebook_id
        )
        report = get_object_or_404(
            Report.objects.filter(user=self.request.user, notebooks=notebook),
            job_id=job_id
        )
        return notebook, report

    def get(self, request, notebook_id, job_id):
        """Download generated report files"""
        try:
            notebook, report = self.get_notebook_and_report(notebook_id, job_id)

            if report.status != Report.STATUS_COMPLETED:
                return Response(
                    {"detail": "Job is not completed yet"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            filename = request.query_params.get("filename")

            # If filename is specified, check against stored metadata
            if filename:
                # Check if filename matches the main report file
                if (report.main_report_object_key and 
                    report.file_metadata.get('main_report_filename') == filename):
                    file_url = report.get_report_url(expires=86400)  # 1 day access
                    if file_url:
                        from django.http import HttpResponseRedirect
                        return HttpResponseRedirect(file_url)
                
                return Response(
                    {"detail": "File not found"}, status=status.HTTP_404_NOT_FOUND
                )

            # Otherwise, return the main report file
            if report.main_report_object_key:
                file_url = report.get_report_url(expires=86400)  # 1 day access
                if file_url:
                    from django.http import HttpResponseRedirect
                    return HttpResponseRedirect(file_url)

            return Response(
                {"detail": "No downloadable report files found"},
                status=status.HTTP_404_NOT_FOUND,
            )

        except Http404:
            return Response(
                {"detail": "Report not found"}, status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            logger.error(f"Error downloading report for job {job_id}: {e}")
            return Response(
                {"detail": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class NotebookReportPdfDownloadView(APIView):
    """Download generated report files as PDF"""
    permission_classes = [permissions.IsAuthenticated]

    def get_notebook_and_report(self, notebook_id, job_id):
        """Get the notebook and report, verify user access"""
        notebook = get_object_or_404(
            Notebook.objects.filter(user=self.request.user),
            pk=notebook_id
        )
        report = get_object_or_404(
            Report.objects.filter(user=self.request.user, notebooks=notebook),
            job_id=job_id
        )
        return notebook, report

    def get(self, request, notebook_id, job_id):
        """Download generated report as PDF"""
        try:
            notebook, report = self.get_notebook_and_report(notebook_id, job_id)

            if report.status != Report.STATUS_COMPLETED:
                return Response(
                    {"detail": "Job is not completed yet"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            # Initialize PDF service
            pdf_service = PdfService()
            
            # Get markdown content
            markdown_content = None
            
            # Try to get content from database first
            if report.result_content:
                markdown_content = report.result_content
            # Fallback: read from MinIO storage
            elif report.main_report_object_key:
                try:
                    from notebooks.utils.storage import FileStorageService
                    storage_service = FileStorageService()
                    content_bytes = storage_service.get_file_content(report.main_report_object_key, user_id=request.user.id)
                    if isinstance(content_bytes, bytes):
                        markdown_content = content_bytes.decode('utf-8')
                    else:
                        markdown_content = content_bytes
                except Exception as e:
                    logger.error(f"Error reading report file for {job_id}: {e}")
            
            if not markdown_content:
                return Response(
                    {"detail": "No report content found to convert to PDF"},
                    status=status.HTTP_404_NOT_FOUND,
                )

            # Generate a temporary PDF file
            report_title = report.article_title or "Research Report"
            filename = f"{report_title.replace(' ', '_')}.pdf"
            
            # Create PDF in temporary directory since we're using MinIO storage
            import tempfile
            temp_dir = Path(tempfile.mkdtemp())
            pdf_path = temp_dir / filename
            
            try:
                # Convert markdown to PDF (now handles image downloading internally)
                logger.info("Converting markdown to PDF with automatic image handling")
                pdf_file_path = pdf_service.convert_markdown_to_pdf(
                    markdown_content=markdown_content,
                    output_path=str(pdf_path),
                    title=report_title,
                    input_file_path=None  # MinIO files don't have local paths
                )
                
                # Return the PDF file
                response = FileResponse(
                    open(pdf_file_path, "rb"),
                    as_attachment=True,
                    filename=filename,
                    content_type='application/pdf'
                )
                
                # Clean up temporary directory
                # Note: We can't clean up immediately due to FileResponse streaming
                # The temp directory will be cleaned up by the OS eventually
                logger.info(f"PDF generated successfully: {pdf_file_path}")
                return response
                
            except Exception as e:
                logger.error(f"Error converting report to PDF for job {job_id}: {e}")
                # Clean up temporary directory on error
                import shutil
                shutil.rmtree(temp_dir, ignore_errors=True)
                
                return Response(
                    {"detail": f"PDF conversion failed: {str(e)}"},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR,
                )

        except Http404:
            return Response(
                {"detail": "Report not found"}, status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            logger.error(f"Error downloading PDF report for job {job_id}: {e}")
            return Response(
                {"detail": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class NotebookReportFilesView(APIView):
    """List all files generated for a specific report job"""
    permission_classes = [permissions.IsAuthenticated]

    def get_notebook_and_report(self, notebook_id, job_id):
        """Get the notebook and report, verify user access"""
        notebook = get_object_or_404(
            Notebook.objects.filter(user=self.request.user),
            pk=notebook_id
        )
        report = get_object_or_404(
            Report.objects.filter(user=self.request.user, notebooks=notebook),
            job_id=job_id
        )
        return notebook, report

    def get(self, request, notebook_id, job_id):
        """List all files generated for a specific job"""
        try:
            notebook, report = self.get_notebook_and_report(notebook_id, job_id)

            files = []

            if report.main_report_object_key:
                try:
                    # Return main report file info from metadata
                    metadata = report.file_metadata or {}
                    filename = metadata.get('main_report_filename', 'report.md')
                    size = metadata.get('main_report_size', 0)
                    file_type = Path(filename).suffix.lower() if filename else '.md'
                    
                    files.append(
                        {
                            "filename": filename,
                            "size": size,
                            "type": file_type,
                            "download_url": f"/api/notebooks/{notebook_id}/reports/{job_id}/download?filename={filename}",
                        }
                    )
                except Exception as e:
                    logger.warning(f"Error listing files for job {job_id}: {e}")

            return Response({"files": files})

        except Http404:
            return Response(
                {"detail": "Report not found"}, status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            logger.error(f"Error listing files for job {job_id}: {e}")
            return Response(
                {"detail": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class NotebookReportContentView(APIView):
    """Get the main report content as text/markdown"""
    permission_classes = [permissions.IsAuthenticated]

    def get_notebook_and_report(self, notebook_id, job_id):
        """Get the notebook and report, verify user access"""
        notebook = get_object_or_404(
            Notebook.objects.filter(user=self.request.user),
            pk=notebook_id
        )
        report = get_object_or_404(
            Report.objects.filter(user=self.request.user, notebooks=notebook),
            job_id=job_id
        )
        return notebook, report

    def get(self, request, notebook_id, job_id):
        """Get the main report content as text/markdown"""
        try:
            notebook, report = self.get_notebook_and_report(notebook_id, job_id)

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
                        "notebook_id": notebook_id,
                        "content": report.result_content,
                        "article_title": report.article_title,
                        "generated_files": report.generated_files,
                    }
                )

            # Fallback: read from MinIO storage
            if report.main_report_object_key:
                try:
                    from notebooks.utils.storage import FileStorageService
                    storage_service = FileStorageService()
                    content_bytes = storage_service.get_file_content(report.main_report_object_key, user_id=request.user.id)
                    if isinstance(content_bytes, bytes):
                        content = content_bytes.decode('utf-8')
                    else:
                        content = content_bytes

                    return Response(
                        {
                            "job_id": job_id,
                            "report_id": report.id,
                            "notebook_id": notebook_id,
                            "content": content,
                            "article_title": report.article_title,
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
                {"detail": "Report not found"}, status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            logger.error(f"Error getting report content for job {job_id}: {e}")
            return Response(
                {"detail": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class ReportModelsView(APIView):
    """Get available models and configuration options"""
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        """Get available models and configuration options"""
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


# ---------------------------------------------------------------------------
# SSE endpoint (plain Django view) – avoids DRF content-negotiation 406 errors
# ---------------------------------------------------------------------------

def notebook_report_status_stream(request, notebook_id, job_id):
    """Server-Sent Events endpoint for real-time report-job status updates."""

    # Support CORS pre-flight / browsers that send OPTIONS
    if request.method == "OPTIONS":
        response = HttpResponse(status=200)
        response["Access-Control-Allow-Origin"] = "*"
        response["Access-Control-Allow-Methods"] = "GET, OPTIONS"
        response["Access-Control-Allow-Headers"] = "Cache-Control, Authorization"
        response["Access-Control-Allow-Credentials"] = "true"
        return response

    # Authentication check – cannot rely on DRF decorators
    if not request.user.is_authenticated:
        response = StreamingHttpResponse(
            f"data: {json.dumps({'type': 'error', 'message': 'Authentication required'})}\n\n",
            content_type="text/event-stream",
            status=401,
        )
        response["Access-Control-Allow-Origin"] = "*"
        response["Access-Control-Allow-Credentials"] = "true"
        return response

    try:
        # Verify user's access to notebook and report
        notebook = get_object_or_404(
            Notebook.objects.filter(user=request.user),
            pk=notebook_id,
        )
        if not Report.objects.filter(job_id=job_id, user=request.user, notebooks=notebook).exists():
            response = StreamingHttpResponse(
                f"data: {json.dumps({'type': 'error', 'message': 'Report not found'})}\n\n",
                content_type="text/event-stream",
                status=404,
            )
            response["Access-Control-Allow-Origin"] = "*"
            response["Access-Control-Allow-Credentials"] = "true"
            return response

        def event_stream():
            """Generator that yields SSE messages."""
            last_status = None
            max_duration = 3600  # 60-minute safety limit to accommodate longer report generation
            start_time = time.time()
            poll_interval = 2  # seconds – server-side polling (DB/cache)

            while time.time() - start_time < max_duration:
                try:
                    status_data = report_orchestrator.get_job_status(job_id)

                    # Fallback to DB if orchestrator returns nothing
                    if not status_data:
                        current_report = Report.objects.filter(job_id=job_id).first()
                        if not current_report:
                            yield f"data: {json.dumps({'type': 'error', 'message': 'Report not found'})}\n\n"
                            break
                        status_data = {
                            "job_id": job_id,
                            "report_id": str(current_report.id),  # Convert UUID to string for JSON serialization
                            "status": current_report.status,
                            "progress": current_report.progress,
                            "error_message": current_report.error_message,
                            "result": None,
                            "updated_at": current_report.updated_at.isoformat(),
                        }

                    current_status_str = json.dumps(status_data, sort_keys=True)
                    if current_status_str != last_status:
                        yield f"data: {json.dumps({'type': 'job_status', 'data': status_data})}\n\n"
                        last_status = current_status_str

                    if status_data.get("status") in ["completed", "failed", "cancelled"]:
                        break

                    time.sleep(poll_interval)

                except Exception as e:
                    logger.error(f"Error in SSE stream for job {job_id}: {e}")
                    yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"
                    break

            yield f"data: {json.dumps({'type': 'stream_closed'})}\n\n"

        response = StreamingHttpResponse(event_stream(), content_type="text/event-stream")
        response["Cache-Control"] = "no-cache"
        response["Access-Control-Allow-Origin"] = "*"
        response["Access-Control-Allow-Headers"] = "Cache-Control"
        response["Access-Control-Allow-Credentials"] = "true"
        return response

    except Exception as e:
        logger.error(f"Error setting up SSE stream for job {job_id}: {e}")
        response = StreamingHttpResponse(
            f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n",
            content_type="text/event-stream",
        )
        response["Access-Control-Allow-Origin"] = "*"
        response["Access-Control-Allow-Credentials"] = "true"
        return response