"""Apply FileSecurityValidator to opportunityattachment.file (keel 0.25.0+).

Auto-generated to record the AbstractAttachment.file change in keel —
keel/core/models.py now sets validators=[FileSecurityValidator()].
"""
from django.db import migrations, models

import keel.security.scanning


class Migration(migrations.Migration):

    dependencies = [
        ('opportunities', '0007_alter_trackedopportunity_status'),
    ]

    operations = [
        migrations.AlterField(
            model_name='opportunityattachment',
            name='file',
            field=models.FileField(
                upload_to='attachments/%Y/%m/',
                validators=[keel.security.scanning.FileSecurityValidator()],
            ),
        ),
    ]
