# Generated migration for knowledge base refactor - Fixed for blank database

from django.db import migrations, models
import django.db.models.deletion
import uuid


def migrate_knowledge_items_to_notebook_specific(apps, schema_editor):
    """
    Migrate data from user-specific KnowledgeBaseItem + KnowledgeItem linking
    to notebook-specific KnowledgeBaseItem model.
    """
    # Since starting with blank database, no data migration needed
    pass


def reverse_migrate_knowledge_items(apps, schema_editor):
    """
    Reverse migration - this is complex and may result in data loss.
    """
    # This is a destructive operation that would be very complex to reverse
    # For now, we'll just pass - manual intervention would be needed
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('notebooks', '0010_remove_source_needs_processing_and_more'),
    ]

    operations = [
        # Step 0: Remove indexes that reference the user field first
        migrations.RunSQL(
            """
            DROP INDEX IF EXISTS notebooks_k_user_id_d865ea_idx;
            DROP INDEX IF EXISTS notebooks_k_user_id_424da8_idx; 
            DROP INDEX IF EXISTS notebooks_k_user_id_899dcb_idx;
            """,
            reverse_sql=""
        ),
        
        # Step 1: Remove user field from KnowledgeBaseItem
        migrations.RemoveField(
            model_name='knowledgebaseitem',
            name='user',
        ),
        
        # Step 2: Add notebook field to KnowledgeBaseItem
        migrations.AddField(
            model_name='knowledgebaseitem',
            name='notebook',
            field=models.ForeignKey(
                help_text='Notebook this knowledge item belongs to',
                on_delete=django.db.models.deletion.CASCADE,
                related_name='knowledge_base_items',
                to='notebooks.notebook',
                default=None  # Will be set properly after creation
            ),
            preserve_default=False,
        ),
        
        # Step 3: Add notes field to KnowledgeBaseItem
        migrations.AddField(
            model_name='knowledgebaseitem',
            name='notes',
            field=models.TextField(blank=True, help_text='User notes about this knowledge item'),
        ),
        
        # Step 4: Remove source field from KnowledgeBaseItem
        migrations.RemoveField(
            model_name='knowledgebaseitem',
            name='source',
        ),
        
        # Step 5: Delete KnowledgeItem model entirely
        migrations.DeleteModel(
            name='KnowledgeItem',
        ),
        
        # Step 6: Add new indexes for notebook-based queries
        migrations.RunSQL(
            """
            CREATE INDEX notebooks_knowledgebaseitem_notebook_id_created_at_idx 
                ON notebooks_knowledgebaseitem (notebook_id, created_at DESC);
            CREATE INDEX notebooks_knowledgebaseitem_notebook_id_source_hash_idx 
                ON notebooks_knowledgebaseitem (notebook_id, source_hash);
            CREATE INDEX notebooks_knowledgebaseitem_notebook_id_content_type_idx 
                ON notebooks_knowledgebaseitem (notebook_id, content_type);
            """,
            reverse_sql="""
            DROP INDEX IF EXISTS notebooks_knowledgebaseitem_notebook_id_created_at_idx;
            DROP INDEX IF EXISTS notebooks_knowledgebaseitem_notebook_id_source_hash_idx;
            DROP INDEX IF EXISTS notebooks_knowledgebaseitem_notebook_id_content_type_idx;
            """
        ),
    ]