"""
One-time repair command to fix missing content in KnowledgeBaseItem records.
This repairs items that have MinIO files but no content in the database.
"""

from django.core.management.base import BaseCommand
from django.db import transaction
from notebooks.models import KnowledgeBaseItem
from notebooks.utils.storage import get_minio_backend


class Command(BaseCommand):
    help = "One-time repair: fix missing content in KnowledgeBaseItem records from MinIO files"

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be updated without making changes',
        )
        parser.add_argument(
            '--limit',
            type=int,
            default=100,
            help='Maximum number of items to process (default: 100)',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        limit = options['limit']
        
        self.stdout.write("Starting one-time content repair process...")
        
        # Find KB items that have MinIO files but no database content
        all_with_files = KnowledgeBaseItem.objects.filter(
            file_object_key__isnull=False  # Has MinIO file reference
        ).exclude(
            file_object_key__exact=''  # Exclude empty strings
        )
        
        # Filter to items with no content or empty content
        items_to_update = []
        for item in all_with_files:
            if not item.content or len(item.content.strip()) == 0:
                items_to_update.append(item)
                if len(items_to_update) >= limit:
                    break

        total_items = len(items_to_update)
        self.stdout.write(f"Found {total_items} items to process")

        if total_items == 0:
            self.stdout.write(self.style.SUCCESS("No items need content population"))
            return

        if dry_run:
            self.stdout.write(self.style.WARNING("DRY RUN - No changes will be made"))
            for item in items_to_update:
                self.stdout.write(f"Would update: {item.title} (ID: {item.id})")
            return

        # Initialize MinIO backend
        minio_backend = get_minio_backend()
        
        updated_count = 0
        error_count = 0

        with transaction.atomic():
            for item in items_to_update:
                try:
                    # Try to retrieve content from MinIO
                    content_bytes = minio_backend.get_file(item.file_object_key)
                    
                    if content_bytes:
                        # Decode and save to database
                        content = content_bytes.decode('utf-8')
                        item.content = content
                        item.save(update_fields=['content'])
                        
                        updated_count += 1
                        self.stdout.write(
                            f"✓ Updated: {item.title} (ID: {item.id}) - {len(content)} chars"
                        )
                    else:
                        error_count += 1
                        self.stdout.write(
                            self.style.ERROR(
                                f"✗ No content found in MinIO: {item.title} (ID: {item.id})"
                            )
                        )

                except Exception as e:
                    error_count += 1
                    self.stdout.write(
                        self.style.ERROR(
                            f"✗ Error processing {item.title} (ID: {item.id}): {str(e)}"
                        )
                    )

        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS(f"Content repair completed!"))
        self.stdout.write(f"Updated: {updated_count} items")
        if error_count > 0:
            self.stdout.write(self.style.WARNING(f"Errors: {error_count} items")) 