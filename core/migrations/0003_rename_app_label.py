"""Rename app_label from 'core' to 'bounty_core' for suite shared DB."""

from django.db import migrations

OLD_LABEL = 'core'
NEW_LABEL = 'bounty_core'

TABLE_RENAMES = [
    ('core_bountyprofile', 'bounty_core_bountyprofile'),
    ('core_auditlog', 'bounty_core_auditlog'),
    ('core_notification', 'bounty_core_notification'),
    ('core_notificationpreference', 'bounty_core_notificationpreference'),
    ('core_notificationlog', 'bounty_core_notificationlog'),
]


def _table_exists(connection, table_name):
    return table_name in connection.introspection.table_names()


def forwards(apps, schema_editor):
    for old_name, new_name in TABLE_RENAMES:
        if _table_exists(schema_editor.connection, old_name):
            schema_editor.execute(f'ALTER TABLE "{old_name}" RENAME TO "{new_name}"')
    schema_editor.execute(
        "UPDATE django_content_type SET app_label = %s WHERE app_label = %s",
        [NEW_LABEL, OLD_LABEL],
    )
    schema_editor.execute(
        "UPDATE django_migrations SET app = %s WHERE app = %s",
        [NEW_LABEL, OLD_LABEL],
    )


def backwards(apps, schema_editor):
    for old_name, new_name in TABLE_RENAMES:
        if _table_exists(schema_editor.connection, new_name):
            schema_editor.execute(f'ALTER TABLE "{new_name}" RENAME TO "{old_name}"')
    schema_editor.execute(
        "UPDATE django_content_type SET app_label = %s WHERE app_label = %s",
        [OLD_LABEL, NEW_LABEL],
    )
    schema_editor.execute(
        "UPDATE django_migrations SET app = %s WHERE app = %s",
        [OLD_LABEL, NEW_LABEL],
    )


class Migration(migrations.Migration):

    atomic = False

    dependencies = [
        ('bounty_core', '0002_ensure_keel_accounts'),
    ]

    operations = [
        migrations.RunPython(forwards, backwards),
    ]
