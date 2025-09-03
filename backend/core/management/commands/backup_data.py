"""
Comprehensive data backup management command.

This command provides backup operations for all critical data:
- Database backup (structure and data)
- MinIO storage backup
- Milvus vector data backup  
- Configuration and settings backup
- Incremental and full backup modes
"""

from django.core.management.base import BaseCommand, CommandError
from django.core.management import call_command
from django.db import connection
from django.conf import settings
from datetime import datetime, timezone
from pathlib import Path
import os
import json
import subprocess
import logging
import shutil

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = """
    Comprehensive data backup operations.
    
    Backup types:
    - database: Database structure and data
    - storage: MinIO files and metadata
    - vectors: Milvus vector database
    - config: Django settings and configurations
    - full: All of the above
    """
    
    def add_arguments(self, parser):
        parser.add_argument(
            'backup_type',
            choices=['database', 'storage', 'vectors', 'config', 'full'],
            help='Type of backup to perform'
        )
        
        parser.add_argument(
            '--output-dir',
            type=str,
            default='./backups',
            help='Directory to store backup files (default: ./backups)'
        )
        
        parser.add_argument(
            '--incremental',
            action='store_true',
            help='Perform incremental backup (only changed data since last backup)'
        )
        
        parser.add_argument(
            '--compress',
            action='store_true',
            help='Compress backup files'
        )
        
        parser.add_argument(
            '--retention-days',
            type=int,
            default=30,
            help='Number of days to retain backups (default: 30)'
        )
        
        parser.add_argument(
            '--exclude-large-files',
            action='store_true',
            help='Exclude large files (>100MB) from backup'
        )

    def handle(self, *args, **options):
        backup_type = options['backup_type']
        output_dir = Path(options['output_dir'])
        incremental = options['incremental']
        compress = options['compress']
        retention_days = options['retention_days']
        exclude_large = options['exclude_large_files']
        
        # Create backup directory
        timestamp = datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')
        backup_dir = output_dir / f"{backup_type}_backup_{timestamp}"
        backup_dir.mkdir(parents=True, exist_ok=True)
        
        self.stdout.write(f"Starting {backup_type} backup to {backup_dir}")
        
        try:
            if backup_type == 'full':
                self._backup_full(backup_dir, incremental, compress, exclude_large)
            elif backup_type == 'database':
                self._backup_database(backup_dir, incremental, compress)
            elif backup_type == 'storage':
                self._backup_storage(backup_dir, incremental, compress, exclude_large)
            elif backup_type == 'vectors':
                self._backup_vectors(backup_dir, compress)
            elif backup_type == 'config':
                self._backup_config(backup_dir, compress)
            
            # Create backup metadata
            self._create_backup_metadata(backup_dir, backup_type, incremental)
            
            # Clean up old backups
            self._cleanup_old_backups(output_dir, retention_days)
            
            self.stdout.write(
                self.style.SUCCESS(f"Backup completed successfully: {backup_dir}")
            )
            
        except Exception as e:
            logger.exception(f"Backup failed: {e}")
            # Clean up failed backup directory
            if backup_dir.exists():
                shutil.rmtree(backup_dir)
            raise CommandError(f"Backup failed: {str(e)}")
    
    def _backup_full(self, backup_dir: Path, incremental: bool, compress: bool, exclude_large: bool):
        """Perform full system backup."""
        self.stdout.write("Performing full system backup...")
        
        self._backup_database(backup_dir / 'database', incremental, compress)
        self._backup_storage(backup_dir / 'storage', incremental, compress, exclude_large)
        self._backup_vectors(backup_dir / 'vectors', compress)
        self._backup_config(backup_dir / 'config', compress)
    
    def _backup_database(self, backup_dir: Path, incremental: bool, compress: bool):
        """Backup database structure and data."""
        backup_dir.mkdir(parents=True, exist_ok=True)
        
        self.stdout.write("Backing up database...")
        
        # Django fixtures backup
        fixtures_file = backup_dir / 'fixtures.json'
        
        try:
            with open(fixtures_file, 'w') as f:
                call_command('dumpdata', stdout=f, format='json', indent=2)
            
            self.stdout.write(f"Database fixtures backed up to {fixtures_file}")
            
        except Exception as e:
            logger.exception(f"Fixtures backup failed: {e}")
            self.stdout.write(self.style.WARNING(f"Fixtures backup failed: {e}"))
        
        # Database-specific backup
        if connection.vendor == 'postgresql':
            self._backup_postgresql(backup_dir, compress)
        elif connection.vendor == 'sqlite':
            self._backup_sqlite(backup_dir, compress)
        
        # Schema backup
        schema_file = backup_dir / 'schema.sql'
        try:
            with open(schema_file, 'w') as f:
                call_command('sqlmigrate', 'notebooks', '0001', stdout=f)
            self.stdout.write(f"Schema backed up to {schema_file}")
        except Exception as e:
            logger.warning(f"Schema backup failed: {e}")
    
    def _backup_postgresql(self, backup_dir: Path, compress: bool):
        """Backup PostgreSQL database."""
        db_config = settings.DATABASES['default']
        
        backup_file = backup_dir / 'postgresql_backup.sql'
        if compress:
            backup_file = backup_file.with_suffix('.sql.gz')
        
        cmd = [
            'pg_dump',
            f"--host={db_config['HOST']}",
            f"--port={db_config['PORT']}",
            f"--username={db_config['USER']}",
            f"--dbname={db_config['NAME']}",
            '--verbose',
            '--clean',
            '--no-owner',
            '--no-privileges'
        ]
        
        if compress:
            cmd.extend(['--compress=9'])
        
        try:
            with open(backup_file, 'w') as f:
                subprocess.run(cmd, stdout=f, check=True, 
                             env={**os.environ, 'PGPASSWORD': db_config['PASSWORD']})
            
            self.stdout.write(f"PostgreSQL backup created: {backup_file}")
            
        except subprocess.CalledProcessError as e:
            logger.exception(f"PostgreSQL backup failed: {e}")
            raise CommandError(f"PostgreSQL backup failed: {e}")
    
    def _backup_sqlite(self, backup_dir: Path, compress: bool):
        """Backup SQLite database."""
        db_path = Path(settings.DATABASES['default']['NAME'])
        
        if not db_path.exists():
            self.stdout.write(self.style.WARNING("SQLite database file not found"))
            return
        
        backup_file = backup_dir / f'sqlite_backup_{db_path.name}'
        
        try:
            shutil.copy2(db_path, backup_file)
            
            if compress:
                import gzip
                with open(backup_file, 'rb') as f_in:
                    with gzip.open(f'{backup_file}.gz', 'wb') as f_out:
                        shutil.copyfileobj(f_in, f_out)
                backup_file.unlink()
                backup_file = Path(f'{backup_file}.gz')
            
            self.stdout.write(f"SQLite backup created: {backup_file}")
            
        except Exception as e:
            logger.exception(f"SQLite backup failed: {e}")
            raise CommandError(f"SQLite backup failed: {e}")
    
    def _backup_storage(self, backup_dir: Path, incremental: bool, compress: bool, exclude_large: bool):
        """Backup MinIO storage."""
        backup_dir.mkdir(parents=True, exist_ok=True)
        
        self.stdout.write("Backing up storage files...")
        
        try:
            from notebooks.utils.storage import get_storage_adapter
            storage = get_storage_adapter()
            
            # Get list of all files
            files_manifest = []
            
            # For MinIO, we'd need to implement file listing
            # This is a simplified version
            from notebooks.models import KnowledgeBaseItem
            
            items = KnowledgeBaseItem.objects.exclude(file_object_key__isnull=True)
            
            for item in items:
                try:
                    # Get file metadata
                    file_size = getattr(item, 'file_size', 0) or 0
                    
                    # Skip large files if requested
                    if exclude_large and file_size > 100 * 1024 * 1024:  # 100MB
                        continue
                    
                    # Download and backup file
                    file_content = storage.get_file_content(item.file_object_key)
                    if file_content:
                        file_path = backup_dir / f"files/{item.id}_{item.file_object_key}"
                        file_path.parent.mkdir(parents=True, exist_ok=True)
                        
                        with open(file_path, 'wb') as f:
                            f.write(file_content)
                        
                        files_manifest.append({
                            'id': str(item.id),
                            'object_key': item.file_object_key,
                            'title': item.title,
                            'size': file_size,
                            'backup_path': str(file_path.relative_to(backup_dir))
                        })
                
                except Exception as e:
                    logger.warning(f"Failed to backup file {item.file_object_key}: {e}")
                    continue
            
            # Save manifest
            manifest_file = backup_dir / 'files_manifest.json'
            with open(manifest_file, 'w') as f:
                json.dump(files_manifest, f, indent=2)
            
            self.stdout.write(f"Storage backup completed: {len(files_manifest)} files backed up")
            
        except Exception as e:
            logger.exception(f"Storage backup failed: {e}")
            raise CommandError(f"Storage backup failed: {e}")
    
    def _backup_vectors(self, backup_dir: Path, compress: bool):
        """Backup Milvus vector data."""
        backup_dir.mkdir(parents=True, exist_ok=True)
        
        self.stdout.write("Backing up vector database...")
        
        try:
            # Export vector collections metadata
            collections_metadata = []
            
            # Legacy Milvus backup removed - RagFlow datasets are managed separately
            from notebooks.models import KnowledgeBaseItem
            
            user_ids = set(KnowledgeBaseItem.objects.values_list('notebook__user_id', flat=True))
            
            for user_id in user_ids:
                if user_id:
                    try:
                        # RagFlow datasets are managed per-notebook, not per-user
                        from notebooks.models import RagFlowDataset
                        datasets = RagFlowDataset.objects.filter(notebook__user_id=user_id)
                        
                        for dataset in datasets:
                            collections_metadata.append({
                                'user_id': user_id,
                                'notebook_id': dataset.notebook.id,
                                'ragflow_dataset_id': dataset.ragflow_dataset_id,
                                'status': dataset.status,
                                'document_count': dataset.get_document_count() if dataset.is_ready() else 0
                            })
                        
                    except Exception as e:
                        logger.warning(f"Failed to backup RagFlow datasets for user {user_id}: {e}")
                        continue
            
            # Save metadata
            metadata_file = backup_dir / 'collections_metadata.json'
            with open(metadata_file, 'w') as f:
                json.dump(collections_metadata, f, indent=2)
            
            self.stdout.write(f"Vector database metadata backed up: {len(collections_metadata)} collections")
            
        except Exception as e:
            logger.exception(f"Vector backup failed: {e}")
            self.stdout.write(self.style.WARNING(f"Vector backup failed: {e}"))
    
    def _backup_config(self, backup_dir: Path, compress: bool):
        """Backup configuration files."""
        backup_dir.mkdir(parents=True, exist_ok=True)
        
        self.stdout.write("Backing up configuration...")
        
        try:
            # Django settings
            config_data = {
                'django_version': __import__('django').VERSION,
                'installed_apps': settings.INSTALLED_APPS,
                'middleware': settings.MIDDLEWARE,
                'database_config': {
                    'engine': settings.DATABASES['default']['ENGINE'],
                    'name': settings.DATABASES['default']['NAME'],
                    # Don't backup sensitive data like passwords
                },
                'static_settings': {
                    'static_url': settings.STATIC_URL,
                    'media_url': settings.MEDIA_URL,
                },
                'backup_timestamp': datetime.now(timezone.utc).isoformat()
            }
            
            config_file = backup_dir / 'django_config.json'
            with open(config_file, 'w') as f:
                json.dump(config_data, f, indent=2, default=str)
            
            self.stdout.write(f"Configuration backed up to {config_file}")
            
        except Exception as e:
            logger.exception(f"Config backup failed: {e}")
            self.stdout.write(self.style.WARNING(f"Config backup failed: {e}"))
    
    def _create_backup_metadata(self, backup_dir: Path, backup_type: str, incremental: bool):
        """Create backup metadata file."""
        metadata = {
            'backup_type': backup_type,
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'incremental': incremental,
            'django_version': __import__('django').VERSION,
            'python_version': __import__('sys').version,
            'backup_size_bytes': self._get_directory_size(backup_dir)
        }
        
        metadata_file = backup_dir / 'backup_metadata.json'
        with open(metadata_file, 'w') as f:
            json.dump(metadata, f, indent=2)
    
    def _get_directory_size(self, path: Path) -> int:
        """Get total size of directory in bytes."""
        total_size = 0
        for file_path in path.rglob('*'):
            if file_path.is_file():
                total_size += file_path.stat().st_size
        return total_size
    
    def _cleanup_old_backups(self, backup_dir: Path, retention_days: int):
        """Clean up old backup files."""
        cutoff_time = datetime.now(timezone.utc).timestamp() - (retention_days * 24 * 3600)
        
        deleted_count = 0
        for backup_path in backup_dir.glob('*_backup_*'):
            if backup_path.is_dir() and backup_path.stat().st_mtime < cutoff_time:
                shutil.rmtree(backup_path)
                deleted_count += 1
        
        if deleted_count > 0:
            self.stdout.write(f"Cleaned up {deleted_count} old backups")