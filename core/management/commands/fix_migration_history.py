"""One-time fix: create keel_accounts tables and record migrations.

Bypasses Django's migration framework which is blocked by
InconsistentMigrationHistory (core.0001 depends on keel_accounts.0001
but core.0001 was applied before keel_accounts existed).

Idempotent — safe to run on every deploy.
"""
from django.core.management.base import BaseCommand
from django.db import connection


def _ensure_table(cursor, table_name, create_sql, stdout):
    cursor.execute(
        "SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = %s)",
        [table_name],
    )
    if not cursor.fetchone()[0]:
        cursor.execute(create_sql)
        stdout.write(f'  Created table: {table_name}')
    else:
        stdout.write(f'  Table exists: {table_name}')


def _ensure_column(cursor, table_name, col_name, col_def, stdout):
    cursor.execute(
        "SELECT EXISTS (SELECT 1 FROM information_schema.columns "
        "WHERE table_name=%s AND column_name=%s)",
        [table_name, col_name],
    )
    if not cursor.fetchone()[0]:
        cursor.execute(f"ALTER TABLE {table_name} ADD COLUMN IF NOT EXISTS {col_name} {col_def}")
        stdout.write(f'  Added column: {table_name}.{col_name}')


class Command(BaseCommand):
    help = 'Fix InconsistentMigrationHistory for keel_accounts'

    def handle(self, *args, **options):
        with connection.cursor() as cursor:
            # Dedupe django_migrations rows accumulated by prior buggy runs
            # of this command (ON CONFLICT DO NOTHING was a no-op without a
            # unique constraint). Idempotent: a no-op once the table is clean.
            cursor.execute(
                "DELETE FROM django_migrations a USING django_migrations b "
                "WHERE a.id > b.id AND a.app = b.app AND a.name = b.name"
            )
            if cursor.rowcount:
                self.stdout.write(f'  Removed {cursor.rowcount} duplicate django_migrations rows')

            self.stdout.write('Ensuring keel_accounts tables exist...')

            # 1. keel_user (custom db_table)
            _ensure_table(cursor, 'keel_user', """
                CREATE TABLE keel_user (
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
            """, self.stdout)

            # Ensure columns added after initial creation
            for col, defn in [
                ('is_state_user', 'boolean NOT NULL DEFAULT false'),
                ('accepted_terms', 'boolean NOT NULL DEFAULT false'),
                ('accepted_terms_at', 'timestamp with time zone'),
            ]:
                _ensure_column(cursor, 'keel_user', col, defn, self.stdout)

            # 2. M2M tables
            _ensure_table(cursor, 'keel_user_groups', """
                CREATE TABLE keel_user_groups (
                    id bigserial PRIMARY KEY,
                    keeluser_id uuid NOT NULL REFERENCES keel_user(id) ON DELETE CASCADE,
                    group_id integer NOT NULL REFERENCES auth_group(id) ON DELETE CASCADE,
                    UNIQUE(keeluser_id, group_id)
                )
            """, self.stdout)

            _ensure_table(cursor, 'keel_user_user_permissions', """
                CREATE TABLE keel_user_user_permissions (
                    id bigserial PRIMARY KEY,
                    keeluser_id uuid NOT NULL REFERENCES keel_user(id) ON DELETE CASCADE,
                    permission_id integer NOT NULL REFERENCES auth_permission(id) ON DELETE CASCADE,
                    UNIQUE(keeluser_id, permission_id)
                )
            """, self.stdout)

            # 3. keel_agency (custom db_table)
            _ensure_table(cursor, 'keel_agency', """
                CREATE TABLE keel_agency (
                    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
                    name varchar(255) NOT NULL,
                    abbreviation varchar(20) NOT NULL UNIQUE,
                    description text NOT NULL DEFAULT '',
                    contact_name varchar(255) NOT NULL DEFAULT '',
                    contact_email varchar(254) NOT NULL DEFAULT '',
                    is_active boolean NOT NULL DEFAULT true
                )
            """, self.stdout)

            # 4. keel_product_access (custom db_table)
            _ensure_table(cursor, 'keel_product_access', """
                CREATE TABLE keel_product_access (
                    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
                    product varchar(30) NOT NULL,
                    role varchar(50) NOT NULL DEFAULT '',
                    is_active boolean NOT NULL DEFAULT true,
                    granted_at timestamp with time zone NOT NULL DEFAULT NOW(),
                    user_id uuid NOT NULL REFERENCES keel_user(id) ON DELETE CASCADE,
                    granted_by_id uuid REFERENCES keel_user(id) ON DELETE SET NULL,
                    is_beta_tester boolean NOT NULL DEFAULT false
                )
            """, self.stdout)

            # 5. keel_invitation (custom db_table)
            _ensure_table(cursor, 'keel_invitation', """
                CREATE TABLE keel_invitation (
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
            """, self.stdout)

            # 6. keel_audit_log (from migration 0003)
            _ensure_table(cursor, 'keel_audit_log', """
                CREATE TABLE keel_audit_log (
                    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
                    action varchar(20) NOT NULL,
                    model_name varchar(100) NOT NULL DEFAULT '',
                    object_id varchar(64) NOT NULL DEFAULT '',
                    changes jsonb NOT NULL DEFAULT '{}',
                    ip_address inet,
                    created_at timestamp with time zone NOT NULL DEFAULT NOW(),
                    user_id uuid REFERENCES keel_user(id) ON DELETE SET NULL
                )
            """, self.stdout)

            # 7. keel_notification tables (from migration 0004)
            _ensure_table(cursor, 'keel_notification', """
                CREATE TABLE keel_notification (
                    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
                    title varchar(255) NOT NULL,
                    message text NOT NULL DEFAULT '',
                    link varchar(500) NOT NULL DEFAULT '',
                    priority varchar(10) NOT NULL DEFAULT 'medium',
                    is_read boolean NOT NULL DEFAULT false,
                    read_at timestamp with time zone,
                    created_at timestamp with time zone NOT NULL DEFAULT NOW(),
                    recipient_id uuid NOT NULL REFERENCES keel_user(id) ON DELETE CASCADE
                )
            """, self.stdout)

            _ensure_table(cursor, 'keel_notification_preference', """
                CREATE TABLE keel_notification_preference (
                    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
                    notification_type varchar(100) NOT NULL,
                    channel_in_app boolean NOT NULL DEFAULT true,
                    channel_email boolean NOT NULL DEFAULT true,
                    channel_sms boolean NOT NULL DEFAULT false,
                    is_muted boolean NOT NULL DEFAULT false,
                    updated_at timestamp with time zone NOT NULL DEFAULT NOW(),
                    user_id uuid NOT NULL REFERENCES keel_user(id) ON DELETE CASCADE,
                    UNIQUE(user_id, notification_type)
                )
            """, self.stdout)

            _ensure_table(cursor, 'keel_notification_log', """
                CREATE TABLE keel_notification_log (
                    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
                    notification_type varchar(100) NOT NULL,
                    channel varchar(20) NOT NULL,
                    success boolean NOT NULL DEFAULT true,
                    error_message text NOT NULL DEFAULT '',
                    created_at timestamp with time zone NOT NULL DEFAULT NOW(),
                    recipient_id uuid NOT NULL REFERENCES keel_user(id) ON DELETE CASCADE
                )
            """, self.stdout)

            # 8. keel_notification_type_override (from migration 0005)
            _ensure_table(cursor, 'keel_notification_type_override', """
                CREATE TABLE keel_notification_type_override (
                    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
                    key varchar(100) NOT NULL UNIQUE,
                    channels jsonb,
                    roles jsonb,
                    priority varchar(10) NOT NULL DEFAULT '',
                    allow_mute boolean,
                    updated_at timestamp with time zone NOT NULL DEFAULT NOW()
                )
            """, self.stdout)

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
                    "SELECT 'keel_accounts', %s, NOW() "
                    "WHERE NOT EXISTS ("
                    "  SELECT 1 FROM django_migrations "
                    "  WHERE app='keel_accounts' AND name=%s"
                    ")",
                    [name, name],
                )

            # Record keel_search if not present
            cursor.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")
            cursor.execute(
                "INSERT INTO django_migrations (app, name, applied) "
                "SELECT 'keel_search', '0001_initial', NOW() "
                "WHERE NOT EXISTS ("
                "  SELECT 1 FROM django_migrations "
                "  WHERE app='keel_search' AND name='0001_initial'"
                ")"
            )

            # Legacy-DB recovery path. Only fire when there is actual evidence that a
            # legacy or already-renamed schema exists — on a truly fresh DB neither
            # table is present and we must NOT pre-create core_bountyprofile, because
            # 0001_initial will create bounty_core_bountyprofile and 0003's rename
            # would then collide with "relation bounty_core_bountyprofile already exists".
            cursor.execute(
                "SELECT "
                "  EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'core_bountyprofile') "
                "  OR EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'bounty_core_bountyprofile')"
            )
            legacy_or_migrated = cursor.fetchone()[0]

            if legacy_or_migrated:
                cursor.execute(
                    "SELECT EXISTS (SELECT 1 FROM information_schema.tables "
                    "WHERE table_name = 'bounty_core_bountyprofile')"
                )
                if not cursor.fetchone()[0]:
                    _ensure_table(cursor, 'core_bountyprofile', """
                        CREATE TABLE core_bountyprofile (
                            id bigserial PRIMARY KEY,
                            anthropic_api_key varchar(255) NOT NULL DEFAULT '',
                            organization_name varchar(255) NOT NULL DEFAULT '',
                            user_id uuid NOT NULL UNIQUE REFERENCES keel_user(id) ON DELETE CASCADE
                        )
                    """, self.stdout)

                for name in ['0001_initial', '0002_ensure_keel_accounts']:
                    cursor.execute(
                        "INSERT INTO django_migrations (app, name, applied) "
                        "SELECT 'core', %s, NOW() "
                        "WHERE NOT EXISTS ("
                        "  SELECT 1 FROM django_migrations "
                        "  WHERE app='core' AND name=%s"
                        ")",
                        [name, name],
                    )

        self.stdout.write(self.style.SUCCESS('All keel_accounts tables ensured. Running migrate next.'))
