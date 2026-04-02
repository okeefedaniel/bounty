"""Add SearchVectorField and trigram indexes for full-text search."""
import django.contrib.postgres.indexes
import django.contrib.postgres.search
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('opportunities', '0002_federalopportunity_harbor_program_id'),
        ('keel_search', '0001_initial'),  # ensures pg_trgm extension exists
    ]

    operations = [
        # Add search_vector field
        migrations.AddField(
            model_name='federalopportunity',
            name='search_vector',
            field=django.contrib.postgres.search.SearchVectorField(null=True),
        ),
        # GIN index on search_vector for fast FTS
        migrations.AddIndex(
            model_name='federalopportunity',
            index=django.contrib.postgres.indexes.GinIndex(
                fields=['search_vector'], name='fedopp_search_gin',
            ),
        ),
        # Trigram indexes for typo-tolerant instant search
        migrations.RunSQL(
            sql="""
                CREATE INDEX IF NOT EXISTS fedopp_title_trgm
                ON opportunities_federalopportunity
                USING gin (title gin_trgm_ops);
            """,
            reverse_sql="DROP INDEX IF EXISTS fedopp_title_trgm;",
        ),
        migrations.RunSQL(
            sql="""
                CREATE INDEX IF NOT EXISTS fedopp_agency_trgm
                ON opportunities_federalopportunity
                USING gin (agency_name gin_trgm_ops);
            """,
            reverse_sql="DROP INDEX IF EXISTS fedopp_agency_trgm;",
        ),
        # Backfill search vectors for existing records
        migrations.RunSQL(
            sql="""
                UPDATE opportunities_federalopportunity
                SET search_vector =
                    setweight(to_tsvector('english', coalesce(title, '')), 'A') ||
                    setweight(to_tsvector('english', coalesce(agency_name, '')), 'B') ||
                    setweight(to_tsvector('english', coalesce(description, '')), 'C')
                WHERE search_vector IS NULL;
            """,
            reverse_sql="UPDATE opportunities_federalopportunity SET search_vector = NULL;",
        ),
    ]
