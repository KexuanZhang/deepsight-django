"""
Comprehensive system health check command.

This command performs health checks on all critical system components:
- Database connectivity and performance
- MinIO storage connectivity and status  
- Milvus vector database connectivity
- Redis cache and Celery broker connectivity
- External API endpoints (OpenAI, etc.)
- File system permissions and storage
"""

from django.core.management.base import BaseCommand, CommandError
from django.db import connection, transaction
from django.core.cache import cache
from django.conf import settings
from typing import Dict, List, Tuple
import logging
import time
import json

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = """
    Perform comprehensive system health checks.
    
    Checks all critical components:
    - Database connectivity and performance
    - MinIO storage connectivity  
    - Milvus vector database
    - Redis and Celery
    - External APIs
    - File system
    """
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--component',
            choices=[
                'database', 'storage', 'vectordb', 'cache', 
                'celery', 'apis', 'filesystem', 'all'
            ],
            default='all',
            help='Specific component to check (default: all)'
        )
        
        parser.add_argument(
            '--format',
            choices=['text', 'json'],
            default='text',
            help='Output format (default: text)'
        )
        
        parser.add_argument(
            '--timeout',
            type=int,
            default=30,
            help='Timeout in seconds for external checks (default: 30)'
        )
        
        parser.add_argument(
            '--critical-only',
            action='store_true',
            help='Only report critical issues'
        )

    def handle(self, *args, **options):
        component = options['component']
        output_format = options['format']
        timeout = options['timeout']
        critical_only = options['critical_only']
        
        self.stdout.write("Starting system health check...")
        
        health_results = {}
        
        try:
            if component == 'all':
                health_results = self._check_all_components(timeout)
            else:
                health_results[component] = self._check_component(component, timeout)
            
            # Output results
            if output_format == 'json':
                self.stdout.write(json.dumps(health_results, indent=2, default=str))
            else:
                self._display_text_results(health_results, critical_only)
                
        except Exception as e:
            logger.exception(f"Health check failed: {e}")
            raise CommandError(f"Health check failed: {str(e)}")
    
    def _check_all_components(self, timeout: int) -> Dict:
        """Check all system components."""
        components = [
            'database', 'storage', 'vectordb', 
            'cache', 'celery', 'apis', 'filesystem'
        ]
        
        results = {}
        for component in components:
            self.stdout.write(f"Checking {component}...")
            results[component] = self._check_component(component, timeout)
        
        return results
    
    def _check_component(self, component: str, timeout: int) -> Dict:
        """Check a specific component."""
        if component == 'database':
            return self._check_database()
        elif component == 'storage':
            return self._check_storage(timeout)
        elif component == 'vectordb':
            return self._check_vectordb(timeout)
        elif component == 'cache':
            return self._check_cache(timeout)
        elif component == 'celery':
            return self._check_celery(timeout)
        elif component == 'apis':
            return self._check_external_apis(timeout)
        elif component == 'filesystem':
            return self._check_filesystem()
        else:
            return {'status': 'error', 'message': f'Unknown component: {component}'}
    
    def _check_database(self) -> Dict:
        """Check database connectivity and performance."""
        try:
            start_time = time.time()
            
            # Test basic connectivity
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
                cursor.fetchone()
            
            # Test transaction
            with transaction.atomic():
                with connection.cursor() as cursor:
                    cursor.execute("SELECT COUNT(*) FROM django_migrations")
                    migration_count = cursor.fetchone()[0]
            
            response_time = time.time() - start_time
            
            # Check database size and table counts
            with connection.cursor() as cursor:
                if connection.vendor == 'postgresql':
                    cursor.execute("""
                        SELECT schemaname, tablename 
                        FROM pg_tables 
                        WHERE schemaname = 'public'
                    """)
                    table_count = len(cursor.fetchall())
                elif connection.vendor == 'sqlite':
                    cursor.execute("""
                        SELECT name FROM sqlite_master 
                        WHERE type='table'
                    """)
                    table_count = len(cursor.fetchall())
                else:
                    table_count = 0
            
            return {
                'status': 'healthy',
                'response_time_ms': round(response_time * 1000, 2),
                'database_vendor': connection.vendor,
                'migration_count': migration_count,
                'table_count': table_count,
                'details': {
                    'connection_ready': True,
                    'transactions_working': True
                }
            }
            
        except Exception as e:
            logger.exception("Database health check failed")
            return {
                'status': 'error',
                'message': str(e),
                'details': {'connection_ready': False}
            }
    
    def _check_storage(self, timeout: int) -> Dict:
        """Check MinIO storage connectivity."""
        try:
            from notebooks.utils.storage import get_storage_adapter
            
            start_time = time.time()
            storage_adapter = get_storage_adapter()
            
            # Test basic connectivity
            test_key = f"health-check-{int(time.time())}"
            test_content = b"health check test"
            
            # Test upload
            upload_success = storage_adapter.upload_file_content(
                test_content, test_key, content_type="text/plain"
            )
            
            # Test download
            if upload_success:
                downloaded_content = storage_adapter.get_file_content(test_key)
                download_success = downloaded_content == test_content
                
                # Cleanup test file
                storage_adapter.delete_file(test_key)
            else:
                download_success = False
            
            response_time = time.time() - start_time
            
            return {
                'status': 'healthy' if upload_success and download_success else 'degraded',
                'response_time_ms': round(response_time * 1000, 2),
                'details': {
                    'upload_working': upload_success,
                    'download_working': download_success,
                    'adapter_type': storage_adapter.__class__.__name__
                }
            }
            
        except Exception as e:
            logger.exception("Storage health check failed")
            return {
                'status': 'error',
                'message': str(e),
                'details': {'connectivity': False}
            }
    
    def _check_vectordb(self, timeout: int) -> Dict:
        """Check vector database connectivity - now using RagFlow."""
        try:
            from infrastructure.ragflow.client import get_ragflow_client
            
            start_time = time.time()
            
            # Test RagFlow connection
            ragflow_client = get_ragflow_client()
            ragflow_healthy = ragflow_client.health_check()
            
            response_time = time.time() - start_time
            
            return {
                'status': 'healthy' if ragflow_healthy else 'unhealthy',
                'response_time_ms': round(response_time * 1000, 2),
                'details': {
                    'ragflow_ready': ragflow_healthy
                }
            }
            
        except Exception as e:
            logger.exception("RagFlow health check failed")
            return {
                'status': 'error',
                'message': str(e),
                'details': {'ragflow_ready': False}
            }
    
    def _check_cache(self, timeout: int) -> Dict:
        """Check Redis cache connectivity."""
        try:
            start_time = time.time()
            
            # Test cache operations
            test_key = f"health-check-{int(time.time())}"
            test_value = "health check test"
            
            cache.set(test_key, test_value, timeout=60)
            retrieved_value = cache.get(test_key)
            cache.delete(test_key)
            
            response_time = time.time() - start_time
            
            cache_working = retrieved_value == test_value
            
            return {
                'status': 'healthy' if cache_working else 'degraded',
                'response_time_ms': round(response_time * 1000, 2),
                'details': {
                    'set_working': True,
                    'get_working': retrieved_value == test_value,
                    'delete_working': True
                }
            }
            
        except Exception as e:
            logger.exception("Cache health check failed")
            return {
                'status': 'error',
                'message': str(e),
                'details': {'connection_ready': False}
            }
    
    def _check_celery(self, timeout: int) -> Dict:
        """Check Celery worker connectivity."""
        try:
            from celery import current_app
            
            start_time = time.time()
            
            # Get active workers
            inspect = current_app.control.inspect(timeout=timeout)
            active_workers = inspect.active()
            
            response_time = time.time() - start_time
            
            worker_count = len(active_workers) if active_workers else 0
            
            return {
                'status': 'healthy' if worker_count > 0 else 'degraded',
                'response_time_ms': round(response_time * 1000, 2),
                'details': {
                    'active_workers': worker_count,
                    'worker_names': list(active_workers.keys()) if active_workers else []
                }
            }
            
        except Exception as e:
            logger.exception("Celery health check failed")
            return {
                'status': 'error',
                'message': str(e),
                'details': {'connection_ready': False}
            }
    
    def _check_external_apis(self, timeout: int) -> Dict:
        """Check external API endpoints."""
        import requests
        
        results = {}
        
        # Check OpenAI API
        if hasattr(settings, 'OPENAI_API_KEY') and settings.OPENAI_API_KEY:
            try:
                start_time = time.time()
                response = requests.get(
                    "https://api.openai.com/v1/models",
                    headers={"Authorization": f"Bearer {settings.OPENAI_API_KEY}"},
                    timeout=timeout
                )
                response_time = time.time() - start_time
                
                results['openai'] = {
                    'status': 'healthy' if response.status_code == 200 else 'degraded',
                    'response_time_ms': round(response_time * 1000, 2),
                    'status_code': response.status_code
                }
            except Exception as e:
                results['openai'] = {
                    'status': 'error',
                    'message': str(e)
                }
        else:
            results['openai'] = {
                'status': 'not_configured',
                'message': 'API key not configured'
            }
        
        return results
    
    def _check_filesystem(self) -> Dict:
        """Check filesystem permissions and storage."""
        import os
        import tempfile
        
        try:
            # Test temp directory access
            temp_dir = tempfile.gettempdir()
            temp_file = os.path.join(temp_dir, f"health-check-{int(time.time())}.tmp")
            
            # Test write
            with open(temp_file, 'w') as f:
                f.write("health check test")
            
            # Test read
            with open(temp_file, 'r') as f:
                content = f.read()
            
            # Cleanup
            os.remove(temp_file)
            
            # Get disk space
            stat = os.statvfs(temp_dir)
            available_bytes = stat.f_bavail * stat.f_frsize
            available_gb = available_bytes / (1024**3)
            
            return {
                'status': 'healthy',
                'details': {
                    'temp_dir': temp_dir,
                    'write_working': True,
                    'read_working': content == "health check test",
                    'available_space_gb': round(available_gb, 2)
                }
            }
            
        except Exception as e:
            logger.exception("Filesystem health check failed")
            return {
                'status': 'error',
                'message': str(e),
                'details': {'filesystem_ready': False}
            }
    
    def _display_text_results(self, results: Dict, critical_only: bool):
        """Display health check results in text format."""
        overall_status = 'healthy'
        
        for component, result in results.items():
            status = result.get('status', 'unknown')
            
            if status == 'error':
                overall_status = 'error'
            elif status == 'degraded' and overall_status != 'error':
                overall_status = 'degraded'
            
            if critical_only and status not in ['error', 'degraded']:
                continue
            
            # Color code status
            if status == 'healthy':
                status_display = self.style.SUCCESS(status.upper())
            elif status == 'degraded':
                status_display = self.style.WARNING(status.upper())
            elif status == 'error':
                status_display = self.style.ERROR(status.upper())
            else:
                status_display = status.upper()
            
            self.stdout.write(f"{component.upper()}: {status_display}")
            
            # Display details
            if 'response_time_ms' in result:
                self.stdout.write(f"  Response Time: {result['response_time_ms']}ms")
            
            if 'message' in result:
                self.stdout.write(f"  Message: {result['message']}")
            
            if 'details' in result and isinstance(result['details'], dict):
                for key, value in result['details'].items():
                    self.stdout.write(f"  {key.replace('_', ' ').title()}: {value}")
            
            self.stdout.write("")  # Empty line
        
        # Overall status
        if overall_status == 'healthy':
            self.stdout.write(self.style.SUCCESS("OVERALL STATUS: HEALTHY"))
        elif overall_status == 'degraded':
            self.stdout.write(self.style.WARNING("OVERALL STATUS: DEGRADED"))
        else:
            self.stdout.write(self.style.ERROR("OVERALL STATUS: ERROR"))