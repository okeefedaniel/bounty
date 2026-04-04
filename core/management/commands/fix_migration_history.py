"""One-time fix: insert keel_accounts migration records to resolve InconsistentMigrationHistory.

The KeelUser migration rewrote core.0001_initial to depend on keel_accounts.0001_initial,
but the database already had the old core.0001_initial applied. Django's consistency check
blocks ALL migrations, including the targeted keel_accounts ones.

This command directly inserts migration records into django_migrations and creates the
keel_user table via raw SQL, bypassing Django's migration framework entirely.
"""
import logging

from django.core.management.base import BaseCommand
from django.db import connection

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Fix InconsistentMigrationHistory for keel_accounts'

    def handle(self, *args, **options):
        with connection.cursor() as cursor:
            # Check if keel_accounts.0001_initial is already recorded
            cursor.execute(
                "SELECT COUNT(*) FROM django_migrations WHERE app='keel_accounts' AND name='0001_initial'"
            )
            count = cursor.fetchone()[0]

            # Always check table/columns even if migration is recorded
            # (previous deploy may have created table with missing columns)

            # Check if keel_user table exists
            cursor.execute(
                "SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'keel_user')"
            )
            table_exists = cursor.fetchone()[0]

            if not table_exists:
                self.stdout.write('Creating keel_user table...')
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS keel_user (
                        id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
                        password varchar(128) NOT NULL,
                        last_login timestamp with time zone,
                        is_superuser boolean NOT NULL DEFAULT false,
                        username varchar(150) NOT NULL UNIQUE,
                        first_name varchar(150) NOT NULL DEFAULT '',
                        last_name varchar(150) NOT NULL DEFAULT '',
                        email varchar(254) NOT NULL DEFAULT '',
                        is_staff boolean NOT NULL DEFAULT false,
                        is_active boolean NOT NULL DEFAULT true,
                        date_joined timestamp with time zone NOT NULL DEFAULT NOW(),
                        phone varchar(30) NOT NULL DEFAULT '',
                        title varchar(100) NOT NULL DEFAULT '',
                        is_state_user boolean NOT NULL DEFAULT false,
                        accepted_terms boolean NOT NULL DEFAULT false,
                        accepted_terms_at timestamp with time zone,
                        agency_id uuid,
                        created_at timestamp with time zone NOT NULL DEFAULT NOW(),
                        updated_at timestamp with time zone NOT NULL DEFAULT NOW()
                    )
                """)
            else:
                self.stdout.write('keel_user table exists, checking for missing columns...')
                # Table exists but may be missing columns from earlier partial creation
                missing_cols = [
                    ('is_state_user', 'boolean NOT NULL DEFAULT false'),
                    ('accepted_terms', 'boolean NOT NULL DEFAULT false'),
                    ('accepted_terms_at', 'timestamp with time zone'),
                ]
                for col, defn in missing_cols:
                    cursor.execute(
                        "SELECT EXISTS (SELECT 1 FROM information_schema.columns "
                        "WHERE table_name='keel_user' AND column_name=%s)", [col]
                    )
                    exists = cursor.fetchone()[0]
                    self.stdout.write(f'  Column {col}: {"exists" if exists else "MISSING"}')
                    if not exists:
                        cursor.execute(f"ALTER TABLE keel_user ADD COLUMN IF NOT EXISTS {col} {defn}")
                        self.stdout.write(self.style.SUCCESS(f'  -> Added {col}'))
                # Create the M2M tables for groups and permissions
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS keel_user_groups (
                        id bigserial PRIMARY KEY,
                        keeluser_id uuid NOT NULL REFERENCES keel_user(id) ON DELETE CASCADE,
                        group_id integer NOT NULL REFERENCES auth_group(id) ON DELETE CASCADE,
                        UNIQUE(keeluser_id, group_id)
                    )
                """)
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS keel_user_user_permissions (
                        id bigserial PRIMARY KEY,
                        keeluser_id uuid NOT NULL REFERENCES keel_user(id) ON DELETE CASCADE,
                        permission_id integer NOT NULL REFERENCES auth_permission(id) ON DELETE CASCADE,
                        UNIQUE(keeluser_id, permission_id)
                    )
                """)
                # Create other keel_accounts tables
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS keel_accounts_agency (
                        id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
                        name varchar(255) NOT NULL,
                        abbreviation varchar(20) NOT NULL UNIQUE,
                        description text NOT NULL DEFAULT '',
                        contact_name varchar(255) NOT NULL DEFAULT '',
                        contact_email varchar(254) NOT NULL DEFAULT '',
                        is_active boolean NOT NULL DEFAULT true
                    )
                """)
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS keel_accounts_productaccess (
                        id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
                        product varchar(30) NOT NULL,
                        role varchar(50) NOT NULL DEFAULT '',
                        is_active boolean NOT NULL DEFAULT true,
                        granted_at timestamp with time zone NOT NULL DEFAULT NOW(),
                        user_id uuid NOT NULL REFERENCES keel_user(id) ON DELETE CASCADE,
                        granted_by_id uuid REFERENCES keel_user(id) ON DELETE SET NULL,
                        is_beta_tester boolean NOT NULL DEFAULT false
                    )
                """)
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS keel_accounts_invitation (
                        id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
                        email varchar(254) NOT NULL,
                        product varchar(30) NOT NULL,
                        role varchar(50) NOT NULL DEFAULT '',
                        token varchar(64) NOT NULL UNIQUE,
                        is_accepted boolean NOT NULL DEFAULT false,
                        created_at timestamp with time zone NOT NULL DEFAULT NOW(),
                        accepted_at timestamp with time zone,
                        invited_by_id uuid NOT NULL REFERENCES keel_user(id) ON DELETE CASCADE,
                        accepted_by_id uuid REFERENCES keel_user(id) ON DELETE SET NULL,
                        is_beta_tester boolean NOT NULL DEFAULT false
                    )
                """)
                self.stdout.write(self.style.SUCCESS('keel_accounts tables created.'))

            # Record all keel_accounts migrations as applied
            migrations_to_fake = [
                '0001_initial',
                '0002_productaccess_is_beta_tester',
                '0003_add_auditlog',
                '0004_add_notification_models',
                '0005_add_notification_type_override',
                '0006_add_beta_tester_to_invitation',
            ]
            for name in migrations_to_fake:
                cursor.execute(
                    "INSERT INTO django_migrations (app, name, applied) "
                    "VALUES ('keel_accounts', %s, NOW()) "
                    "ON CONFLICT DO NOTHING",
                    [name],
                )
            self.stdout.write(self.style.SUCCESS(
                'Recorded keel_accounts migrations in django_migrations table.'
            ))

            # Also record keel_search if not present
            cursor.execute(
                "SELECT COUNT(*) FROM django_migrations WHERE app='keel_search'"
            )
            if cursor.fetchone()[0] == 0:
                cursor.execute("""
                    CREATE EXTENSION IF NOT EXISTS pg_trgm
                """)
                cursor.execute(
                    "INSERT INTO django_migrations (app, name, applied) "
                    "VALUES ('keel_search', '0001_initial', NOW()) "
                    "ON CONFLICT DO NOTHING"
                )
                self.stdout.write('Recorded keel_search.0001_initial.')

        self.stdout.write(self.style.SUCCESS('Migration history fixed. Run migrate --noinput next.'))
