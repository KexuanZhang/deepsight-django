"""
Management command to migrate content from MinIO files to database content field.
"""

from django.core.management.base import BaseCommand
from django.db import transaction
from notebooks.models import KnowledgeBaseItem
from notebooks.utils.storage import get_minio_backend


class Command(BaseCommand):
    help = 'Migrate content from MinIO files to database content field for existing knowledge base items'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be migrated without making changes',
        )
        parser.add_argument(
            '--limit',
            type=int,
            default=100,
            help='Limit number of items to process (default: 100)',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        limit = options['limit']
        
        self.stdout.write(f"Starting content migration {'(DRY RUN)' if dry_run else ''}...")
        
        # Find KB items that have MinIO files but no database content
        items_to_migrate = KnowledgeBaseItem.objects.filter(
            content__isnull=True,  # No content in database
            file_object_key__isnull=False  # But has MinIO file
        ).exclude(
            file_object_key=''  # Exclude empty keys
        )[:limit]
        
        if not items_to_migrate.exists():
            self.stdout.write(self.style.SUCCESS("No items need migration."))
            return
        
        self.stdout.write(f"Found {items_to_migrate.count()} items to migrate")
        
        if dry_run:
            for item in items_to_migrate:
                self.stdout.write(f"Would migrate: {item.id} - {item.title}")
            return
        
        # Initialize MinIO backend
        minio_backend = get_minio_backend()
        
        migrated_count = 0
        failed_count = 0
        
        for item in items_to_migrate:
            try:
                with transaction.atomic():
                    # Try to get content from MinIO
                    content_bytes = minio_backend.get_file(item.file_object_key)
                    
                    if content_bytes:
                        content = content_bytes.decode('utf-8')
                        
                        # Update the database with content
                        item.content = content
                        item.save(update_fields=['content'])
                        
                        migrated_count += 1
                        self.stdout.write(f"✓ Migrated: {item.title} ({len(content)} chars)")
                    else:
                        failed_count += 1
                        self.stdout.write(
                            self.style.WARNING(f"✗ No content found in MinIO: {item.title}")
                        )
                        
            except Exception as e:
                failed_count += 1
                self.stdout.write(
                    self.style.ERROR(f"✗ Error migrating {item.title}: {str(e)}")
                )
        
        self.stdout.write(
            self.style.SUCCESS(
                f"\nMigration complete:\n"
                f"  ✓ Migrated: {migrated_count} items\n"
                f"  ✗ Failed: {failed_count} items"
            )
        ) 