"""Ensure keel_accounts tables exist.

The KeelUser migration rewrote 0001_initial to depend on keel_accounts,
but the database already had the old 0001 applied. This migration
forces keel_accounts.0001 to be processed.
"""
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('bounty_core', '0001_initial'),
        ('keel_accounts', '0001_initial'),
    ]

    operations = [
        # No-op — just forces the dependency to be resolved
        migrations.RunSQL(migrations.RunSQL.noop, migrations.RunSQL.noop),
    ]
