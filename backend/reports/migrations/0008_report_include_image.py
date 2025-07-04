from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('reports', '0007_alter_report_prompt_type'),
    ]

    operations = [
        migrations.AddField(
            model_name='report',
            name='include_image',
            field=models.BooleanField(
                default=False,
                help_text='Whether to include figure data (images) during report generation',
            ),
        ),
    ] 