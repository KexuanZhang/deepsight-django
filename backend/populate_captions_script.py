#!/usr/bin/env python
"""
Simple script to populate image captions using the KnowledgeBaseImageService.
This can be run directly without Django management commands.
"""

import os
import sys
import django

# Add the backend directory to Python path
backend_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, backend_dir)

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from notebooks.utils.knowledge_base_image_service import KnowledgeBaseImageService
from notebooks.models import KnowledgeBaseImage, KnowledgeBaseItem


def populate_captions(user_id=None, kb_item_id=None, dry_run=True):
    """
    Populate empty image captions using the KnowledgeBaseImageService.
    
    Args:
        user_id: Process only images for a specific user ID
        kb_item_id: Process only images for a specific knowledge base item ID
        dry_run: Show what would be updated without making changes
    """
    print("Starting image caption population...")
    
    service = KnowledgeBaseImageService()
    
    # Build query for images that need caption updates
    query = KnowledgeBaseImage.objects.select_related('knowledge_base_item')
    
    if user_id:
        query = query.filter(knowledge_base_item__user_id=user_id)
    
    if kb_item_id:
        query = query.filter(knowledge_base_item_id=kb_item_id)
    
    # Only process images with empty captions
    query = query.filter(image_caption__in=['', None])
    
    images_to_process = query.order_by('knowledge_base_item_id', 'image_id')
    
    print(f"Found {images_to_process.count()} images to process")
    
    updated_count = 0
    error_count = 0
    processed_kb_items = set()
    
    for image in images_to_process:
        try:
            kb_item = image.knowledge_base_item
            
            # Process each knowledge base item only once
            if kb_item.id not in processed_kb_items:
                processed_kb_items.add(kb_item.id)
                
                print(f"Processing KB item {kb_item.id}: {kb_item.title}")
                
                if dry_run:
                    print(f"  Would auto-populate captions for KB item {kb_item.id}")
                else:
                    # Auto-populate captions for this knowledge base item
                    success = service.auto_populate_captions_from_content(
                        kb_item_id=kb_item.id,
                        user_id=kb_item.user_id
                    )
                    
                    if success:
                        print(f"  Successfully updated captions for KB item {kb_item.id}")
                        # Count how many images were updated
                        updated_images = KnowledgeBaseImage.objects.filter(
                            knowledge_base_item=kb_item,
                            image_caption__isnull=False
                        ).exclude(image_caption='')
                        updated_count += updated_images.count()
                    else:
                        print(f"  Failed to update captions for KB item {kb_item.id}")
                        error_count += 1
            
        except Exception as e:
            error_count += 1
            print(f"Error processing image {image.id}: {e}")
    
    # Summary
    if dry_run:
        print(f"Dry run complete: would process {len(processed_kb_items)} knowledge base items")
    else:
        print(f"Updated captions for {len(processed_kb_items)} knowledge base items")
        print(f"Total images updated: {updated_count}")
    
    if error_count > 0:
        print(f"{error_count} items had errors during processing")


def main():
    """Main function with command line argument parsing."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Populate image captions using paper processing utilities')
    parser.add_argument('--user-id', type=int, help='Process only images for a specific user ID')
    parser.add_argument('--kb-item-id', type=int, help='Process only images for a specific knowledge base item ID')
    parser.add_argument('--dry-run', action='store_true', default=True, help='Show what would be updated without making changes')
    parser.add_argument('--execute', action='store_true', help='Actually execute the updates (overrides --dry-run)')
    
    args = parser.parse_args()
    
    # If --execute is specified, turn off dry-run
    dry_run = args.dry_run and not args.execute
    
    populate_captions(
        user_id=args.user_id,
        kb_item_id=args.kb_item_id,
        dry_run=dry_run
    )


if __name__ == '__main__':
    main()