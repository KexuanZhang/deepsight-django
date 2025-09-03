"""
Comprehensive notebook cleanup management command.

This command provides various cleanup operations for notebooks including:
- Removing empty notebooks older than specified days
- Cleaning up orphaned files and data
- Removing failed processing jobs
- Optimizing database records
"""

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone
from datetime import timedelta
from typing import Dict, Any
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = """
    Comprehensive notebook cleanup operations.
    
    Available operations:
    - empty-notebooks: Remove notebooks with no content older than N days
    - failed-jobs: Remove failed batch jobs older than N days  
    - orphaned-files: Clean up files with no associated notebook
    - processing-stuck: Reset stuck processing jobs
    - optimize: Optimize database records and indexes
    """
    
    def add_arguments(self, parser):
        parser.add_argument(
            'operation',
            choices=[
                'empty-notebooks', 
                'failed-jobs', 
                'orphaned-files', 
                'processing-stuck', 
                'optimize',
                'all'
            ],
            help='Cleanup operation to perform'
        )
        
        parser.add_argument(
            '--days',
            type=int,
            default=30,
            help='Age threshold in days for cleanup operations (default: 30)'
        )
        
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be cleaned without making changes'
        )
        
        parser.add_argument(
            '--limit',
            type=int,
            default=1000,
            help='Maximum number of items to process per operation (default: 1000)'
        )
        
        parser.add_argument(
            '--force',
            action='store_true',
            help='Skip confirmation prompts'
        )

    def handle(self, *args, **options):
        operation = options['operation']
        dry_run = options['dry_run']
        days = options['days']
        limit = options['limit']
        force = options['force']
        
        self.stdout.write(
            self.style.SUCCESS(f"Starting cleanup operation: {operation}")
        )
        
        if dry_run:
            self.stdout.write(
                self.style.WARNING("DRY RUN MODE - No changes will be made")
            )
        
        try:
            if operation == 'all':
                self._run_all_operations(days, limit, dry_run, force)
            else:
                self._run_operation(operation, days, limit, dry_run, force)
                
        except Exception as e:
            logger.exception(f"Cleanup operation failed: {e}")
            raise CommandError(f"Cleanup failed: {str(e)}")
        
        self.stdout.write(
            self.style.SUCCESS("Cleanup operation completed successfully")
        )
    
    def _run_all_operations(self, days: int, limit: int, dry_run: bool, force: bool):
        """Run all cleanup operations in sequence."""
        operations = [
            'empty-notebooks',
            'failed-jobs', 
            'orphaned-files',
            'processing-stuck',
            'optimize'
        ]
        
        for operation in operations:
            self.stdout.write(f"\n--- Running {operation} ---")
            self._run_operation(operation, days, limit, dry_run, force)
    
    def _run_operation(self, operation: str, days: int, limit: int, dry_run: bool, force: bool):
        """Run a specific cleanup operation."""
        if operation == 'empty-notebooks':
            self._cleanup_empty_notebooks(days, limit, dry_run, force)
        elif operation == 'failed-jobs':
            self._cleanup_failed_jobs(days, limit, dry_run, force)
        elif operation == 'orphaned-files':
            self._cleanup_orphaned_files(limit, dry_run, force)
        elif operation == 'processing-stuck':
            self._reset_stuck_processing(days, dry_run, force)
        elif operation == 'optimize':
            self._optimize_database(dry_run, force)
    
    @transaction.atomic
    def _cleanup_empty_notebooks(self, days: int, limit: int, dry_run: bool, force: bool):
        """Remove notebooks with no content older than specified days."""
        from notebooks.models import Notebook
        
        cutoff_date = timezone.now() - timedelta(days=days)
        
        # Find empty notebooks
        empty_notebooks = Notebook.objects.filter(
            created_at__lt=cutoff_date,
            knowledge_base_items__isnull=True
        ).distinct()[:limit]
        
        count = empty_notebooks.count()
        
        if count == 0:
            self.stdout.write("No empty notebooks found for cleanup")
            return
        
        self.stdout.write(f"Found {count} empty notebooks older than {days} days")
        
        if not force and not dry_run:
            confirm = input(f"Delete {count} empty notebooks? [y/N]: ")
            if confirm.lower() != 'y':
                self.stdout.write("Operation cancelled")
                return
        
        if not dry_run:
            deleted_names = list(empty_notebooks.values_list('name', flat=True))
            empty_notebooks.delete()
            
            self.stdout.write(
                self.style.SUCCESS(f"Deleted {count} empty notebooks")
            )
            logger.info(f"Deleted empty notebooks: {deleted_names}")
        else:
            for notebook in empty_notebooks:
                self.stdout.write(f"Would delete: {notebook.name} (created: {notebook.created_at})")
    
    @transaction.atomic
    def _cleanup_failed_jobs(self, days: int, limit: int, dry_run: bool, force: bool):
        """Remove failed batch jobs older than specified days."""
        from notebooks.models import BatchJob
        
        cutoff_date = timezone.now() - timedelta(days=days)
        
        failed_jobs = BatchJob.objects.filter(
            status__in=['failed', 'error'],
            created_at__lt=cutoff_date
        )[:limit]
        
        count = failed_jobs.count()
        
        if count == 0:
            self.stdout.write("No failed jobs found for cleanup")
            return
        
        self.stdout.write(f"Found {count} failed jobs older than {days} days")
        
        if not force and not dry_run:
            confirm = input(f"Delete {count} failed jobs? [y/N]: ")
            if confirm.lower() != 'y':
                self.stdout.write("Operation cancelled")
                return
        
        if not dry_run:
            failed_jobs.delete()
            self.stdout.write(
                self.style.SUCCESS(f"Deleted {count} failed jobs")
            )
            logger.info(f"Deleted {count} failed batch jobs")
        else:
            for job in failed_jobs:
                self.stdout.write(f"Would delete job: {job.id} ({job.job_type}, {job.status})")
    
    def _cleanup_orphaned_files(self, limit: int, dry_run: bool, force: bool):
        """Clean up files with no associated notebook."""
        from notebooks.models import KnowledgeBaseItem
        
        # Find knowledge base items with no notebook (orphaned)
        orphaned_items = KnowledgeBaseItem.objects.filter(
            notebook__isnull=True
        )[:limit]
        
        count = orphaned_items.count()
        
        if count == 0:
            self.stdout.write("No orphaned files found")
            return
        
        self.stdout.write(f"Found {count} orphaned files")
        
        if not force and not dry_run:
            confirm = input(f"Delete {count} orphaned files? [y/N]: ")
            if confirm.lower() != 'y':
                self.stdout.write("Operation cancelled")
                return
        
        if not dry_run:
            orphaned_items.delete()
            self.stdout.write(
                self.style.SUCCESS(f"Deleted {count} orphaned files")
            )
            logger.info(f"Deleted {count} orphaned knowledge base items")
        else:
            for item in orphaned_items:
                self.stdout.write(f"Would delete orphaned item: {item.id} ({item.title})")
    
    @transaction.atomic
    def _reset_stuck_processing(self, days: int, dry_run: bool, force: bool):
        """Reset processing jobs stuck in 'processing' status."""
        from notebooks.models import KnowledgeBaseItem
        
        cutoff_date = timezone.now() - timedelta(days=days)
        
        stuck_items = KnowledgeBaseItem.objects.filter(
            processing_status='processing',
            created_at__lt=cutoff_date
        )
        
        count = stuck_items.count()
        
        if count == 0:
            self.stdout.write("No stuck processing jobs found")
            return
        
        self.stdout.write(f"Found {count} items stuck in processing for more than {days} days")
        
        if not force and not dry_run:
            confirm = input(f"Reset {count} stuck processing jobs to 'failed'? [y/N]: ")
            if confirm.lower() != 'y':
                self.stdout.write("Operation cancelled")
                return
        
        if not dry_run:
            stuck_items.update(
                processing_status='failed',
                updated_at=timezone.now()
            )
            self.stdout.write(
                self.style.SUCCESS(f"Reset {count} stuck processing jobs")
            )
            logger.info(f"Reset {count} stuck processing jobs to failed status")
        else:
            for item in stuck_items:
                self.stdout.write(f"Would reset stuck item: {item.id} ({item.title})")
    
    def _optimize_database(self, dry_run: bool, force: bool):
        """Optimize database records and indexes."""
        from django.db import connection
        
        if not force and not dry_run:
            confirm = input("Run database optimization? This may take some time [y/N]: ")
            if confirm.lower() != 'y':
                self.stdout.write("Operation cancelled")
                return
        
        if not dry_run:
            with connection.cursor() as cursor:
                # Update statistics for query optimizer
                if connection.vendor == 'postgresql':
                    cursor.execute("ANALYZE;")
                    self.stdout.write("Updated PostgreSQL table statistics")
                elif connection.vendor == 'sqlite':
                    cursor.execute("ANALYZE;")
                    self.stdout.write("Updated SQLite table statistics")
            
            self.stdout.write(
                self.style.SUCCESS("Database optimization completed")
            )
            logger.info("Database optimization completed")
        else:
            self.stdout.write("Would run database optimization (ANALYZE)")