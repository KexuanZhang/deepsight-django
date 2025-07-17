"""
Main orchestrator service for report generation using dependency injection.
"""

import logging
from typing import Dict, Optional, List, Any
from .interfaces.report_generator_interface import ReportGeneratorInterface
from .interfaces.input_processor_interface import InputProcessorInterface
from .interfaces.file_storage_interface import FileStorageInterface
from .interfaces.configuration_interface import ReportConfigurationInterface
from .core.generation_service import GenerationService
from .core.job_service import JobService
from .core.input_service import InputService
from .core.storage_service import StorageService
from .factories.report_generator_factory import ReportGeneratorFactory
from .factories.input_processor_factory import InputProcessorFactory
from .factories.storage_factory import StorageFactory
from .models import Report

logger = logging.getLogger(__name__)


class ReportOrchestrator:
    """Main orchestrator service for report generation using dependency injection"""
    
    def __init__(
        self,
        report_generator: Optional[ReportGeneratorInterface] = None,
        input_processor: Optional[InputProcessorInterface] = None,
        file_storage: Optional[FileStorageInterface] = None,
        config_manager: Optional[ReportConfigurationInterface] = None
    ):
        # Use dependency injection or default implementations
        self.report_generator = report_generator or ReportGeneratorFactory.create_generator()
        self.input_processor = input_processor or InputProcessorFactory.create_processor()
        self.file_storage = file_storage or StorageFactory.create_storage()
        
        # Import here to avoid circular imports
        from .config import report_config as default_config_manager
        self.config_manager = config_manager or default_config_manager
        
        # Initialize services with dependencies
        self.generation_service = GenerationService(
            self.report_generator,
            self.input_processor,
            self.file_storage,
            self.config_manager
        )
        self.job_service = JobService()
        self.input_service = InputService(self.input_processor)
        self.storage_service = StorageService(self.file_storage)
    
    def create_report_job(
        self, report_data: Dict[str, Any], user=None, notebook=None
    ) -> Report:
        """Create a new report generation job"""
        return self.job_service.create_job(report_data, user, notebook)
    
    def generate_report(self, report_id: int) -> Dict[str, Any]:
        """Generate a complete report"""
        return self.generation_service.generate_report(report_id)
    
    def update_job_progress(
        self, job_id: str, progress: str, status: Optional[str] = None
    ):
        """Update job progress and optionally status"""
        self.job_service.update_job_progress(job_id, progress, status)
    
    def update_job_result(self, job_id: str, result: Dict, status: str = "completed"):
        """Update job with final result"""
        self.job_service.update_job_result(job_id, result, status)
    
    def update_job_error(self, job_id: str, error: str):
        """Update job with error information"""
        self.job_service.update_job_error(job_id, error)
    
    def get_job_status(self, job_id: str) -> Optional[Dict]:
        """Get the status of a report generation job"""
        return self.job_service.get_job_status(job_id)
    
    def cancel_report_job(self, job_id: str) -> bool:
        """Cancel a report generation job by dispatching a background task."""
        return self.job_service.cancel_job(job_id)
    
    def list_report_jobs(self, user_id: Optional[int] = None, limit: int = 50) -> List[Dict[str, Any]]:
        """List report generation jobs"""
        return self.job_service.list_jobs(user_id, limit)
    
    def delete_report_job(self, job_id: str, user_id: int) -> bool:
        """Delete a report generation job and its associated files"""
        # Get report ID from job
        job_status = self.get_job_status(job_id)
        if not job_status:
            return False
        
        report_id = str(job_status.get('report_id', ''))
        
        # Delete storage files
        storage_deleted = self.storage_service.delete_report_storage(report_id, user_id)
        
        # Delete job metadata
        job_deleted = self.job_service.delete_job(job_id)
        
        return storage_deleted and job_deleted
    
    def validate_report_configuration(self, config: Dict[str, Any]) -> bool:
        """Validate report configuration"""
        return self.generation_service.validate_report_config(config)
    
    def get_supported_options(self) -> Dict[str, Any]:
        """Get supported configuration options"""
        return self.generation_service.get_supported_options()
    
    def process_knowledge_base_input(self, file_paths: List[str]) -> Dict[str, Any]:
        """Process input files from knowledge base"""
        return self.input_service.process_knowledge_base_files(file_paths)
    
    def cleanup_temporary_files(self, temp_file_paths: List[str]):
        """Clean up temporary files"""
        self.input_service.cleanup_temporary_files(temp_file_paths)
    
    def setup_report_storage(self, user_id: int, report_id: str, notebook_id: Optional[int] = None):
        """Set up storage for a report"""
        return self.storage_service.setup_report_storage(user_id, report_id, notebook_id)
    
    def validate_configuration_settings(self, config: Dict[str, Any]) -> Dict[str, bool]:
        """Validate configuration settings"""
        return self.config_manager.validate_config(config)
    
    def cleanup_old_jobs(self, days: int = 7):
        """Clean up old jobs"""
        self.job_service.cleanup_old_jobs(days)
    
    def cleanup_failed_job(self, job_id: str):
        """Clean up temp directories and resources for a failed job"""
        try:
            # First try to get the report to find its output directory
            from .models import Report
            try:
                report = Report.objects.get(job_id=job_id)
                # Create the output directory path to cleanup
                output_dir = self.storage_service.file_storage.create_output_directory(
                    user_id=report.user.pk,
                    report_id=str(report.id),
                    notebook_id=report.notebooks.pk if report.notebooks else None
                )
                
                # Clean up the failed generation resources
                self.storage_service.cleanup_failed_generation(output_dir)
                logger.info(f"Cleaned up storage resources for failed job {job_id}")
            except Report.DoesNotExist:
                logger.warning(f"Report not found for cleanup: {job_id}")
            
            # Also use the cancel_generation method for any additional cleanup
            self.cancel_generation(job_id)
            logger.info(f"Completed cleanup for failed job {job_id}")
        except Exception as e:
            logger.warning(f"Error cleaning up failed job {job_id}: {e}")


# Global singleton instance with default dependencies
report_orchestrator = ReportOrchestrator()