"""Add SearchVectorField and trigram indexes for full-text search."""
import django.contrib.postgres.indexes
import django.contrib.postgres.search
from django.db import connection, migrations


def pg_only_indexes(apps, schema_editor):
    """Create trigram indexes and backfill search vectors on PostgreSQL only."""
    if connection.vendor != 'postgresql':
        return
    cursor = schema_editor.connection.cursor()
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS fedopp_title_trgm
        ON opportunities_federalopportunity USING gin (title gin_trgm_ops);
    """)
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS fedopp_agency_trgm
        ON opportunities_federalopportunity USING gin (agency_name gin_trgm_ops);
    """)
    cursor.execute("""
        UPDATE opportunities_federalopportunity
        SET search_vector =
            setweight(to_tsvector('english', coalesce(title, '')), 'A') ||
            setweight(to_tsvector('english', coalesce(agency_name, '')), 'B') ||
            setweight(to_tsvector('english', coalesce(description, '')), 'C')
        WHERE search_vector IS NULL;
    """)


class Migration(migrations.Migration):

    dependencies = [
        ('opportunities', '0001_initial'),
        ('keel_search', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='federalopportunity',
            name='search_vector',
            field=django.contrib.postgres.search.SearchVectorField(null=True),
        ),
        migrations.AddIndex(
            model_name='federalopportunity',
            index=django.contrib.postgres.indexes.GinIndex(
                fields=['search_vector'], name='fedopp_search_gin',
            ),
        ),
        migrations.RunPython(pg_only_indexes, migrations.RunPython.noop),
    ]
