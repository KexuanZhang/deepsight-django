"""
Report generation service following SOLID principles.
"""

import logging
from typing import Dict, Any, Optional
from pathlib import Path
from ..interfaces.report_generator_interface import ReportGeneratorInterface
from ..interfaces.input_processor_interface import InputProcessorInterface
from ..interfaces.file_storage_interface import FileStorageInterface
from ..interfaces.configuration_interface import ReportConfigurationInterface
from ..models import Report

logger = logging.getLogger(__name__)


class GenerationService:
    """Service responsible for coordinating report generation"""
    
    def __init__(
        self,
        report_generator: ReportGeneratorInterface,
        input_processor: InputProcessorInterface,
        file_storage: FileStorageInterface,
        config_manager: ReportConfigurationInterface
    ):
        self.report_generator = report_generator
        self.input_processor = input_processor
        self.file_storage = file_storage
        self.config_manager = config_manager
    
    def generate_report(self, report_id: int) -> Dict[str, Any]:
        """Generate a report based on the report configuration"""
        try:
            # Get the report from database
            try:
                report = Report.objects.get(id=report_id)
            except Report.DoesNotExist:
                error_msg = f"Report {report_id} not found"
                logger.error(error_msg)
                raise Exception(error_msg)
            
            logger.info(f"Starting report generation for report {report_id}")
            
            # Prepare ReportImage records before generation starts (fixes timing issue)
            if report.include_image:
                from .job_service import JobService
                job_service = JobService()
                if not job_service.prepare_report_images(report):
                    logger.warning(f"Failed to prepare ReportImage records for report {report_id}, continuing anyway")
            
            # Create output directory
            output_dir = self.file_storage.create_output_directory(
                user_id=report.user.pk,
                report_id=str(report.id),
                notebook_id=report.notebooks.pk if report.notebooks else None
            )
            
            # Log the output directory path to track MinIO vs temp paths
            logger.info(f"Output directory for report {report_id}: {output_dir}")
            
            # Prepare input data from knowledge base (no temp files - direct content like podcast)
            content_data = {}
            if report.selected_files_paths:
                processed_data = self.input_processor.process_selected_files(
                    report.selected_files_paths, user_id=report.user.pk
                )
                content_data = self.input_processor.get_content_data(processed_data)
                
                # Conditionally get combined figure data from database based on include_image flag
                if report.include_image:
                    from .figure_service import FigureDataService
                    selected_file_ids = content_data.get("selected_file_ids", [])
                    if selected_file_ids:
                        # Create combined figure data and cache it in the report instance
                        FigureDataService.create_combined_figure_data(
                            report, selected_file_ids
                        )
            
            # Load figure data if available
            figure_data = []
            if report.include_image:
                # Check if we have cached figure data from earlier processing
                if hasattr(report, '_cached_figure_data'):
                    figure_data = report._cached_figure_data

            # Create configuration for report generation
            config_dict = report.get_configuration_dict()
            config_dict.update({
                'output_dir': output_dir,
                'old_outline': report.old_outline,
                'report_id': str(report.id),  # Convert UUID to string for JSON serialization
                'user_id': str(report.user.pk),  # Add user ID for MinIO access
                'figure_data': figure_data,  # Add figure data to config
                **content_data  # Add content data directly (no file paths)
            })
            
            # Topic will be generated from content if empty - no need for default
            
            # Validate configuration
            if not self.report_generator.validate_configuration(config_dict):
                raise Exception("Invalid configuration for report generation")
            
            # Generate the report
            result = self.report_generator.generate_report(config_dict)
            
            if not result.get('success', False):
                error_msg = result.get('error_message', 'Report generation failed')
                raise Exception(error_msg)
            
            # For MinIO storage, files are already uploaded by the report generator
            # For local storage, we need to ensure files are in the correct location
            generated_files = result.get('generated_files', [])
            stored_files = generated_files  # Files are already in final location
            
            # Find main report file
            main_report_file = self.file_storage.get_main_report_file(stored_files)
            
            # Prepare final result
            final_result = {
                "success": True,
                "report_id": report.id,
                "job_id": report.job_id,
                "article_title": result.get('article_title', report.article_title),
                "output_directory": str(output_dir),
                "generated_files": stored_files,
                "main_report_file": main_report_file,
                "processing_logs": result.get('processing_logs', []),
                "report_content": result.get('report_content', ''),
                "created_at": result.get('created_at', ''),
                "generated_topic": result.get('generated_topic', ''),
            }
            
            logger.info(f"Report generation completed successfully for report {report_id}")
            return final_result
            
        except Exception as e:
            logger.error(f"Error in report generation for report {report_id}: {e}")
            
            # Cleanup any temp directories on failure
            try:
                self.report_generator.cancel_generation(str(report.job_id) if report else "unknown")
            except Exception as cleanup_error:
                logger.warning(f"Failed to cleanup temp directories after error: {cleanup_error}")
            
            raise
    
    def validate_report_config(self, config: Dict[str, Any]) -> bool:
        """Validate report configuration before generation"""
        try:
            return self.report_generator.validate_configuration(config)
        except Exception as e:
            logger.error(f"Error validating report config: {e}")
            return False
    
    def get_supported_options(self) -> Dict[str, Any]:
        """Get supported configuration options"""
        try:
            return self.report_generator.get_supported_providers()
        except Exception as e:
            logger.error(f"Error getting supported options: {e}")
            return {}
    
    def cancel_generation(self, job_id: str) -> bool:
        """Cancel an ongoing report generation"""
        try:
            return self.report_generator.cancel_generation(job_id)
        except Exception as e:
            logger.error(f"Error cancelling generation for job {job_id}: {e}")
            return False